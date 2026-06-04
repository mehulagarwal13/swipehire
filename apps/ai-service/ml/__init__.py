from .embeddings import embed_profile, embed_job, embed_text
from .scorer import compute_match_score, ScoreDetails
from .recommender import rank_jobs_for_user, filter_by_preferences

# resume_parser depends on optional heavy OCR packages (pdfplumber, pytesseract, Pillow, python-docx)
# Import lazily so that the rest of the ML package works in test/CI environments without them.
try:
    from .resume_parser import parse_resume, ParsedResume
except ImportError:
    parse_resume = None  # type: ignore[assignment]
    ParsedResume = None  # type: ignore[assignment]

__all__ = [
    "embed_profile", "embed_job", "embed_text",
    "compute_match_score", "ScoreDetails",
    "rank_jobs_for_user", "filter_by_preferences",
    "parse_resume", "ParsedResume",
]
