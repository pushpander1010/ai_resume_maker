from docx2pdf import convert
from models import ModelState,Details,JD,GmailMessage,Question,QuestionList
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import urllib
import json
import os, io, pickle, urllib
from urllib.parse import urlparse
from typing import Optional
import streamlit as st
from google.oauth2.credentials import Credentials
from datetime import date, datetime
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import docx
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from pydantic import BaseModel
import uuid
from typing import List,Optional
from docx import Document
from docx.shared import Pt, Inches
from langchain_core.output_parsers import StrOutputParser,PydanticOutputParser
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt
import os, io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from PyPDF2 import PdfReader
from langchain.output_parsers import PydanticOutputParser
from docx2pdf import convert
import re
from bs4 import BeautifulSoup
from langchain_community.document_loaders import RecursiveUrlLoader
from dotenv import load_dotenv
from docx import Document
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from langchain_groq import ChatGroq
from langchain_perplexity import ChatPerplexity
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from email.message import EmailMessage
import base64
import mimetypes
import mimetypes
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st
import os, pickle
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
import os, io, pickle, urllib
from urllib.parse import urlparse
from typing import Optional
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

#load_dotenv()
load_dotenv(dotenv_path="environ.env")


import os, io, pickle, urllib
from typing import Optional
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import os, pickle, urllib, pathlib
from typing import Optional

import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

import os, pickle, urllib, pathlib
import streamlit as st
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

# ---- per-user token storage ----
def _tokens_dir() -> str:
    d = "tokens"
    pathlib.Path(d).mkdir(exist_ok=True)
    return d

def _user_token_path(user_sub: str) -> str:
    return os.path.join(_tokens_dir(), f"{user_sub}.pickle")

def _load_creds_for_user(user_sub: str) -> Optional[Credentials]:
    p = _user_token_path(user_sub)
    if not os.path.exists(p):
        return None
    try:
        creds = pickle.load(open(p, "rb"))
    except Exception:
        return None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            pickle.dump(creds, open(p, "wb"))
        except Exception:
            return None
    return creds if creds and creds.valid else None

def _save_creds_for_user(creds: Credentials, client_id: str) -> tuple[str, str]:
    """Return (user_sub, email) and persist token to tokens/{sub}.pickle."""
    if not creds.id_token:
        creds.refresh(Request())
    claims = google_id_token.verify_oauth2_token(
        creds.id_token, google_requests.Request(), client_id
    )
    user_sub = claims["sub"]
    email = claims.get("email", "")
    name = claims.get("name") or email

    pickle.dump(creds, open(_user_token_path(user_sub), "wb"))
    st.session_state.user_sub = user_sub
    st.session_state.user_email = email
    st.session_state.user_name = name
    return user_sub, email

def _clear_query_params():
    try:
        st.query_params.clear()          # Streamlit >= 1.30
    except Exception:
        st.experimental_set_query_params()  # legacy

def sign_out():
    """Clear THIS user's token & session, then rerun."""
    sub = st.session_state.get("user_sub")
    if sub:
        try:
            p = _user_token_path(sub)
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    for k in ("user_sub", "user_email", "user_name", "oauth_code_exchanged"):
        st.session_state.pop(k, None)
    st.rerun()

