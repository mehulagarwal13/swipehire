"""
Resume AI rewriter — Premium feature.

Given a user's profile + a target job, uses Gemini to:
  1. Rewrite the professional summary/objective to mirror the job's language
  2. Suggest which skills to highlight (from user's existing skills)
  3. Rephrase 1–2 experience bullet points to match job requirements
  4. Generate a tailored cover letter paragraph

All rewrites are non-destructive — original data is never overwritten.
Returns a RewriteResult with the tailored sections only.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from config import settings

log = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    _gemini = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"temperature": 0.4, "max_output_tokens": 1500},
    )
except Exception:
    _gemini = None


@dataclass
class RewriteResult:
    summary: str                    # Rewritten professional summary
    highlighted_skills: list[str]   # Top 5–7 skills to feature for this job
    tailored_bullets: list[str]     # 3 rephrased experience bullet points
    cover_letter: str               # 1-paragraph tailored cover letter
    ats_keywords: list[str]         # ATS keywords from job description to include
    match_tips: list[str]           # 2–3 tips to improve this specific application


_REWRITE_PROMPT = """
You are an expert Indian resume coach helping a job seeker tailor their resume for a specific role.

USER PROFILE:
Name: {full_name}
Current headline: {headline}
Skills: {skills}
Experience ({exp_years} years):
{experience}
Education:
{education}

TARGET JOB:
Title: {job_title}
Company: {company}
Description:
{job_description}
Required Skills: {required_skills}

Your task — return ONLY valid JSON with these exact keys:

{{
  "summary": "2–3 sentence professional summary tailored to this specific job. Use keywords from the job description. Written in first person. Mention the company by name.",
  "highlighted_skills": ["skill1", "skill2", ...],
  "tailored_bullets": [
    "• Rephrased experience bullet 1 — use action verbs, quantify where possible",
    "• Rephrased experience bullet 2",
    "• Rephrased experience bullet 3"
  ],
  "cover_letter": "One paragraph (4–5 sentences) cover letter opening. Mention the specific role, company, and why this candidate is a great fit. Professional but warm tone.",
  "ats_keywords": ["keyword1", "keyword2", ...],
  "match_tips": [
    "Tip to improve this application",
    "Another specific tip"
  ]
}}

Important: Only use skills and experience the candidate actually has. Do not invent credentials.
Return ONLY the JSON object, no markdown.
"""


async def rewrite_resume_for_job(
    profile,   # UserProfile model
    user,      # User model
    job,       # Job model
) -> RewriteResult:
    """
    Main entry point — tailors resume content for a specific job.
    Raises ValueError if LLM fails.
    """
    # Build experience text
    exp_text = ""
    for exp in (profile.experience or []):
        if isinstance(exp, dict):
            exp_text += f"- {exp.get('role')} at {exp.get('company')}: {exp.get('description', '')[:200]}\n"

    edu_text = ""
    for edu in (profile.education or []):
        if isinstance(edu, dict):
            edu_text += f"- {edu.get('degree')} from {edu.get('college')} ({edu.get('year', '')})\n"

    prompt = _REWRITE_PROMPT.format(
        full_name=user.full_name or "Candidate",
        headline=profile.headline or "",
        skills=", ".join(profile.skills or []),
        exp_years=profile.experience_years or 0,
        experience=exp_text or "Not provided",
        education=edu_text or "Not provided",
        job_title=job.title,
        company=job.company,
        job_description=(job.description or "")[:1500],
        required_skills=", ".join(job.skills_required or []),
    )

    raw = await _call_llm(prompt)
    return _parse_result(raw)


async def _call_llm(prompt: str) -> str:
    """Call Gemini with Groq fallback."""
    if _gemini:
        try:
            response = _gemini.generate_content(prompt)
            return response.text
        except Exception as e:
            log.warning("Gemini failed, trying Groq: %s", e)

    # Groq fallback
    if settings.groq_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 1500,
                },
            )
            return resp.json()["choices"][0]["message"]["content"]

    raise ValueError("No LLM configured. Set GEMINI_API_KEY or GROQ_API_KEY.")


def _parse_result(raw: str) -> RewriteResult:
    # Strip markdown code blocks if present
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("LLM returned non-JSON response")

    data = json.loads(match.group())
    return RewriteResult(
        summary=data.get("summary", ""),
        highlighted_skills=data.get("highlighted_skills", []),
        tailored_bullets=data.get("tailored_bullets", []),
        cover_letter=data.get("cover_letter", ""),
        ats_keywords=data.get("ats_keywords", []),
        match_tips=data.get("match_tips", []),
    )
