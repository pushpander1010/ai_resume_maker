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

TOKEN_PATH = "token.pickle"

def sign_out():
    """Clear local token & session state."""
    try:
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
    except Exception:
        pass
    for k in ("user_email", "user_name", "oauth_code_exchanged"):
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

def _clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()

def ensure_google_creds(scopes: list[str], *, force_refresh: bool = False) -> Credentials:
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")

    # ... keep your existing guardrails & cached-token logic ...

    flow = Flow.from_client_config(client_config, scopes=scopes)
    flow.redirect_uri = redirect_uri

    if code and not st.session_state.get("oauth_code_exchanged"):
        # ... your existing fetch_token code ...
        creds = flow.credentials

        # NEW: extract name/email from ID token (requires openid/email/profile scopes)
        try:
            if not creds.id_token:
                creds.refresh(Request())
            claims = google_id_token.verify_oauth2_token(
                creds.id_token, google_requests.Request(), client_id
            )
            st.session_state.user_email = claims.get("email")
            st.session_state.user_name = claims.get("name") or st.session_state.user_email
        except Exception:
            # best-effort: just leave blanks if decoding fails
            st.session_state.user_email = st.session_state.get("user_email") or ""
            st.session_state.user_name  = st.session_state.get("user_name") or st.session_state.user_email

        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

        st.session_state.oauth_code_exchanged = True
        _clear_query_params()
        st.rerun()

    # ... your existing “kick off OAuth” block ...

    return creds  # when cached/valid

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
    print("Making word docx file")
    doc = Document()

    # === Format settings ===
    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    # Font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Calibri')
    font.size = Pt(10)

    # === Helpers ===
    def set_spacing(p):
        fmt = p.paragraph_format
        fmt.space_before = Pt(2)
        fmt.space_after = Pt(2)
        fmt.line_spacing = 1.0

    def add_title(text: str):
        p = doc.add_paragraph(text.upper())
        p.runs[0].bold = True
        set_spacing(p)

    def add_bullets(items: list[str]):
        for item in items:
            p = doc.add_paragraph(item, style='List Bullet')
            set_spacing(p)

    def add_hyperlink(paragraph, text, url):
        part = paragraph.part
        r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
        hyperlink = OxmlElement('w:hyperlink')
        hyperlink.set(qn('r:id'), r_id)

        new_run = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        color = OxmlElement('w:color')
        color.set(qn('w:val'), "000000")
        u = OxmlElement('w:u')
        u.set(qn('w:val'), "none")
        rPr.append(color)
        rPr.append(u)
        new_run.append(rPr)
        text_node = OxmlElement('w:t')
        text_node.text = text
        new_run.append(text_node)
        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)
        return paragraph

    # === Header ===
    if state.candidate_details.name:
        name_para = doc.add_paragraph(state.candidate_details.name.upper())
        name_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        name_para.runs[0].bold = True
        name_para.runs[0].font.size = Pt(20)
        set_spacing(name_para)

        contact = doc.add_paragraph()
        contact.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    if state.candidate_details.email:
        add_hyperlink(contact, state.candidate_details.email, f"mailto:{state.candidate_details.email}")
        contact.add_run(" | ")

    if state.candidate_details.phone:
        add_hyperlink(contact, state.candidate_details.phone, f"tel:{state.candidate_details.phone}")
        contact.add_run(" | ")
    if state.candidate_details.profiles:
        for i, profile in enumerate(state.candidate_details.profiles):
            add_hyperlink(contact, profile.url, profile.url)
            if i < len(state.candidate_details.profiles) - 1:
                contact.add_run(" | ")
        set_spacing(contact)

    # === Summary ===
    if state.candidate_details.summary:
        add_title("Summary")
        p = doc.add_paragraph(state.candidate_details.summary)
        set_spacing(p)

    # === Skills ===
    if state.candidate_details.skills:
        add_title("Skills")
        p = doc.add_paragraph(", ".join(state.candidate_details.skills))
        set_spacing(p)

    # === Experience ===
    if state.candidate_details.experience:
        add_title("Professional Experience")
        for exp in state.candidate_details.experience:
            title_line = f"{exp.title}, {exp.company} ({exp.start_date} - {exp.end_date or 'Present'})"
            p = doc.add_paragraph(title_line)
            p.runs[0].bold = True
            set_spacing(p)
            add_bullets(exp.responsibilities)

    # === Projects ===
    if state.candidate_details.projects:
        add_title("Projects")
        for proj in state.candidate_details.projects:
            title_line = f"{proj.name} ({proj.date or ''})"
            p = doc.add_paragraph(title_line)
            p.runs[0].bold = True
            set_spacing(p)
            p = doc.add_paragraph(proj.description)
            set_spacing(p)
            if proj.technologies:
                p = doc.add_paragraph("Technologies: " + ", ".join(proj.technologies))
                set_spacing(p)
            if proj.link:
                p = doc.add_paragraph()
                add_hyperlink(p, proj.link, proj.link)
                set_spacing(p)

    # === Education ===
    if state.candidate_details.education:
        add_title("Education")
        for edu in state.candidate_details.education:
            line = f"{edu.degree}, {edu.institute or ''} ({edu.start_date} - {edu.end_date or 'Present'})"
            p = doc.add_paragraph(line)
            set_spacing(p)

    # === Certifications ===
    if state.candidate_details.certifications:
        add_title("Certifications")
        for cert in state.candidate_details.certifications:
            line = f"{cert.name} - {cert.issuer or ''} ({cert.date or ''})"
            p = doc.add_paragraph(line)
            set_spacing(p)

    # === Save ===
    output_path = state.file_path.replace(".pdf", ".docx")
    doc.save(output_path)
    return {"docx_file":output_path}

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
