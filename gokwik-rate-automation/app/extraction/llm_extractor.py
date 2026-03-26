"""
LLM-powered PDF extraction using OpenAI GPT-4o-mini.

Extracts rates and agreement info from PDFs with much higher accuracy
than regex/table-based approaches. Handles any PDF layout.

Page targeting:
  - Agreement PDF: page 2 for date extraction
  - Rate Card PDF: page 2 for rate extraction
"""

import json
import re
import logging
from typing import Optional

import pdfplumber
from openai import OpenAI

from app.config import get_openai_api_key

logger = logging.getLogger(__name__)

# Maximum characters to send to LLM (roughly ~50K tokens)
MAX_TEXT_LENGTH = 200_000


def _get_client() -> Optional[OpenAI]:
    """Get OpenAI client if API key is available."""
    api_key = get_openai_api_key()
    if not api_key:
        logger.warning("[LLM Extractor] No API key found in OPENAI_API_KEY or OPEN_AI_KEY")
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"[LLM Extractor] Failed to create OpenAI client: {e}")
        return None


def _extract_text_from_pdf(pdf_path: str, target_page: Optional[int] = None) -> str:
    """
    Extract text from a PDF using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.
        target_page: If set, extract ONLY from this page number (1-based).
                     If the page doesn't exist, falls back to all pages.
    """
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        # Determine which pages to process
        if target_page is not None and 1 <= target_page <= total_pages:
            pages_to_process = [pdf.pages[target_page - 1]]
        else:
            # Fallback: all pages (if target page doesn't exist)
            if target_page is not None:
                logger.warning(
                    f"[LLM Extractor] Requested page {target_page} but PDF has {total_pages} pages. "
                    f"Falling back to all pages."
                )
            pages_to_process = pdf.pages

        for page in pages_to_process:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

            # Also try extracting tables as text
            tables = page.extract_tables()
            for table in tables:
                if table:
                    for row in table:
                        if row:
                            row_text = " | ".join(str(cell or "") for cell in row)
                            full_text += row_text + "\n"

    # Truncate if too long for LLM context window
    if len(full_text) > MAX_TEXT_LENGTH:
        logger.warning(
            f"[LLM Extractor] PDF text too long ({len(full_text)} chars), truncating to {MAX_TEXT_LENGTH}"
        )
        full_text = full_text[:MAX_TEXT_LENGTH]

    return full_text


