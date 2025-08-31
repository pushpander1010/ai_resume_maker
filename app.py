import os
import streamlit as st
from pydantic import TypeAdapter, BaseModel

from models import ModelState
from main import build_getting_input_graph, build_process_request_graph
from tools import ensure_google_creds, sign_out, get_model_instance

# Page setup
st.set_page_config(page_title="Resume AI Assistant", layout="centered")
st.title("Resume AI Assistant")

# Local dev: allow http (safe to remove in production/Cloud)
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

# Scopes (include OIDC so we can show name/email)
SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Model options
MODEL_OPTIONS = [
    "google|gemini-2.5-pro",
    "google|gemini-2.5-flash",
    "perplexity|sonar",
    "groq|llama3-70b-8192",
    "groq|mixtral-8x7b-32768",
    "groq|gemma-7b-it",
]

@st.cache_resource(show_spinner=False)
def _graphs():
    return build_getting_input_graph(), build_process_request_graph()


def _coerce_state(raw_state):
    """Accept a dict or ModelState; sanitize nested Pydantic models to dicts before validation.
    This avoids class-identity mismatches after hot-reload (common in Streamlit).
    """
    if isinstance(raw_state, ModelState):
        return raw_state
    if isinstance(raw_state, dict):
        sanitized = {}
        for k, v in raw_state.items():
            # If nested pydantic model, convert to dict
            if hasattr(v, "model_dump"):
                try:
                    v = v.model_dump()
                except Exception:
                    pass
            sanitized[k] = v
        return ModelState.model_validate(sanitized)
    # Fallback to pydantic validation for other mapping-like objects
    return ModelState.model_validate(raw_state)

# Auth first (blocks until authenticated)
os.makedirs("input", exist_ok=True)
creds = ensure_google_creds(SCOPES)

# Header: show signed-in user & Logout
left, right = st.columns([3, 1])
with left:
    user_label = st.session_state.get("user_name") or st.session_state.get("user_email")
    if user_label:
        st.caption(f"Signed in as **{user_label}**")
with right:
    if st.button("Logout"):
        sign_out()

# Session State Setup
st.session_state.setdefault("state", None)
st.session_state.setdefault("questions_answered", False)
st.session_state.setdefault("phase", "upload")

# Upload Phase
if st.session_state.phase == "upload":
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.session_state.phase = "jd"
        st.rerun()

# JD + Model Selection Phase
if st.session_state.phase == "jd":
    model_choice = st.selectbox("Choose Model", MODEL_OPTIONS)
    format_labels = {
        "fmt1": "Format 1 – Modern (Calibri, gray accent)",
        "fmt2": "Format 2 – Classic (Times New Roman, minimal)",
        "fmt3": "Format 3 – Clean (Arial, blue accent)",
        "fmt4": "Format 4 – Verdana (green accent, tight)",
        "fmt5": "Format 5 – Georgia (maroon banner)",
    }
    fmt_key = st.selectbox(
        "Choose Resume Format",
        options=list(format_labels.keys()),
        format_func=lambda k: format_labels.get(k, k),
        index=0,
    )
    st.markdown("### Provide Job Description")
    jd_text = st.text_area(
        "Paste the job description (include recruiter email if available)", height=300
    )
    if jd_text:
        st.session_state.jd_text = jd_text
        st.session_state.model_choice = model_choice
        st.session_state.resume_format = fmt_key
        st.session_state.phase = "ready"
        st.rerun()

# Generate Button
if st.session_state.phase == "ready":
    if st.button("Generate Updated Resume"):
        st.session_state.phase = "processing"
        st.rerun()

# Processing Initial Resume
if st.session_state.phase == "processing":
    with st.spinner("Processing your resume..."):
        try:
            file_path = os.path.join("input", st.session_state.uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(st.session_state.uploaded_file.getvalue())

            model_instance = get_model_instance(st.session_state.model_choice)
            init_state = ModelState(
                file_path=file_path,
                jd={"raw_jd": st.session_state.jd_text},
                model=model_instance,
                resume_format=st.session_state.get("resume_format", "fmt1"),
                gmail_auth_creds=creds,
            )

            getting_input_graph, _ = _graphs()
            raw_state = getting_input_graph.invoke(init_state)
            st.session_state.state = _coerce_state(raw_state)
            st.session_state.questions_answered = False

            if st.session_state.state.questions and st.session_state.state.questions.questions:
                st.session_state.phase = "questions"
            else:
                st.session_state.phase = "final"
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.phase = "upload"

# Questions Phase
if st.session_state.phase == "questions":
    with st.expander("Missing Resume Info (Click to Answer)", expanded=True):
        st.warning("Your resume is missing some important information. Please answer the following:")

        updated_questions = []
        for i, question in enumerate(st.session_state.state.questions.questions):
            answer = st.text_input(f"Q{i+1}: {question.question}", key=f"q_{i}")
            question.answer = answer
            updated_questions.append(question)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Submit Answers"):
                for i, q in enumerate(st.session_state.state.questions.questions):
                    q.answer = st.session_state.get(f"q_{i}", "")
                st.session_state.questions_answered = True
                st.session_state.phase = "processing_answers"
                st.rerun()
        with c2:
            if st.button("Ignore"):
                for q in st.session_state.state.questions.questions:
                    q.answer = ""
                st.session_state.questions_answered = True
                st.session_state.phase = "processing_answers"
                st.rerun()

# Processing Answers
if st.session_state.phase == "processing_answers":
    with st.spinner("Processing your answers..."):
        try:
            _, process_request = _graphs()
            raw_state = process_request.invoke(st.session_state.state)
            st.session_state.state = _coerce_state(raw_state)
            st.session_state.phase = "final"
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.phase = "upload"

# Final Output Phase
if st.session_state.phase == "final":
    state = st.session_state.state
    st.success("Resume & Email generated successfully!")

    if state.docx_file and os.path.exists(state.docx_file):
        with open(state.docx_file, "rb") as f:
            st.download_button(
                "Download Resume (DOCX)",
                f,
                file_name="Updated_Resume.docx",
            )

    if state.pdf_file and os.path.exists(state.pdf_file):
        with open(state.pdf_file, "rb") as f:
            st.download_button(
                "Download Resume (PDF)",
                f,
                file_name="Updated_Resume.pdf",
            )

    if state.gmail_message and state.gmail_message.body:
        with st.expander("Generated Email"):
            st.markdown(f"**To:** {state.gmail_message.to}")
            st.markdown(f"**Subject:** {state.gmail_message.subject}")
            st.text_area("Email Body", state.gmail_message.body, height=200)
    elif getattr(state, "referral_message", None):
        with st.expander("Referral Message"):
            st.text_area("Referral Text", state.referral_message, height=150)

    if st.button("Create Another"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