def ensure_google_creds(scopes: list[str], *, force_refresh: bool = False) -> Credentials:
    """
    Same-tab OAuth with per-user tokens.
      Requires env/secrets:
        GOOGLE_CLIENT_ID
        GOOGLE_CLIENT_SECRET
        GOOGLE_REDIRECT_URI (http://localhost:8501/ OR https://<app>.streamlit.app/)
    Stores name/email in st.session_state.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")

    # ---- Guardrails
    if not client_id or not client_secret:
        st.error("Missing GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.")
        st.stop()
    if not redirect_uri or not redirect_uri.endswith("/"):
        st.error("Set GOOGLE_REDIRECT_URI to your app URL with trailing slash.")
        st.stop()
    if "streamlit.app" in redirect_uri and not redirect_uri.startswith("https://"):
        st.error("On Streamlit Cloud, GOOGLE_REDIRECT_URI must begin with https://")
        st.stop()

    # Local http dev
    if redirect_uri.startswith("http://"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    # Session guards
    st.session_state.setdefault("oauth_code_exchanged", False)
    st.session_state.setdefault("user_sub", None)

    # ---- Per-user cached token ONLY (no global token!)
    if st.session_state.user_sub and not force_refresh:
        cached = _load_creds_for_user(st.session_state.user_sub)
        if cached:
            # fill name/email if not already set
            if not st.session_state.get("user_email"):
                try:
                    if not cached.id_token:
                        cached.refresh(Request())
                    claims = google_id_token.verify_oauth2_token(
                        cached.id_token, google_requests.Request(), client_id
                    )
                    st.session_state.user_email = claims.get("email")
                    st.session_state.user_name = claims.get("name") or claims.get("email")
                except Exception:
                    pass
            return cached

    # ---- Read callback params
    try:
        qp = dict(st.query_params)
    except Exception:
        qp = st.experimental_get_query_params()

    def _one(k):
        v = qp.get(k)
        return v[0] if isinstance(v, list) else v

    code = _one("code")
    error = _one("error")
    if error:
        st.error(f"OAuth error: {error}")
        _clear_query_params()
        st.stop()

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
            "javascript_origins": [redirect_uri.rstrip("/")],
        }
    }

    flow = Flow.from_client_config(client_config, scopes=scopes)
    flow.redirect_uri = redirect_uri

    # ---- Callback: exchange code -> tokens (once)
    if code and not st.session_state.oauth_code_exchanged:
        query = urllib.parse.urlencode(
            {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()},
            doseq=True
        )
        authorization_response = f"{redirect_uri}?{query}"
        try:
            flow.fetch_token(authorization_response=authorization_response)
        except InvalidGrantError:
            # code used/expired: reset, start over
            _clear_query_params()
            st.session_state.oauth_code_exchanged = False
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent select_account",
            )
            st.link_button("Continue with Google", auth_url)
            st.stop()
        except Exception as e:
            st.error(
                "Failed to fetch token. Ensure this exact redirect URI "
                f"is in your OAuth client:\n{redirect_uri}\n\nDetails: {e}"
            )
            _clear_query_params()
            st.stop()

        creds = flow.credentials
        # Save creds for THIS user (identified by id_token.sub)
        try:
            _save_creds_for_user(creds, client_id)
        except Exception as e:
            st.error(f"Could not save user token: {e}")
            _clear_query_params()
            st.stop()

        st.session_state.oauth_code_exchanged = True
        _clear_query_params()
        st.rerun()

    # If we have code but already exchanged it, wait for rerun to clean URL
    if code and st.session_state.oauth_code_exchanged:
        st.stop()

    # ---- Start OAuth (same tab)  force account chooser
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent select_account",
    )
    st.link_button("Continue with Google", auth_url)
    st.stop()

def get_model_instance(model_key):
    if not isinstance(model_key, str):
        return model_key
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

def passthrough(state:ModelState)->ModelState:
    return state

def write_email(state: ModelState) -> ModelState:
    print("writing email")
    parser = PydanticOutputParser(pydantic_object=GmailMessage)
    prompt = PromptTemplate(
        template=(
            "You are an expert email drafter, known for your ability to draft professional emails.\n\n"
            "Given candidate details:\n{candidate_details}\n\n"
            "Draft a professional email based on the job description:\n{jd}\n\n"
            "Required fields:\n"
            "  `to`: string\n"
            "  `subject`: string\n"
            "  `body`: string\n\n"
            "Return the output in STRICT format:\n{template}"
        ),
        input_variables=["candidate_details", "jd"],
        partial_variables={"template": parser.get_format_instructions()},
    )
    chain = prompt | get_model_instance(model_key=state.model) | parser
    output = chain.invoke({"candidate_details": state.candidate_details, "jd": state.jd})
    return {"gmail_message": output}


def convert_docx_to_pdf(state: ModelState) -> ModelState:
    """
    Converts DOCX -> PDF via Google Drive:
      1) Ensures OAuth ONCE with combined scopes (Drive+Gmail).
      2) Uploads DOCX as Google Doc.
      3) Exports to PDF and downloads.
      4) Returns pdf_file and saves creds for later Gmail usage.
    """
    if not state.docx_file or not os.path.exists(state.docx_file):
        return {"pdf_file": None}

    SCOPES = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    # --- Save intent BEFORE auth (so we can resume after redirect) ---
    st.session_state.oauth_pending_action = "convert_docx_to_pdf"
    st.session_state.oauth_payload = {"docx_file": state.docx_file}

    creds = state.gmail_auth_creds or ensure_google_creds(SCOPES)
    # If we got creds immediately (cached/refresh), we wont leave the page.
    # If we had to redirect, well return here after st.rerun().

    # Resume only once
    if st.session_state.oauth_pending_action == "convert_docx_to_pdf":
        # clear the pending marker so we don't loop
        st.session_state.oauth_pending_action = None
        payload = st.session_state.oauth_payload or {}
        st.session_state.oauth_payload = {}

        input_path = payload.get("docx_file") or state.docx_file
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.pdf"

        drive = build("drive", "v3", credentials=creds)

        # 1) Upload DOCX as Google Doc
        file_metadata = {
            "name": os.path.basename(input_path),
            "mimeType": "application/vnd.google-apps.document",
        }
        media = MediaFileUpload(
            input_path,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            resumable=True,
        )
        uploaded = drive.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        file_id = uploaded["id"]

        try:
            # 2) Export Google Doc to PDF
            request = drive.files().export_media(fileId=file_id, mimeType="application/pdf")
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            # 3) Save PDF
            with open(output_path, "wb") as f:
                f.write(fh.getvalue())

            # 4) Expose creds for downstream Gmail step
            return {"pdf_file": output_path, "gmail_auth_creds": creds}

        finally:
            # Cleanup temp Google Doc
            try:
                drive.files().delete(fileId=file_id).execute()
            except Exception:
                pass

    # If for some reason we're between legs
    return {}

def create_draft_with_gmail_auth(state: ModelState) -> ModelState:
    """
    Reuses OAuth creds (set during DOCX->PDF conversion).
    If not present, ensures creds silently via the same helper.
    Creates a Gmail draft with optional PDF attachment.
    """
    import os, base64, mimetypes
    from email.message import EmailMessage
    from googleapiclient.discovery import build

    # Reuse creds from state if available; else ensure them (no popup if token.pickle exists)
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]
    creds = state.gmail_auth_creds or ensure_google_creds(SCOPES)

    service = build("gmail", "v1", credentials=creds)

    # Compose email
    msg = EmailMessage()
    body = (state.gmail_message.body if state.gmail_message else None) or "Default message body"
    msg.set_content(body)

    profile = service.users().getProfile(userId="me").execute()
    from_addr = profile["emailAddress"]

    to_addr = (state.gmail_message.to if state.gmail_message and state.gmail_message.to else "example@example.com")
    subject = (state.gmail_message.subject if state.gmail_message and state.gmail_message.subject else "AI Test")

    msg["To"] = to_addr
    msg["From"] = from_addr
    msg["Subject"] = subject

    # Attach PDF if present
    if state.pdf_file and os.path.exists(state.pdf_file):
        ctype, _ = mimetypes.guess_type(state.pdf_file)
        main, sub = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        with open(state.pdf_file, "rb") as f:
            msg.add_attachment(f.read(), maintype=main, subtype=sub, filename=os.path.basename(state.pdf_file))

    # Create draft
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    print(f"✅ Draft created: ID = {draft['id']}")

    # Persist creds on state
    return {"gmail_auth_creds": creds}


def get_jd(state:ModelState)->ModelState:
    print("Getting JD")
    "Gets JD from the user"
    if state.jd and state.jd.raw_jd:
        return state
    jd_text=input("Enter the job description.")
    if len(jd_text)>0:
        jd=JD.model_construct(raw_jd=jd_text)
        return {"jd":jd}
    return {"jd":None}

def jd_provided(state:ModelState)->bool:
    return state.jd is not None

def fill_jd(state:ModelState)->ModelState:
    print("Filling JD")
    "Given the jd content it fills the JD pydantic get_model_instance(model_key=state.model) object"
    content=state.jd.raw_jd
    parser=PydanticOutputParser(pydantic_object=JD)
    prompt=PromptTemplate(template="""You are good at extracting and filling data in a given template.
                          Task is to fill template: \n{template}, based on given content:\n{content}, return the output in STRICT format :\n{template}"""
                          ,input_variables=["content"],partial_variables={"template":parser.get_format_instructions()})
    chain=prompt | get_model_instance(model_key=state.model) | parser
    output=chain.invoke({"content":content})
    return {"jd":output}


#Helpers
def read_pdf(state: ModelState) -> ModelState:
    print("reading pdf")
    """Reads a PDF and returns a Details object with text in `thought`."""

    reader = PdfReader(state.file_path)
    content = "\n".join(page.extract_text() or "" for page in reader.pages)
    return {"thought": content}

def find_missing(state: ModelState):
    print("finding missing")
    template_parser = PydanticOutputParser(pydantic_object=Details)
    prompt = PromptTemplate(
        template="""