def _parse_llm_json(content: str) -> Optional[any]:
    """Safely parse JSON from LLM response, handling markdown code blocks."""
    if not content:
        return None

    # Remove markdown code blocks
    if "```" in content:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if match:
            content = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON array or object from surrounding text
    for pattern in [r'(\[[\s\S]*\])', r'(\{[\s\S]*\})']:
        match = re.search(pattern, content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    logger.error(f"[LLM Extractor] Failed to parse JSON from LLM response: {content[:200]}...")
    return None


def extract_rates_with_llm(pdf_path: str) -> Optional[list[dict]]:
    """
    Extract payment mode rates from a Rate PDF using OpenAI.

    Targets page 2 of the PDF for rate extraction.
    Returns list of dicts: [{"mode": "UPI", "rate": 2.5}, ...] or None if LLM unavailable.
    """
    client = _get_client()
    if not client:
        return None

    # Target page 2 for rate extraction
    pdf_text = _extract_text_from_pdf(pdf_path, target_page=2)
    if not pdf_text.strip():
        # Fallback: try all pages if page 2 is empty
        print("[LLM Extractor] Page 2 empty, falling back to ALL pages")
        pdf_text = _extract_text_from_pdf(pdf_path)
    if not pdf_text.strip():
        return None

    char_count = len(pdf_text)
    token_estimate = char_count // 4  # ~4 chars per token
    print(f"[LLM Extractor] RATES: Sending page 2 only | {char_count} chars | ~{token_estimate} tokens")

    # Explicit list of ALL 16 modes from MODE_MAP for accurate extraction
    prompt = f"""You are a data extraction expert. Extract ALL payment mode rates from the following PDF text.

The PDF contains a rate card with payment modes and their commission percentages.

You MUST look for these EXACT payment modes (extract the name EXACTLY as written in the PDF):
1. UPI
2. DC Below2K (or Debit Card Below 2K)
3. DC Above2K (or Debit Card Above 2K)
4. Credit Card
5. CC EMI (Credit Card EMI)
6. DC EMI (Debit Card EMI - separate from "Debit Card EMI" below)
7. Debit Card EMI (may also appear as "DC EMI" variant)
8. Card Less EMI (or Cardless EMI)
9. Amex (American Express)
10. UPI Credit Card (Rupay only)
11. Net Banking (or NetBanking)
12. Diners Credit Card (or Diners)
13. Corporate Credit Card (or Corporate CC)
14. Wallets (or Wallet)
15. BNPL (Buy Now Pay Later)
16. International CC (International Credit Card)

IMPORTANT RULES:
- Extract the EXACT mode name as written in the PDF
- Rate should be a number (percentage). "2.5%" -> 2.5, "0%" or "NIL" -> 0
- Rate must be between 0 and 100 (it's a percentage)
- Do NOT merge "DC EMI" and "Debit Card EMI" if they appear as separate entries
- Do NOT skip any mode, even if its rate is 0%
- If a mode appears twice, extract BOTH entries

Return ONLY a JSON array, no other text:
[
  {{"mode": "exact mode name from PDF", "rate": <number>}},
  ...
]

PDF Text:
{pdf_text}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured data from PDFs. Always return valid JSON arrays only. Never skip entries even if rate is 0."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=2000,
        )

        usage = response.usage
        print(f"[LLM Extractor] RATES tokens used: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

        content = response.choices[0].message.content.strip()
        rates = _parse_llm_json(content)

        if not isinstance(rates, list):
            logger.error(f"[LLM Extractor] Expected list, got {type(rates)}")
            return None

        valid_rates = []
        seen_modes = set()
        for entry in rates:
            if isinstance(entry, dict) and "mode" in entry and "rate" in entry:
                try:
                    mode = str(entry["mode"]).strip()
                    rate = float(entry["rate"])

                    # Validate rate is a reasonable percentage (0-100)
                    if rate < 0 or rate > 100:
                        logger.warning(f"[LLM Extractor] Skipping invalid rate for {mode}: {rate}%")
                        continue

                    # Warn on duplicate modes (but still include them)
                    if mode in seen_modes:
                        logger.warning(f"[LLM Extractor] Duplicate mode detected: {mode}")
                    seen_modes.add(mode)

                    valid_rates.append({"mode": mode, "rate": rate})
                except (ValueError, TypeError):
                    continue

        return valid_rates if valid_rates else None

    except Exception as e:
        logger.error(f"[LLM Extractor] Rate extraction failed: {e}")
        print(f"[LLM Extractor] Rate extraction failed: {e}")
        return None


def extract_agreement_with_llm(pdf_path: str) -> Optional[dict]:
    """
    Extract agreement details from an Agreement PDF using OpenAI.

    Targets page 2 of the PDF for date extraction.
    Returns dict with start_date (YYYY-MM-DD), merchant_size, merchant_type,
    purchased_products, or None if LLM unavailable.
    """
    client = _get_client()
    if not client:
        return None

    # Target page 2 for agreement date
    pdf_text = _extract_text_from_pdf(pdf_path, target_page=2)
    if not pdf_text.strip():
        print("[LLM Extractor] Page 2 empty, falling back to ALL pages")
        pdf_text = _extract_text_from_pdf(pdf_path)
    if not pdf_text.strip():
        return None

    char_count = len(pdf_text)
    token_estimate = char_count // 4
    print(f"[LLM Extractor] AGREEMENT: Sending page 2 only | {char_count} chars | ~{token_estimate} tokens")

    prompt = f"""You are a legal document analysis expert. Extract the following details from this agreement PDF:

1. **start_date**: The agreement start/effective/commencement/execution date from the AGREEMENT TEXT ONLY. Convert to YYYY-MM-DD format.
   RULES for finding the correct date:
   - Look for the date in the opening paragraph of the agreement, e.g. "made and entered into 1st day of December, 2021"
   - Look for keywords: "effective date", "commencement date", "execution date", "dated", "start date", "agreement date", "w.e.f", "with effect from"
   - ONLY pick the date from the agreement body text — do NOT use signature dates, audit trail dates, or e-stamp dates
   - Indian date format: DD/MM/YYYY (day first, then month)
   - Example: "01/03/2026" means March 1, 2026 (NOT January 3)
2. **merchant_size**: If mentioned, one of: "Long Tail", "Mid Market", "Enterprise", "SMB". Default: "Long Tail"
3. **merchant_type**: If mentioned, one of: "D2C", "Marketplace", "B2B", "Aggregator". Default: "D2C"
4. **purchased_products**: List of products mentioned. Possible values: "Checkout", "KwikPass", "KwikAds", "RTO". Default: ["Checkout"]

Return ONLY a JSON object, no other text:
{{
  "start_date": "YYYY-MM-DD or null if not found",
  "merchant_size": "...",
  "merchant_type": "...",
  "purchased_products": ["..."]
}}

Agreement PDF Text:
{pdf_text}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured data from legal documents. Always return valid JSON only. Dates in Indian format: DD/MM/YYYY means day/month/year."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=500,
        )

        usage = response.usage
        print(f"[LLM Extractor] AGREEMENT tokens used: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

        content = response.choices[0].message.content.strip()
        data = _parse_llm_json(content)

        if not isinstance(data, dict):
            logger.error(f"[LLM Extractor] Expected dict, got {type(data)}")
            return None

        start_date = data.get("start_date")
        if start_date in ("null", "None", None, ""):
            start_date = None

        return {
            "start_date": start_date,
            "merchant_size": data.get("merchant_size", "Long Tail"),
            "merchant_type": data.get("merchant_type", "D2C"),
            "purchased_products": data.get("purchased_products", ["Checkout"]),
        }

    except Exception as e:
        logger.error(f"[LLM Extractor] Agreement extraction failed: {e}")
        print(f"[LLM Extractor] Agreement extraction failed: {e}")
        return None
