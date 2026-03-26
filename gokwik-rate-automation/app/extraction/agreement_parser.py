"""Extract start date and agreement details from Agreement PDF (MSA/PSA).

Uses LLM (OpenAI) as primary extraction, falls back to pdfplumber regex.
Targets page 2 of the PDF for date extraction.

Also includes date calculation (end date = start date + 3 years),
merged from the former date_calculator module.
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional

import pdfplumber
from dateutil.relativedelta import relativedelta

from app.extraction.llm_extractor import extract_agreement_with_llm
from app.config import AGREEMENT_PAGE

logger = logging.getLogger(__name__)

# Date patterns from the docs (priority order)
DATE_PATTERNS = [
    # Keyword-based (most reliable)
    r'(?:effective|commencement|start|agreement)\s*date[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
    r'(?:effective|commencement|start|agreement)\s*date[:\s]*(\d{1,2}\s+\w+\s+\d{4})',
    r'dated?\s+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
    r'dated?\s+(\d{1,2}\s+\w+\s+\d{4})',
    # Standalone dates (less specific, fallback)
    r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b',
    r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
]

# Indian date format first (DD/MM/YYYY), then US fallback (MM/DD/YYYY)
DATE_FORMATS = [
    '%d/%m/%Y',
    '%d-%m-%Y',
    '%d/%m/%y',
    '%d-%m-%y',
    '%d %B %Y',
    '%d %b %Y',
    '%m/%d/%Y',
    '%m-%d-%Y',
]


def _parse_date(date_str: str) -> Optional[datetime]:
    """Try multiple date formats to parse a date string. Indian DD/MM/YYYY tried first."""
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # Sanity check: year should be between 2000 and 2050
            if 2000 <= parsed.year <= 2050:
                return parsed
        except ValueError:
            continue
    return None


def _extract_text_from_page(pdf_path: str, target_page: Optional[int] = None) -> str:
    """Extract text from specific page or all pages."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        if target_page is not None and 1 <= target_page <= total_pages:
            pages = [pdf.pages[target_page - 1]]
        else:
            pages = pdf.pages

        for page in pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text


def extract_start_date(pdf_path: str) -> Optional[str]:
    """
    Extract the agreement start date from a PDF.
    LLM first (targets page 2), then regex fallback.
    Returns date as YYYY-MM-DD string, or None if not found.
    """
    # Try LLM extraction first (targets page 2 internally)
    print("[Agreement Parser] Attempting LLM extraction...")
    llm_data = extract_agreement_with_llm(pdf_path)
    if llm_data and llm_data.get("start_date"):
        print(f"[Agreement Parser] LLM extracted start_date: {llm_data['start_date']}")
        return llm_data["start_date"]

    print("[Agreement Parser] LLM unavailable or failed, falling back to regex...")

    # Fallback: regex extraction from page 2 first
    full_text = _extract_text_from_page(pdf_path, target_page=AGREEMENT_PAGE)
    if not full_text.strip():
        # Try all pages if page 2 is empty
        full_text = _extract_text_from_page(pdf_path)

    if not full_text.strip():
        return None

    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        for match in matches:
            parsed = _parse_date(match)
            if parsed:
                return parsed.strftime('%Y-%m-%d')

    return None


def extract_agreement_info(pdf_path: str) -> dict:
    """
    Extract all relevant info from Agreement PDF.
    LLM provides richer data (merchant_size, merchant_type, products).
    """
    # Try LLM for full extraction (targets page 2 internally)
    llm_data = extract_agreement_with_llm(pdf_path)
    if llm_data and llm_data.get("start_date"):
        return {
            "start_date": llm_data["start_date"],
            "file_name": os.path.basename(pdf_path),
            "merchant_size": llm_data.get("merchant_size", "Long Tail"),
            "merchant_type": llm_data.get("merchant_type", "D2C"),
            "purchased_products": llm_data.get("purchased_products", ["Checkout"]),
        }

    # Fallback
    start_date = extract_start_date(pdf_path)
    return {
        "start_date": start_date,
        "file_name": os.path.basename(pdf_path),
    }


def calculate_end_date(start_date_str: str) -> str:
    """
    Given a start date in YYYY-MM-DD format, return end date (start + 3 years).
    Returns YYYY-MM-DD string.
    Handles invalid input gracefully.
    """
    try:
        start = datetime.strptime(start_date_str, '%Y-%m-%d')
        end = start + relativedelta(years=3)
        return end.strftime('%Y-%m-%d')
    except (ValueError, TypeError) as e:
        print(f"[Date Calculator] Invalid date '{start_date_str}': {e}")
        return start_date_str  # Return as-is if parsing fails
