import os
import streamlit as st
import streamlit.components.v1 as components
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


def _format_preview_preset(fmt: str) -> dict:
    presets = {
        "fmt1": {"font": "Calibri, Arial, sans-serif", "accent": "#2D2D2D", "banner": False, "sidebar": False},
        "fmt2": {"font": "'Times New Roman', Times, serif", "accent": "#000000", "banner": False, "sidebar": False},
        "fmt3": {"font": "Arial, Helvetica, sans-serif", "accent": "#2F54EB", "banner": False, "sidebar": False},
        "fmt4": {"font": "Verdana, Geneva, sans-serif", "accent": "#00875A", "banner": False, "sidebar": False},
        "fmt5": {"font": "Georgia, 'Times New Roman', serif", "accent": "#800000", "banner": True, "sidebar": False},
        "fmt6": {"font": "Garamond, serif", "accent": "#2F54EB", "banner": False, "sidebar": False},
        "fmt7": {"font": "Cambria, Georgia, serif", "accent": "#008080", "banner": False, "sidebar": False},
        "fmt8": {"font": "Tahoma, Geneva, sans-serif", "accent": "#E06C00", "banner": False, "sidebar": False},
        "fmt9": {"font": "'Trebuchet MS', Tahoma, sans-serif", "accent": "#663399", "banner": False, "sidebar": False},
        "fmt10": {"font": "'Century Gothic', Arial, sans-serif", "accent": "#607D8B", "banner": False, "sidebar": False},
        "fmt11": {"font": "'Palatino Linotype', Palatino, serif", "accent": "#003366", "banner": False, "sidebar": False},
        "fmt12": {"font": "Calibri, Arial, sans-serif", "accent": "#00BCD4", "banner": True, "sidebar": True},
    }
    if fmt not in presets:
        # Cycle a palette for fmt13..fmt30
        palette = ["#3F51B5", "#009688", "#FF5722", "#9C27B0", "#607D8B", "#4CAF50", "#F44336"]
        idx = (int(fmt[3:]) - 1) % len(palette)
        return {"font": "Arial, Helvetica, sans-serif", "accent": palette[idx], "banner": (idx % 2 == 0), "sidebar": (idx % 3 == 0)}
    return presets[fmt]