You are a resume evaluator.

Given the following extracted resume information:\n
{resume}
\n
And the required structured format:\n
{template}
\n
Identify the specific fields or types of information that are missing from the resume but are required to fully complete the given template.

For example, if work experience dates or job titles are absent, mention them.
ONLY mention missing items.
List the missing items clearly and concisely, separated by commas.
Only return the field names or types of data that are missing.
""",
        input_variables=["resume", "template"]
    )
    chain = prompt | get_model_instance(model_key=state.model) | StrOutputParser()
    output = chain.invoke({"resume": state.thought, "template": template_parser.get_format_instructions()})
    thought = state.thought + "\n" + output
    return {"thought": thought}

def ask_questions(state: ModelState):
    print("Making user questions")
    parser = PydanticOutputParser(pydantic_object=QuestionList)
    prompt = PromptTemplate(
        template="""
You are an AI assistant helping to improve a candidate's resume.
Given the raw resume {resume}
The following information is missing and needs to be collected:
{missing}

For each missing item, ask a clear and relevant question based on the resume to the user to gather that information. Give examples of possible answer in brackets.
Return your output in the following STRICT format:
{format}
""",
        input_variables=["missing","resume"],
        partial_variables={"format": parser.get_format_instructions()}
    )
    chain = prompt | get_model_instance(model_key=state.model) | parser
    thought = state.thought
    missing = thought.split("\n")[-1]
    previous_thought = "\n".join(thought.split("\n")[:-1])
    questions = chain.invoke({"missing": missing,"resume":previous_thought})
    return {"questions": questions}

def get_answers(state: ModelState):
    print("Getting user answers")

    for ques in state.questions.questions:
        a = input(ques.question)
        ques.answer = a  # ✅ Update in-place

    return {"questions": state.questions}  # ✅ Mutated questions list is returned

# --- Node 2: Fill State ---
def fill_details(state: ModelState) -> ModelState:
    print("filling details")
    """Extracts structured info from `thought` using Gemini + Pydantic parser."""
    parser = PydanticOutputParser(pydantic_object=Details)

    prompt = PromptTemplate(
        template=(
            """Given the candidate details :{candidate_data}\n
            Extract details ,fill and return the following STRICT format:\n{format_instructions}"""
        ),
        input_variables=["candidate_data"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    chain = prompt | get_model_instance(model_key=state.model) | parser
    output=chain.invoke({"candidate_data": state.thought})

    return {"candidate_details":output}

def resume_improvements(state: ModelState) -> ModelState:
    print("Improving resume with JD alignment...")
    call_id = uuid.uuid4().hex[:8]
    print(f"[resume_improvements] Call ID: {call_id}, has JD: {bool(state.jd)}, has Resume: {bool(state.thought)}")
    prompt = PromptTemplate(
        template="""You are an expert resume writer and job application optimizer.

