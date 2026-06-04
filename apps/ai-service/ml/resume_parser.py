"""
Resume parsing pipeline:
1. PDF/DOCX → raw text  (pdfplumber + python-docx + Tesseract OCR fallback)
2. Raw text → structured JSON  (Gemini 1.5 Flash)
3. Return ParsedResume pydantic model
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import httpx
import pdfplumber
import pytesseract
from PIL import Image
from docx import Document
from pydantic import BaseModel, Field

from config import settings

try:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    _gemini = genai.GenerativeModel("gemini-1.5-flash")
except Exception:
    _gemini = None  # fallback to Groq below


class EducationEntry(BaseModel):
    degree: str = ""
    college: str = ""
    year: int | None = None
    cgpa: float | None = None


class ExperienceEntry(BaseModel):
    company: str = ""
    role: str = ""
    duration: str = ""
    description: str = ""


class ProjectEntry(BaseModel):
    name: str = ""
    stack: str = ""
    link: str = ""
    description: str = ""


class ParsedResume(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    headline: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0.0
    current_location: str = ""
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


# ─── Text extraction ──────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    text = ""
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

    # Fallback: OCR if pdfplumber got nothing (scanned PDF)
    if len(text.strip()) < 100:
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=200).original
                text += pytesseract.image_to_string(img) + "\n"

    Path(tmp_path).unlink(missing_ok=True)
    return text.strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    doc = Document(tmp_path)
    text = "\n".join(p.text for p in doc.paragraphs)
    Path(tmp_path).unlink(missing_ok=True)
    return text.strip()


# ─── LLM parsing ──────────────────────────────────────────────────────────────

_PARSE_PROMPT = """
You are a resume parser. Extract structured data from the Indian resume text below.
Return ONLY valid JSON with these exact keys. Infer experience_years from work history dates.

{{
  "full_name": "",
  "email": "",
  "phone": "",
  "headline": "e.g. Full-stack Developer, 2 yrs",
  "skills": [],
  "experience_years": 0.0,
  "current_location": "",
  "education": [{{"degree":"","college":"","year":null,"cgpa":null}}],
  "experience": [{{"company":"","role":"","duration":"","description":""}}],
  "projects": [{{"name":"","stack":"","link":"","description":""}}],
  "certifications": []
}}

Resume text:
{resume_text}
"""


async def parse_resume_with_llm(resume_text: str) -> ParsedResume:
    prompt = _PARSE_PROMPT.format(resume_text=resume_text[:6000])

    raw_json = ""
    if _gemini:
        response = _gemini.generate_content(prompt)
        raw_json = response.text
    else:
        # Groq fallback
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=30,
            )
            raw_json = resp.json()["choices"][0]["message"]["content"]

    # Extract JSON block from response (LLMs sometimes wrap in markdown)
    match = re.search(r"\{.*\}", raw_json, re.DOTALL)
    if not match:
        raise ValueError("LLM did not return valid JSON")

    data = json.loads(match.group())
    return ParsedResume(**data)


# ─── Public API ───────────────────────────────────────────────────────────────

async def parse_resume(file_bytes: bytes, content_type: str) -> ParsedResume:
    """End-to-end resume parsing: bytes → ParsedResume."""
    if "pdf" in content_type:
        text = extract_text_from_pdf(file_bytes)
    elif "word" in content_type or "docx" in content_type or "document" in content_type:
        text = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {content_type}")

    if not text:
        raise ValueError("Could not extract text from resume")

    return await parse_resume_with_llm(text)
