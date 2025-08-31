import os
import streamlit as st
import streamlit.components.v1 as components
from pydantic import TypeAdapter, BaseModel

from models import ModelState, JD
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
    # Exact mapping of DOCX presets (fonts/accent/banner/sidebar)
    presets = {
        "fmt1":  {"font": "Calibri, Arial, sans-serif",                  "accent": "#2D2D2D", "banner": False, "sidebar": False},  # (45,45,45)
        "fmt2":  {"font": "'Times New Roman', Times, serif",             "accent": "#000000", "banner": False, "sidebar": False},  # (0,0,0)
        "fmt3":  {"font": "Arial, Helvetica, sans-serif",                 "accent": "#2F54EB", "banner": False, "sidebar": False},  # (47,84,235)
        "fmt4":  {"font": "Verdana, Geneva, sans-serif",                  "accent": "#00875A", "banner": False, "sidebar": False},  # (0,135,90)
        "fmt5":  {"font": "Georgia, 'Times New Roman', serif",            "accent": "#800000", "banner": True,  "sidebar": False},  # (128,0,0)
        "fmt6":  {"font": "Garamond, serif",                              "accent": "#2F54EB", "banner": False, "sidebar": False},  # (47,84,235)
        "fmt7":  {"font": "Cambria, Georgia, serif",                      "accent": "#008080", "banner": False, "sidebar": False},  # (0,128,128)
        "fmt8":  {"font": "Tahoma, Geneva, sans-serif",                   "accent": "#E06C00", "banner": False, "sidebar": False},  # (224,108,0)
        "fmt9":  {"font": "'Trebuchet MS', Tahoma, sans-serif",           "accent": "#663399", "banner": False, "sidebar": False},  # (102,51,153)
        "fmt10": {"font": "'Century Gothic', Arial, sans-serif",          "accent": "#607D8B", "banner": False, "sidebar": False},  # (96,125,139)
        "fmt11": {"font": "'Palatino Linotype', Palatino, serif",         "accent": "#003366", "banner": False, "sidebar": False},  # (0,51,102)
        "fmt12": {"font": "Calibri, Arial, sans-serif",                   "accent": "#00BCD4", "banner": True,  "sidebar": True },  # (0,188,212) + sidebar
        "fmt13": {"font": "Arial, Helvetica, sans-serif",                 "accent": "#3F51B5", "banner": False, "sidebar": False},  # (63,81,181)
        "fmt14": {"font": "Georgia, 'Times New Roman', serif",            "accent": "#E91E63", "banner": False, "sidebar": False},  # (233,30,99)
        "fmt15": {"font": "Verdana, Geneva, sans-serif",                  "accent": "#2E7D32", "banner": True,  "sidebar": False},  # (46,125,50)
        "fmt16": {"font": "'Times New Roman', Times, serif",              "accent": "#2196F3", "banner": False, "sidebar": False},  # (33,150,243)
        "fmt17": {"font": "Cambria, Georgia, serif",                      "accent": "#00695C", "banner": False, "sidebar": False},  # (0,105,92)
        "fmt18": {"font": "Garamond, serif",                              "accent": "#795548", "banner": True,  "sidebar": False},  # (121,85,72)
        "fmt19": {"font": "Tahoma, Geneva, sans-serif",                   "accent": "#009688", "banner": False, "sidebar": False},  # (0,150,136)
        "fmt20": {"font": "'Trebuchet MS', Tahoma, sans-serif",           "accent": "#FF5722", "banner": False, "sidebar": False},  # (255,87,34)
        "fmt21": {"font": "'Century Gothic', Arial, sans-serif",          "accent": "#9C27B0", "banner": True,  "sidebar": False},  # (156,39,176)
        "fmt22": {"font": "'Palatino Linotype', Palatino, serif",         "accent": "#CDDC39", "banner": False, "sidebar": False},  # (205,220,57)
        "fmt23": {"font": "Arial, Helvetica, sans-serif",                 "accent": "#000000", "banner": False, "sidebar": False},  # (0,0,0)
        "fmt24": {"font": "Georgia, 'Times New Roman', serif",            "accent": "#3F51B5", "banner": True,  "sidebar": False},  # (63,81,181)
        "fmt25": {"font": "Verdana, Geneva, sans-serif",                  "accent": "#212121", "banner": False, "sidebar": False},  # (33,33,33)
        "fmt26": {"font": "'Times New Roman', Times, serif",              "accent": "#4CAF50", "banner": False, "sidebar": False},  # (76,175,80)
        "fmt27": {"font": "Cambria, Georgia, serif",                      "accent": "#F44336", "banner": False, "sidebar": False},  # (244,67,54)
        "fmt28": {"font": "Arial, Helvetica, sans-serif",                 "accent": "#F44336", "banner": True,  "sidebar": True },  # override
        "fmt29": {"font": "Tahoma, Geneva, sans-serif",                   "accent": "#9E9E9E", "banner": False, "sidebar": False},  # (158,158,158)
        "fmt30": {"font": "'Trebuchet MS', Tahoma, sans-serif",           "accent": "#795548", "banner": True,  "sidebar": False},  # (121,85,72)
    }
    return presets.get(fmt, presets["fmt1"]) 


