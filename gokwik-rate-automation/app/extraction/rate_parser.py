"""Extract payment mode rates from Rate PDF (Rate Card).

Uses LLM (OpenAI) as primary extraction, falls back to pdfplumber table/regex.
Targets page 2 of the PDF for rate data.
"""

import re
import logging
from typing import Optional

import pdfplumber

from app.extraction.llm_extractor import extract_rates_with_llm
from app.config import RATE_PAGE

logger = logging.getLogger(__name__)


def _normalize_header(header: str) -> str:
    """Normalize table header text for matching."""
    if not header:
        return ""
    return re.sub(r'\s+', ' ', header.strip().lower())


def _parse_percentage(value: str) -> Optional[float]:
    """Parse a percentage value like '2.5%' or '2.5' into a float."""
    if not value:
        return None
    value = value.strip().replace('%', '').replace('NIL', '0').replace('nil', '0').strip()
    try:
        rate = float(value)
        # Validate: rate must be 0-100 (percentage)
        if rate < 0 or rate > 100:
            return None
        return rate
    except ValueError:
        return None


def extract_rates(pdf_path: str) -> list[dict]:
    """
    Extract payment mode rates from a Rate PDF.

    Strategy: LLM first (OpenAI) -> pdfplumber tables -> regex fallback.
    All methods target page 2 first, falling back to all pages.
    Returns list of dicts: [{"mode": "UPI", "rate": 2.5}, ...]
    """
    # Try LLM extraction first (targets page 2 internally)
    print("[Rate Parser] Attempting LLM extraction...")
    llm_rates = extract_rates_with_llm(pdf_path)
    if llm_rates:
        print(f"[Rate Parser] LLM extracted {len(llm_rates)} rates successfully")
        return _deduplicate_rates(llm_rates)

    print("[Rate Parser] LLM unavailable or failed, falling back to pdfplumber...")

    # Fallback: pdfplumber table extraction (page 2 first, then all)
    rates = _extract_from_tables(pdf_path, target_page=RATE_PAGE)
    if not rates:
        rates = _extract_from_tables(pdf_path, target_page=None)

    # If no table found, try regex fallback
    if not rates:
        rates = _regex_fallback(pdf_path, target_page=RATE_PAGE)
    if not rates:
        rates = _regex_fallback(pdf_path, target_page=None)

    return _deduplicate_rates(rates)


def _deduplicate_rates(rates: list[dict]) -> list[dict]:
    """
    Warn about and handle duplicate mode entries.
    If same mode appears with same rate, keep one.
    If same mode appears with different rates, keep both (user must resolve).
    """
    seen = {}  # mode -> list of rates
    for r in rates:
        mode = r["mode"]
        if mode in seen:
            if r["rate"] not in seen[mode]:
                seen[mode].append(r["rate"])
                logger.warning(f"[Rate Parser] Duplicate mode '{mode}' with different rates: {seen[mode]}")
            # Skip exact duplicates (same mode + same rate)
        else:
            seen[mode] = [r["rate"]]

    # Rebuild deduplicated list
    result = []
    added = set()
    for r in rates:
        key = f"{r['mode']}_{r['rate']}"
        if key not in added:
            added.add(key)
            result.append(r)
    return result


def _extract_from_tables(pdf_path: str, target_page: Optional[int] = None) -> list[dict]:
    """Extract rates from PDF tables using pdfplumber."""
    rates = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        if target_page is not None and 1 <= target_page <= total_pages:
            pages = [pdf.pages[target_page - 1]]
        else:
            pages = pdf.pages

        for page in pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                header_row = table[0]
                if not header_row:
                    continue

                normalized_headers = [_normalize_header(h or '') for h in header_row]

                mode_col = None
                rate_col = None

                for i, h in enumerate(normalized_headers):
                    if any(kw in h for kw in ['mode', 'payment', 'method', 'instrument']):
                        mode_col = i
                    if any(kw in h for kw in ['commercial', 'rate', 'fee', 'commission', 'percentage', '%']):
                        rate_col = i

                if mode_col is None or rate_col is None:
                    continue

                for row in table[1:]:
                    if not row or len(row) <= max(mode_col, rate_col):
                        continue

                    mode_name = (row[mode_col] or '').strip()
                    rate_value = _parse_percentage(row[rate_col] or '')

                    # Validate mode name: must be > 2 chars and not noise
                    if mode_name and len(mode_name) > 2 and rate_value is not None:
                        if not mode_name.lower().startswith(('merchant', 'effective', 'tppa', 'platform', 'total')):
                            rates.append({
                                "mode": mode_name,
                                "rate": rate_value,
                            })

    return rates


def _regex_fallback(pdf_path: str, target_page: Optional[int] = None) -> list[dict]:
    """Fallback: try to extract rates from text using regex patterns."""
    rates = []
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

    # Pattern 1: "Mode Name - 2.5%" or "Mode Name: 2.5%"
    pattern1 = r'([A-Za-z][A-Za-z0-9\s/()]+?)\s*[-\u2013:]\s*(\d+\.?\d*)\s*%'
    matches = re.findall(pattern1, full_text)

    for mode, rate in matches:
        mode = mode.strip()
        rate_val = _parse_percentage(rate + '%')
        if len(mode) > 2 and rate_val is not None:
            if not mode.lower().startswith(('merchant', 'effective', 'tppa', 'platform', 'total')):
                rates.append({"mode": mode, "rate": rate_val})

    if rates:
        return rates

    # Pattern 2: "Mode Name  2.5%" (space-separated, after header line)
    lines = full_text.split('\n')
    found_header = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        lower = line.lower()
        if any(kw in lower for kw in ['modes', 'payment mode', 'instrument']):
            if any(kw in lower for kw in ['commercial', 'rate', 'fee', 'commission', '%']):
                found_header = True
                continue

        if found_header:
            match = re.match(r'^(.+?)\s+(\d+\.?\d*)\s*%?\s*$', line)
            if match:
                mode_name = match.group(1).strip()
                rate_val = _parse_percentage(match.group(2) + '%')
                if (len(mode_name) > 2
                        and rate_val is not None
                        and not mode_name.lower().startswith(('merchant', 'effective', 'tppa', 'platform', 'total'))):
                    rates.append({"mode": mode_name, "rate": rate_val})

    return rates