def render_format_preview(fmt: str):
    p = _format_preview_preset(fmt)
    font = p["font"]
    accent = p["accent"]
    banner = p["banner"]
    sidebar = p["sidebar"]

    # Minimal HTML/CSS + tiny JS hover to illustrate style
    if sidebar:
        html = f"""
        <style>
          html, body {{ background:#fff; }}
          .cv {{ font-family:{font}; color:#222; background:#fff; }}
          .cv .wrap {{ display:grid; grid-template-columns: 240px 1fr; gap:18px; }}
          .cv .sidebar {{ background:#f7f9fb; border-left:6px solid {accent}; padding:14px; border-radius:6px; }}
          .cv .name {{ font-weight:800; font-size:26px; margin:0 0 6px; }}
          .cv .banner {{ display:{'block' if banner else 'none'}; background:{accent}; color:#fff; padding:10px 14px; border-radius:6px; font-weight:800; margin-bottom:10px; }}
          .cv h3 {{ font-size:13px; letter-spacing:.06em; text-transform:uppercase; color:{accent}; margin:14px 0 6px; }}
          .cv .chip {{ display:inline-block; padding:4px 8px; background:#eef3ff; border:1px solid {accent}; color:{accent}; border-radius:999px; margin:2px 4px 0 0; font-size:11px; }}
          .cv .sec h2 {{ color:{accent}; font-size:14px; margin:10px 0 6px; text-transform:uppercase; letter-spacing:.06em; }}
          .cv li {{ margin:4px 0; }}
        </style>
        <div class="cv">
          <div class="banner">JANE DOE</div>
          <div class="wrap">
            <aside class="sidebar">
              <div class="name">Jane Doe</div>
              <div>jane@example.com</div>
              <div>+1 555 0100</div>
              <h3>Skills</h3>
              <div>
                <span class="chip">SQL</span>
                <span class="chip">Python</span>
                <span class="chip">Tableau</span>
              </div>
              <h3>Links</h3>
              <div><a href="#">github.com/jane</a></div>
              <div><a href="#">linkedin.com/in/jane</a></div>
            </aside>
            <main>
              <section class="sec">
                <h2>Summary</h2>
                <p>Data analyst with 4+ years driving insights and automation.</p>
              </section>
              <section class="sec">
                <h2>Experience</h2>
                <ul>
                  <li>Improved ETL pipelines, reducing latency by 35%.</li>
                  <li>Built KPI dashboards adopted by 6 teams.</li>
                </ul>
              </section>
            </main>
          </div>
        </div>
        <script>document.querySelectorAll('.chip').forEach(c=>c.addEventListener('mouseenter',()=>c.style.background='{accent}33'));</script>
        """
    else:
        html = f"""
        <style>
          html, body {{ background:#fff; }}
          .cv {{ font-family:{font}; color:#222; background:#fff; border:1px solid #e6e6e6; border-radius:8px; padding:14px; }}
          .cv .name {{ text-align:center; font-weight:800; font-size:26px; margin:0; {('background:'+accent+';color:#fff;padding:10px;border-radius:6px;') if banner else ''} }}
          .cv .contact {{ text-align:center; margin:8px 0 12px; color:#444; }}
          .cv hr {{ border:none; border-top:2px solid {accent}; margin:8px 0 12px; }}
          .cv h2 {{ color:{accent}; font-size:14px; margin:10px 0 6px; text-transform:uppercase; letter-spacing:.06em; }}
          .cv li {{ margin:4px 0; }}
        </style>
        <div class="cv">
          <div class="name">JANE DOE</div>
          <div class="contact">jane@example.com • +1 555 0100 • linkedin.com/in/jane</div>
          <hr />
          <section>
            <h2>Summary</h2>
            <p>Data analyst with 4+ years driving insights and automation.</p>
          </section>
          <section>
            <h2>Experience</h2>
            <ul>
              <li>Improved ETL pipelines, reducing latency by 35%.</li>
              <li>Built KPI dashboards adopted by 6 teams.</li>
            </ul>
          </section>
        </div>
        <script>document.querySelectorAll('h2').forEach(h=>h.addEventListener('click',()=>h.style.opacity='0.7'));</script>
        """
    components.html(html, height=320, scrolling=False)


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
    # Offer 30 styles; label first few with descriptions, rest generic
    base_labels = {
        "fmt1": "Format 1 – Modern (Calibri, gray)",
        "fmt2": "Format 2 – Classic (Times)",
        "fmt3": "Format 3 – Clean (Arial, blue)",
        "fmt4": "Format 4 – Verdana (green, tight)",
        "fmt5": "Format 5 – Georgia (maroon banner)",
        "fmt6": "Format 6 – Garamond (blue)",
        "fmt7": "Format 7 – Cambria (teal)",
        "fmt8": "Format 8 – Tahoma (orange)",
        "fmt9": "Format 9 – Trebuchet (purple)",
        "fmt10": "Format 10 – Century Gothic (slate)",
        "fmt11": "Format 11 – Palatino (navy)",
        "fmt12": "Format 12 – Calibri (cyan banner)",
    }
    options = [f"fmt{i}" for i in range(1, 31)]
    def _fmt_label(k: str) -> str:
        return base_labels.get(k, f"Format {k[3:]} – Variant")
    fmt_key = st.selectbox("Choose Resume Format", options=options, format_func=_fmt_label, index=0)
    st.markdown("### Provide Job Description")
    # Preview the chosen format
    with st.expander("Preview Selected Format", expanded=True):
        render_format_preview(fmt_key)

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

            # Keep only the model key on state; instantiate lazily in tools
            model_key = st.session_state.model_choice
            init_state = ModelState(
                file_path=file_path,
                jd={"raw_jd": st.session_state.jd_text},
                model=model_key,
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
        # Preserve auth/session identity keys; reset only flow-related state
        preserve = {"user_sub", "user_email", "user_name", "oauth_code_exchanged"}
        for key in list(st.session_state.keys()):
            if key in preserve:
                continue
            del st.session_state[key]
        # Reinitialize phase cleanly
        st.session_state.phase = "upload"
        st.rerun()
