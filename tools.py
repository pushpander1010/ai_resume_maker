from docx2pdf import convert
from models import ModelState,Details,JD,GmailMessage,Question,QuestionList
from langchain_community.document_loaders import TextLoader
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import json
import docx
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


load_dotenv()

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


def passthrough(state:ModelState)->ModelState:
    return state

def write_email(state:ModelState)->ModelState:
    print("writing email")
    parser=PydanticOutputParser(pydantic_object=GmailMessage)
    prompt=PromptTemplate(template="""You are an expert email drafter, known for your ability draft professional emails,
                           given candidate details:\n{candidate_details} \n Draft a professional email based on the the job description:\n{jd}
                            \nfollowing data is required:\n
                          `to`: string type \n
                        `subject`: string type \n
                          `body`: string type \n
                          \n return the output in STRICT format :\n{template}""",input_variables=["candidate_details","jd"],partial_variables={"template":parser.get_format_instructions()})
    chain=prompt | state.model | parser
    output=chain.invoke({"candidate_details":state.candidate_details,"jd":state.jd})
    return {"gmail_message":output}

def create_draft_with_gmail_auth(state: ModelState) -> ModelState:
    print("making draft")
    credentials_dict = {
    "installed": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "project_id":"agentic-resumer",
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs"
    }
}

    with open("credentials.json", "w") as f:
        json.dump(credentials_dict, f)

    """
    Authenticate with Gmail and create a draft message with optional attachments.
    """

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose'
    ]

    creds = None

    # Step 1: Authenticate
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Step 2: Create Gmail API service
    service = build("gmail", "v1", credentials=creds)

    # Step 3: Compose email
    message = EmailMessage()
    message.set_content(state.gmail_message.body or "Default message body")

    user_info = service.users().getProfile(userId='me').execute()
    gmail_address = user_info['emailAddress']

    message["To"] = state.gmail_message.to if state.gmail_message else "sks96439@gmail.com"
    message["From"] = gmail_address
    message["Subject"] = state.gmail_message.subject if state.gmail_message else "AI Test"

    # Step 4: Attach file(s) if available
    if state.pdf_file:
        file_path = state.pdf_file
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_data = f.read()

        message.add_attachment(file_data, maintype=main_type, subtype=sub_type, filename=filename)
        print(f"📎 Attached: {filename}")

    # Step 5: Encode and create draft
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"message": {"raw": encoded_message}}

    draft = (
        service.users()
        .drafts()
        .create(userId="me", body=create_message)
        .execute()
    )

    print(f"✅ Draft created: ID = {draft['id']}")

    # Step 6: Return updated state
    return {"gmail_auth_creds": creds}

def get_jd(state:ModelState)->ModelState:
    print("Getting JD")
    "Gets JD from the user"
    if state.jd and state.jd.raw_jd:
        return state
    jd_text=input("Enter the job description.")
    if len(jd_text)>0:
        jd=JD.state.model_construct(raw_jd=jd_text)
        return {"jd":jd}
    return {"jd":None}

def jd_provided(state:ModelState)->bool:
    return state.jd is not None

def fill_jd(state:ModelState)->ModelState:
    print("Filling JD")
    "Given the jd content it fills the JD pydantic state.model object"
    content=state.jd.raw_jd
    parser=PydanticOutputParser(pydantic_object=JD)
    prompt=PromptTemplate(template="""You are good at extracting and filling data in a given template.
                          Task is to fill template: \n{template}, based on given content:\n{content}, return the output in STRICT format :\n{template}"""
                          ,input_variables=["content"],partial_variables={"template":parser.get_format_instructions()})
    chain=prompt | state.model | parser
    output=chain.invoke({"content":content})
    return {"jd":output}

def convert_docx_to_pdf(state: ModelState) -> ModelState:
    print("converting docx to pdf")
    "Converts docx file to pdf file"
    input_path=state.docx_file
    output_path=input_path.split(".")[0]+"_.pdf"
    convert(input_path=input_path,output_path=output_path)
    return {"pdf_file":output_path}

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
    chain = prompt | state.model | StrOutputParser()
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
    chain = prompt | state.model | parser
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

    chain = prompt | state.model | parser
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

    chain = prompt | state.model | StrOutputParser()
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
        | state.model  # or whatever LLM you use
        | StrOutputParser()
    )

    output = chain.invoke({
        "jd": state.jd,
        "resume": state.thought
    })

    return {"referral_message": output}