Given the following:
- Job Description : {jd}
- Candidate's Resume: {thought}
- and missing data from resume in form of question answers:{questions}

Your task:
- Improve the resume using ONLY the information already present in the resume.
- Enhance grammar, spelling, and sentence flow.
- Use professional and high-impact action verbs.
- Ensure the resume aligns strongly with the job description.
- Focus on ATS optimization (use relevant keywords from the JD).
- DO NOT fabricate or introduce new experiences, skills, or qualifications.
- The final result must look professional and be compelling.
- Ensure the word count remains under 600 words.

Respond ONLY with the improved resume content.
""",
        input_variables=["jd", "thought","questions"]
    )

    chain = prompt | get_model_instance(model_key=state.model) | StrOutputParser()
    improved_resume = chain.invoke({"jd": state.jd, "thought": state.thought,"questions":state.questions})

    return {"thought": improved_resume}

def make_resume_docx(state: ModelState) -> ModelState:
    """
    Generates a clean, ATS-friendly resume (fixed bullet handling):
    - Single column, 0.5" margins
    - Centered name/contact + thin rule
    - Section headers in small-caps style
    - Dates right-aligned via borderless 2-col tables
    - SAFE bullet helper that never relies on doc.styles.get()
    """

    def fmt_date(d):
        if not d:
            return ""
        try:
            if isinstance(d, (date, datetime)):
                return d.strftime("%b %Y")
            for fmt in ("%Y-%m-%d", "%Y-%m", "%d-%m-%Y", "%m/%d/%Y", "%b %Y", "%B %Y", "%Y"):
                try:
                    return datetime.strptime(str(d), fmt).strftime("%b %Y")
                except Exception:
                    pass
            return str(d)
        except Exception:
            return str(d)

    def join_clean(items, sep=" • "):
        return sep.join([str(s) for s in items if s])

    doc = Document()

    # === Page & base font ===
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(10.5)

    # === Styles (idempotent) ===
    def ensure_style(name, base="Normal", size=10.5, bold=False, all_caps=False, color=RGBColor(0, 0, 0)):
        try:
            st = doc.styles[name]
        except KeyError:
            st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = doc.styles[base]
        st.font.name = "Calibri"
        st._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        st.font.size = Pt(size)
        st.font.bold = bold
        st.font.all_caps = all_caps
        st.font.color.rgb = color
        st.paragraph_format.space_before = Pt(0)
        st.paragraph_format.space_after = Pt(2)
        st.paragraph_format.line_spacing = 1.05
        return st

    ensure_style("SectionHeader", size=10, bold=True, all_caps=True, color=RGBColor(45, 45, 45))
    ensure_style("HeaderName", size=20, bold=True, all_caps=True)
    ensure_style("HeaderContact", size=10)
    ensure_style("Tight", size=10.5)

    def set_spacing(p, before=0, after=2, line=1.05):
        pf = p.paragraph_format
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = line

    # Bullet helper that never fails
    def add_bullet(text: str):
        # Try to use the built-in numbered/bulleted style if present
        try:
            _ = doc.styles["List Bullet"]  # will raise KeyError if missing
            p = doc.add_paragraph(text, style="List Bullet")
            # tighten spacing & indent
            pf = p.paragraph_format
            pf.left_indent = Inches(0.2)
            pf.first_line_indent = Inches(-0.12)
            set_spacing(p, before=0, after=2, line=1.05)
            return p
        except KeyError:
            # Fallback: render a visual bullet
            p = doc.add_paragraph(u"\u2022 " + str(text), style="Tight")
            pf = p.paragraph_format
            pf.left_indent = Inches(0.2)
            pf.first_line_indent = Inches(0)
            set_spacing(p, before=0, after=2, line=1.05)
            return p

    # Hyperlink helper
    def add_hyperlink(paragraph, text, url):
        part = paragraph.part
        r_id = part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)

        new_run = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "1155CC")
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(color)
        rPr.append(u)
        new_run.append(rPr)
        text_node = OxmlElement("w:t")
        text_node.text = text
        new_run.append(text_node)
        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)
        return paragraph

    # Borderless 2-col row (left text + right text)
    def add_row_2col(left_text, right_text, left_bold=False):
        table = doc.add_table(rows=1, cols=2)

        # remove borders
        tbl = table._tbl
        tblPr = tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "nil")
            borders.append(e)
        tblPr.append(borders)

        # column widths
        try:
            table.columns[0].width = Inches(5.8)
            table.columns[1].width = Inches(1.6)
        except Exception:
            pass  # width setting can be flaky; safe to ignore

        left, right = table.rows[0].cells
        p_left = left.paragraphs[0]
        run_left = p_left.add_run(left_text)
        run_left.bold = left_bold
        set_spacing(p_left, after=0)

        p_right = right.paragraphs[0]
        p_right.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        p_right.add_run(right_text)
        set_spacing(p_right, after=0)

        return table

    # Thin rule under header
    def add_rule():
        t = doc.add_table(rows=1, cols=1)
        tbl = t._tbl
        tblPr = tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "right", "insideH", "insideV"):
            e = OxmlElement(f"w:{edge}")
            e.set(qn("w:val"), "nil")
            borders.append(e)
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:color"), "999999")
        borders.append(bottom)
        tblPr.append(borders)
        t.rows[0].cells[0].paragraphs[0].add_run("")
        set_spacing(t.rows[0].cells[0].paragraphs[0], after=6)

    # === Header ===
    if getattr(state.candidate_details, "name", None):
        name_para = doc.add_paragraph(style="HeaderName")
        name_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        name_para.add_run(state.candidate_details.name.upper())
        set_spacing(name_para, after=2)

    contact_para = doc.add_paragraph(style="HeaderContact")
    contact_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    contact_bits = []

    if getattr(state.candidate_details, "email", None):
        contact_bits.append(("mailto:" + state.candidate_details.email, state.candidate_details.email))
    if getattr(state.candidate_details, "phone", None):
        contact_bits.append(("tel:" + state.candidate_details.phone, state.candidate_details.phone))
    profiles = getattr(state.candidate_details, "profiles", []) or []
    for prof in profiles:
        url = getattr(prof, "url", None) if hasattr(prof, "url") else str(prof)
        if url:
            contact_bits.append((url, url))

    for i, (url, text) in enumerate(contact_bits):
        add_hyperlink(contact_para, text, url)
        if i < len(contact_bits) - 1:
            contact_para.add_run("  •  ")
    set_spacing(contact_para, after=6)
    add_rule()

    # === Summary ===
    summary = getattr(state.candidate_details, "summary", None)
    if summary:
        p = doc.add_paragraph("Summary", style="SectionHeader")
        p.paragraph_format.keep_with_next = True
        doc.add_paragraph(summary, style="Tight")

    # === Skills ===
    skills = getattr(state.candidate_details, "skills", None)
    if skills:
        p = doc.add_paragraph("Skills", style="SectionHeader")
        p.paragraph_format.keep_with_next = True
        doc.add_paragraph(join_clean(list(map(str, skills))), style="Tight")

    # === Experience ===
    experience = getattr(state.candidate_details, "experience", None)
    if experience:
        p = doc.add_paragraph("Professional Experience", style="SectionHeader")
        p.paragraph_format.keep_with_next = True

        for exp in experience:
            title = getattr(exp, "title", "") or ""
            company = getattr(exp, "company", "") or ""
            location = getattr(exp, "location", "") or ""
            sd = fmt_date(getattr(exp, "start_date", ""))
            ed_raw = getattr(exp, "end_date", None)
            ed = fmt_date(ed_raw) if ed_raw else "Present"

            left_line = join_clean([s for s in [title, company] if s], sep=", ")
            right_line = join_clean([s for s in [location] if s], sep="")

            add_row_2col(left_line, f"{sd} – {ed}", left_bold=True)
            if right_line:
                add_row_2col("", right_line)

            responsibilities = getattr(exp, "responsibilities", None) or []
            for item in responsibilities:
                add_bullet(str(item))

    # === Projects ===
    projects = getattr(state.candidate_details, "projects", None)
    if projects:
        p = doc.add_paragraph("Projects", style="SectionHeader")
        p.paragraph_format.keep_with_next = True

        for proj in projects:
            name = getattr(proj, "name", "") or ""
            techs = getattr(proj, "technologies", None) or []
            descr = getattr(proj, "description", "") or ""
            date_txt = fmt_date(getattr(proj, "date", "")) if getattr(proj, "date", None) else ""
            link = getattr(proj, "link", None)

            header_left = join_clean([name, f"({date_txt})" if date_txt else ""], sep=" ")
            add_row_2col(header_left, "", left_bold=True)

            if descr:
                doc.add_paragraph(descr, style="Tight")
            if techs:
                doc.add_paragraph("Technologies: " + ", ".join(map(str, techs)), style="Tight")
            if link:
                lp = doc.add_paragraph(style="Tight")
                add_hyperlink(lp, str(link), str(link))

    # === Education ===
    education = getattr(state.candidate_details, "education", None)
    if education:
        p = doc.add_paragraph("Education", style="SectionHeader")
        p.paragraph_format.keep_with_next = True

        for edu in education:
            degree = getattr(edu, "degree", "") or ""
            institute = getattr(edu, "institute", "") or ""
            sd = fmt_date(getattr(edu, "start_date", ""))
            ed_raw = getattr(edu, "end_date", None)
            ed = fmt_date(ed_raw) if ed_raw else "Present"
            left = join_clean([degree, institute], sep=", ")
            add_row_2col(left, f"{sd} – {ed}")

            gpa = getattr(edu, "gpa", None)
            if gpa:
                doc.add_paragraph(f"GPA: {gpa}", style="Tight")
            coursework = getattr(edu, "coursework", None)
            if coursework:
                doc.add_paragraph("Relevant coursework: " + ", ".join(map(str, coursework)), style="Tight")

    # === Certifications ===
    certs = getattr(state.candidate_details, "certifications", None)
    if certs:
        p = doc.add_paragraph("Certifications", style="SectionHeader")
        p.paragraph_format.keep_with_next = True
        for cert in certs:
            name = getattr(cert, "name", "") or ""
            issuer = getattr(cert, "issuer", "") or ""
            cdate = fmt_date(getattr(cert, "date", "")) if getattr(cert, "date", None) else ""
            left = join_clean([name, issuer], sep=" — ")
            add_row_2col(left, cdate)

    # === Save ===
    base = getattr(state, "file_path", None) or "resume.docx"
    root, _ = os.path.splitext(base)
    output_path = root + ".docx"
    doc.save(output_path)
    return {"docx_file": output_path}


def is_email_in_jd(state:ModelState):
    if state.jd.email and "@" in state.jd.email:
        return "email_present"
    else:
        return "email_absent"

def write_referral(state: ModelState):
    prompt = PromptTemplate.from_template("""
You are a job applicant seeking a referral. Write a short and professional LinkedIn-style referral message (60–100 words max) to someone working at the company.

Use the following:
- Job Description:
{jd}

- Resume Summary:
{resume}

Write in a polite, concise tone. Don't assume familiarity.
""")

    chain = (
        prompt
        | get_model_instance(model_key=state.model)  # or whatever LLM you use
        | StrOutputParser()
    )

    output = chain.invoke({
        "jd": state.jd,
        "resume": state.thought
    })

    return {"referral_message": output}