def render_format_preview(fmt: str = None, *, layout_key: str = None, font_key: str = None, color_key: str = None):
    # Back-compat: if fmt provided, use mapping; else use 3-axis selection
    if fmt:
        p = _format_preview_preset(fmt)
    else:
        # Map keys to CSS presets
        font_map = {
            "calibri": "Calibri, Arial, sans-serif",
            "times": "'Times New Roman', Times, serif",
            "arial": "Arial, Helvetica, sans-serif",
            "verdana": "Verdana, Geneva, sans-serif",
            "georgia": "Georgia, 'Times New Roman', serif",
            "garamond": "Garamond, serif",
            "cambria": "Cambria, Georgia, serif",
            "tahoma": "Tahoma, Geneva, sans-serif",
            "trebuchet": "'Trebuchet MS', Tahoma, sans-serif",
            "centurygothic": "'Century Gothic', Arial, sans-serif",
        }
        color_map = {
            "blue": "#2F54EB",
            "teal": "#009688",
            "green": "#2E7D32",
            "red": "#F44336",
            "purple": "#9C27B0",
            "slate": "#607D8B",
            "orange": "#FF5722",
            "navy": "#003366",
            "maroon": "#800000",
            "gray": "#2D2D2D",
        }
        layout_map = {
            "classic": {"banner": False, "sidebar": False},
            "banner": {"banner": True, "sidebar": False},
            "sidebar": {"banner": True, "sidebar": True},
            "compact": {"banner": False, "sidebar": False},
            "modern": {"banner": False, "sidebar": False},
            "minimal": {"banner": False, "sidebar": False},
            "elegant": {"banner": True, "sidebar": False},
            "sidebar-wide": {"banner": True, "sidebar": True},
        }
        p = {
            "font": font_map.get(font_key or "calibri"),
            "accent": color_map.get(color_key or "blue"),
        }
        p.update(layout_map.get(layout_key or "classic", {}))
    font = p["font"]
    accent = p["accent"]
    banner = p.get("banner", False)
    sidebar = p.get("sidebar", False)

    # Minimal HTML/CSS + tiny JS hover to illustrate style
    if sidebar:
        col_css = "270px 1fr" if (layout_key == "sidebar-wide") else "220px 1fr"
        html = f"""
        <style>
          html, body {{ background:#fff; }}
          .cv {{ font-family:{font}; color:#222; background:#fff; }}
          .cv .wrap {{ display:grid; grid-template-columns: {col_css}; gap:18px; }}
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
    # Merge partial dicts onto the existing state to preserve user selections
    if isinstance(raw_state, dict):
        base = None
        if isinstance(st.session_state.get("state"), ModelState):
            base = st.session_state.state.model_dump()
        elif st.session_state.get("uploaded_file") is not None:
            # Build a minimal base from what we put into init_state in this session
            base = {}
        else:
            base = {}

        # sanitize nested pydantic
        sanitized = {}
        for k, v in raw_state.items():
            if hasattr(v, "model_dump"):
                try:
                    v = v.model_dump()
                except Exception:
                    pass
            sanitized[k] = v
        merged = {**(base or {}), **sanitized}
        return ModelState.model_validate(merged)
    # Fallback
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
    if st.button("← Back"):
        st.session_state.phase = "upload"
        st.rerun()
    model_choice = st.selectbox("Choose Model", MODEL_OPTIONS)
    # New 3-axis preset selection (Layouts x Fonts x Colors)
    layouts = {
        "classic": "Classic (single column)",
        "banner": "Banner (single column with header)",
        "sidebar": "Sidebar (two columns)",
        "compact": "Compact (tight margins)",
        "modern": "Modern (accented sections)",
    }
    fonts = {
        "calibri": "Calibri",
        "times": "Times New Roman",
        "arial": "Arial",
        "verdana": "Verdana",
        "georgia": "Georgia",
        "garamond": "Garamond",
        "cambria": "Cambria",
        "tahoma": "Tahoma",
        "trebuchet": "Trebuchet MS",
        "centurygothic": "Century Gothic",
    }
    colors = {
        "blue": "Blue",
        "teal": "Teal",
        "green": "Green",
        "red": "Red",
        "purple": "Purple",
        "slate": "Slate",
        "orange": "Orange",
        "navy": "Navy",
        "maroon": "Maroon",
        "gray": "Gray",
    }
    c1, c2, c3 = st.columns(3)
    with c1:
        layout_key = st.selectbox("Layout", options=list(layouts.keys()), format_func=lambda k: layouts[k], index=list(layouts.keys()).index(st.session_state.get("resume_layout", "classic")) if st.session_state.get("resume_layout") in layouts else 0)
    with c2:
        font_key = st.selectbox("Font", options=list(fonts.keys()), format_func=lambda k: fonts[k], index=list(fonts.keys()).index(st.session_state.get("resume_font", "calibri")) if st.session_state.get("resume_font") in fonts else 0)
    with c3:
        color_key = st.selectbox("Accent Color", options=list(colors.keys()), format_func=lambda k: colors[k], index=list(colors.keys()).index(st.session_state.get("resume_color", "blue")) if st.session_state.get("resume_color") in colors else 0)
    st.markdown("### Provide Job Description")
    # Preview the chosen format
    with st.expander("Preview Selected Format", expanded=True):
        # Derived name for clarity
        st.caption(f"Preview: {layouts[layout_key]} • {fonts[font_key]} • {colors[color_key]}")
        render_format_preview(layout_key=layout_key, font_key=font_key, color_key=color_key)

    jd_text = st.text_area(
        "Paste the job description (include recruiter email if available)", height=300
    )
    user_req = st.text_area(
        "User request (additional) — optional",
        value=st.session_state.get("user_request", ""),
        height=120,
        help="Add any specific ask, tone, format, or constraints you want the agent to consider.",
    )
    if jd_text:
        st.session_state.jd_text = jd_text
        st.session_state.model_choice = model_choice
        st.session_state.user_request = user_req
        st.session_state.resume_layout = layout_key
        st.session_state.resume_font = font_key
        st.session_state.resume_color = color_key
        st.session_state.phase = "ready"
        st.rerun()

# Generate Button
if st.session_state.phase == "ready":
    if st.button("← Back"):
        st.session_state.phase = "jd"
        st.rerun()
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
                jd=JD.model_construct(raw_jd=st.session_state.jd_text),
                model=model_key,
                resume_layout=st.session_state.get("resume_layout", "classic"),
                resume_font=st.session_state.get("resume_font", "calibri"),
                resume_color=st.session_state.get("resume_color", "blue"),
                user_request=st.session_state.get("user_request"),
                gmail_auth_creds=creds,
            )

            getting_input_graph, _ = _graphs()
            raw_state = getting_input_graph.invoke(init_state)
            st.session_state.state = _coerce_state(raw_state)
            st.session_state.questions_answered = False

            if st.session_state.state.questions and st.session_state.state.questions.questions:
                st.session_state.phase = "questions"
                st.rerun()
            else:
                # No questions needed; run the process graph now to generate DOCX/PDF and drafts
                try:
                    _, process_request = _graphs()
                    raw2 = process_request.invoke(st.session_state.state)
                    st.session_state.state = _coerce_state(raw2)
                except Exception as e:
                    st.error(f"Error while generating outputs: {e}")
                st.session_state.phase = "final"
                st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.phase = "upload"

# Questions Phase
if st.session_state.phase == "questions":
    if st.button("← Back"):
        st.session_state.phase = "jd"
        st.rerun()
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
    if st.button("← Back"):
        st.session_state.phase = "questions"
        st.rerun()
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
    if st.button("← Back"):
        # Return to questions if they existed, else JD
        if getattr(st.session_state.state, "questions", None) and getattr(st.session_state.state.questions, "questions", None):
            st.session_state.phase = "questions"
        else:
            st.session_state.phase = "jd"
        st.rerun()
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

    # Show Email only if JD.email exists; else show Referral
    jd_email = None
    try:
        if state.jd:
            jd_email = getattr(state.jd, "email", None)
    except Exception:
        jd_email = None

    if jd_email and state.gmail_message and getattr(state.gmail_message, "body", None):
        with st.expander("Generated Email"):
            st.markdown(f"**To:** {state.gmail_message.to}")
            st.markdown(f"**Subject:** {state.gmail_message.subject}")
            st.text_area("Email Body", state.gmail_message.body, height=200)
    elif getattr(state, "referral_message", None):
        with st.expander("Referral Message", expanded=True):
            st.text_area("Referral Text (copy/paste to LinkedIn/email)", state.referral_message, height=200)

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
