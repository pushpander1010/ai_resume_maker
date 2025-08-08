import streamlit as st
import os
from main import getting_input_graph, process_request, ModelState
from pydantic import TypeAdapter
from langchain_google_genai import GoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_perplexity import ChatPerplexity
import streamlit as st
from tools import ensure_google_creds
import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"   # DEV ONLY: allow http (no TLS)
# optional but handy when scopes differ slightly:
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


SCOPES = [
    "openid", "email", "profile",               # 👈 add these
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]


# ---------- Constants ----------
MODEL_OPTIONS = [
    "google|gemini-2.5-pro",
    "google|gemini-2.5-flash",
    "perplexity|sonar",
    "groq|llama3-70b-8192",
    "groq|mixtral-8x7b-32768",
    "groq|gemma-7b-it"
]

def get_model_instance(model_key: str):
    if model_key.startswith("google|"):
        model_id = model_key.split("|")[1]
        return GoogleGenerativeAI(model=model_id, temperature=0.7)
    elif model_key.startswith("groq|"):
        model_id = model_key.split("|")[1]
        return ChatGroq(model=model_id, temperature=0.7)
    elif model_key.startswith("perplexity|"):
        model_id = model_key.split("|")[1]
        return ChatPerplexity(model=model_id, temperature=0.7)
    else:
        raise ValueError(f"Unknown model: {model_key}")

col1, col2 = st.columns([3,1])
with col1:
    if st.session_state.get("user_email"):
        st.caption(f"Signed in as **{st.session_state.user_email}**")
with col2:
    if st.session_state.get("user_sub"):
        if st.button("Sign out"):
            # Just clear session; optionally delete token file too
            # os.remove(os.path.join("tokens", f"{st.session_state.user_sub}.pickle"))
            st.session_state.user_sub = None
            st.session_state.user_email = None
            st.rerun()

# ---------- Page Setup ----------
st.set_page_config(page_title="Resume AI Assistant", layout="centered")
st.title("📄 Resume AI Assistant")
os.makedirs("input", exist_ok=True)
creds = ensure_google_creds(SCOPES) 

# ---------- Session State Setup ----------
if "state" not in st.session_state:
    st.session_state.state = None
if "questions_answered" not in st.session_state:
    st.session_state.questions_answered = False
if "phase" not in st.session_state:
    st.session_state.phase = "upload"

# ---------- Upload Phase ----------
if st.session_state.phase == "upload":
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.session_state.phase = "jd"

# ---------- JD + Model Selection Phase ----------
if st.session_state.phase == "jd":
    model_choice = st.selectbox("Choose Model", MODEL_OPTIONS)
    st.markdown("### ✏️ Provide Job Description")
    jd_text = st.text_area("Paste the job description (include recruiter email if available)", height=300)
    if jd_text:
        st.session_state.jd_text = jd_text
        st.session_state.model_choice = model_choice
        st.session_state.phase = "ready"

# ---------- Generate Button ----------
if st.session_state.phase == "ready":
    if st.button("✨ Generate Updated Resume"):
        st.session_state.phase = "processing"
        st.rerun()

# ---------- Processing Initial Resume ----------
if st.session_state.phase == "processing":
    with st.spinner("🔄 Processing your resume..."):
        try:
            file_path = os.path.join("input", st.session_state.uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(st.session_state.uploaded_file.getvalue())

            model_instance = get_model_instance(st.session_state.model_choice)
            init_state = ModelState(
                file_path=file_path,
                jd={"raw_jd": st.session_state.jd_text},
                model=model_instance,
                gmail_auth_creds=creds
            )

            raw_state = getting_input_graph.invoke(init_state)

            st.session_state.state = raw_state if isinstance(raw_state, ModelState) else TypeAdapter(ModelState).validate_python(raw_state)
            st.session_state.questions_answered = False

            if (
                st.session_state.state.questions and
                st.session_state.state.questions.questions
            ):
                st.session_state.phase = "questions"
            else:
                st.session_state.phase = "final"
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.session_state.phase = "upload"

# ---------- Questions Phase ----------
if st.session_state.phase == "questions":
    with st.expander("📝 Missing Resume Info (Click to Answer)", expanded=True):
        st.warning("Your resume is missing some important information. Please answer the following:")

        updated_questions = []
        for i, question in enumerate(st.session_state.state.questions.questions):
            answer = st.text_input(f"Q{i+1}: {question.question}", key=f"q_{i}")
            question.answer = answer
            updated_questions.append(question)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Submit Answers"):
                for i, q in enumerate(st.session_state.state.questions.questions):
                    q.answer = st.session_state.get(f"q_{i}", "")
                st.session_state.questions_answered = True
                st.session_state.phase = "processing_answers"
                st.rerun()

        with col2:
            if st.button("🚫 Ignore"):
                for q in st.session_state.state.questions.questions:
                    q.answer = ""
                st.session_state.questions_answered = True
                st.session_state.phase = "processing_answers"
                st.rerun()

# ---------- Processing Answers ----------
if st.session_state.phase == "processing_answers":
    with st.spinner("🔄 Processing your answers..."):
        try:
            raw_state = process_request.invoke(st.session_state.state)
            st.session_state.state = raw_state if isinstance(raw_state, ModelState) else TypeAdapter(ModelState).validate_python(raw_state)
            st.session_state.phase = "final"
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.session_state.phase = "upload"

# ---------- Final Output Phase ----------
if st.session_state.phase == "final":
    state = st.session_state.state
    st.success("✅ Resume & Email generated successfully!")

    if state.docx_file and os.path.exists(state.docx_file):
        st.download_button("📄 Download Resume (DOCX)", open(state.docx_file, "rb"), file_name="Updated_Resume.docx")

    if state.pdf_file and os.path.exists(state.pdf_file):
        st.download_button("🧾 Download Resume (PDF)", open(state.pdf_file, "rb"), file_name="Updated_Resume.pdf")

    if state.gmail_message and state.gmail_message.body:
        with st.expander("📨 Generated Email"):
            st.markdown(f"**To:** {state.gmail_message.to}")
            st.markdown(f"**Subject:** {state.gmail_message.subject}")
            st.text_area("Email Body", state.gmail_message.body, height=200)

    elif state.referral_message:
        with st.expander("🤝 Referral Message"):
            st.text_area("Referral Text", state.referral_message, height=150)

    if st.button("🔄 Create Another"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
