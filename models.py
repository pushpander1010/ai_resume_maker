from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List,Any,Annotated
# --- Models ---
class Experience(BaseModel):
    title: Optional[str] = Field(default=None,description="Job title or role")
    company: Optional[str] = Field(default=None,description="Company name")
    start_date: Optional[str] = Field(default=None,description="Start date of employment")
    end_date: Optional[str] = Field(default=None,description="End date of employment")
    responsibilities: Optional[List[str]] = Field(default=None,description="List of responsibilities or achievements")

class Certification(BaseModel):
    name: Optional[str] = Field(default=None,description="Name of the certification")
    issuer: Optional[str] = Field(default=None,description="Issuing organization")
    date: Optional[str] = Field(default=None,description="Date of certification")

class Profile(BaseModel):
    platform: Optional[str] = Field(default=None,description="Name of the platform (e.g., LinkedIn, GitHub)")
    url: Optional[str] = Field(default=None,description="URL to the candidate's profile")

class Education(BaseModel):
    degree: Optional[str] = Field(default=None,description="Name of the degree")
    start_date: Optional[str] = Field(default=None,description="Start date of education")
    end_date: Optional[str] = Field(default=None,description="End date of education")
    percentage: Optional[str] = Field(default=None,description="Percentage of the candidate")
    institute: Optional[str] = Field(default=None,description="Name of the education institute")

class Project(BaseModel):
    name: Optional[str] = Field(default=None,description="Name of the project")
    description: Optional[str] = Field(default=None,description="Brief description of the project")
    technologies: Optional[List[str]] = Field(default=None,description="List of technologies or tools used")
    role: Optional[str] = Field(default=None,description="Role or responsibility in the project")
    outcome: Optional[str] = Field(default=None,description="Impact, results, or achievements from the project")
    date:Optional[str]=Field(default=None,description="Date of the project")
    link: Optional[str] = Field(default=None,description="URL to the project demo, repo, or publication")

class Details(BaseModel):
    name: Optional[str] = Field(default=None,description="Name of the candidate")
    summary: Optional[str] = Field(default=None,description="Brief Summary of the candidate")
    phone: Optional[str] = Field(default=None,description="Phone number of the candidate")
    email: Optional[EmailStr] = Field(default=None,description="Email of the candidate")
    address: Optional[str] = Field(default=None,description="Address of the candidate")
    skills: Optional[List[str]] = Field(default=None,description="List of skills of candidate")
    education: Optional[List[Education]] = Field(default=None,description="Education qualifications of candidate")
    experience: Optional[List[Experience]] = Field(default=None,description="Experiences of the candidate")
    certifications: Optional[List[Certification]] = Field(default=None,description="Certifications of the candidate")
    projects:Optional[List[Project]]=Field(default=None,description="projects worked on by candidate")
    profiles: Optional[List[Profile]] = Field(default=None,description="Profiles of the candidate")

class JD(BaseModel):
    raw_jd: Optional[str] = Field(default=None,description="Raw jd provided by the user")
    title: Optional[str] = Field(default=None,description="Title of the job role")
    company: Optional[str] = Field(default=None,description="Name of the hiring company")
    location: Optional[str] = Field(default=None,description="Job location (city, remote, etc.)")
    responsibilities: Optional[List[str]] = Field(default=None,description="List of job responsibilities")
    qualifications: Optional[List[str]] = Field(default=None,description="List of required qualifications or skills")
    experience_required: Optional[str] = Field(default=None,description="Experience requirement for the role")
    employment_type: Optional[str] = Field(default=None,description="Type of employment (Full-time, Contract, etc.)")
    salary_range: Optional[str] = Field(default=None,description="Offered salary or range")
    perks: Optional[List[str]] = Field(default=None,description="List of benefits or perks")
    description: Optional[str] = Field(default=None,description="Full raw job description text")
    email:Optional[EmailStr]=Field(default=None, description="email to post the resume")

class GmailMessage(BaseModel):
    to: Optional[EmailStr] = Field(default=None, description="Recipient email address")
    subject: Optional[str] = Field(default=None, description="Subject of the email")
    body: Optional[str] = Field(default=None, description="Body content of the email")

class Question(BaseModel):
    question:Optional[str]=Field(default=None,description="question to be asked regarding the missing data in resume.")
    answer:Optional[str]=Field(default=None,description="answer to the asked question regarding the missing data in resume.")
    
class QuestionList(BaseModel):
    questions:Optional[list[Question]]=Field(default=None,description="list of questions to be asked regarding the missing data in resume.")

class ModelState(BaseModel):
    model:Optional[Any]=Field(default="google|gemini-2.5-flash", description="model to be used by the agents")
    thought: Annotated[Optional[str],lambda x,y:y] = Field(default=None,description="temp variable to store output of previous node")
    file_path:Optional[str]=Field(default=None,description="path of the file")
    resume_format: Optional[str] = Field(default="fmt1", description="selected resume docx format id: fmt1..fmt5")
    candidate_details:Optional[Details]=Field(default=None,description="Relevant Details of the candidate")
    jd:Optional[JD]=Field(default=None,description="job description of the job")
    docx_file:Optional[str]=Field(default=None,description="path of the word document file")
    pdf_file:Optional[str]=Field(default=None,description="path of the pdf document file")
    gmail_auth_creds:Optional[Any]=Field(default=None,description="gmail service object")
    gmail_message:Optional[GmailMessage]=Field(default=None,description="email to be sent to hr")
    referral_message:Optional[str]=Field(default=None,description="referral message to be sent to hr")
    questions:Optional[QuestionList]=Field(default=None,description="list of questions and answers to be asked regarding the missing data in resume.")
