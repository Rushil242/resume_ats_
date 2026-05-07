from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class ContactInfo(BaseModel):
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    website: Optional[str] = ""

class BulletItem(BaseModel):
    text: str

class SectionItem(BaseModel):
    type: str  # "paragraph" | "job" | "project" | "education" | "skill_category" | "award"
    # job / project / education fields
    title: Optional[str] = None
    subtitle: Optional[str] = None
    location: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    bullets: Optional[List[str]] = []
    # paragraph / summary
    text: Optional[str] = None
    # skills
    category: Optional[str] = None
    skills: Optional[List[str]] = []

class ResumeSection(BaseModel):
    id: str            # e.g. "EXPERIENCE", "PROJECTS"
    title: str         # Display name e.g. "Work Experience"
    items: List[SectionItem] = []

class ResumeContent(BaseModel):
    name: str
    contact: ContactInfo
    sections: List[ResumeSection]

class StyleConfig(BaseModel):
    page_size: str = "A4"
    margins: Dict[str, float] = {"top": 1.5, "bottom": 1.5, "left": 1.8, "right": 1.8}
    columns: int = 1
    fonts: Dict[str, Any] = {}
    colors: Dict[str, str] = {}
    sections_order: List[str] = []
    section_styles: Dict[str, Any] = {}
    bullet_style: Dict[str, Any] = {}
    raw_description: str = ""  # Full LLM style description text

class ResumeAnalysisResult(BaseModel):
    resume_id: str
    style: StyleConfig
    content: ResumeContent
    roundtrip_pdf_url: Optional[str] = None

class TailorResult(BaseModel):
    job_id: str
    resume_id: str
    ats_score: Optional[float] = None
    missing_keywords: Optional[List[str]] = []
    matched_keywords: Optional[List[str]] = []
    content: ResumeContent
    tailored_pdf_url: Optional[str] = None
    tailored_tex_url: Optional[str] = None
