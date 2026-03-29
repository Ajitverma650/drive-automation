"""
GoKwik Auto-Fill API — the main endpoint that ties everything together.

POST /api/gokwik/fill
  Input: { merchant_name, agreement_json, tabs_json, rate_card_path, is_new }
  Does: Login to GoKwik → Navigate to Rate Capture → Fill form with extracted data

POST /api/gokwik/fill-from-drive
  Input: { merchant_name }
  Does: Search Drive → Download → Extract → Fill GoKwik

Both endpoints launch a fresh headless browser, login automatically, and fill.
No separate browser_server needed.
"""

import os
import json
import traceback
import tempfile

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

from app.services.google_drive import (
    search_agreement_pdf, search_rate_card_pdf, download_file, is_drive_configured,
)
from app.extraction.rate_parser import extract_rates
from app.extraction.agreement_parser import extract_start_date, extract_agreement_info, calculate_end_date
from app.transformation.mode_mapping import map_rates_to_dashboard, group_by_tab

router = APIRouter(prefix="/api/gokwik", tags=["GoKwik Auto"])


@router.post("/fill")
async def gokwik_fill(
    merchant_name: str = Form(...),
    agreement_json: str = Form(...),
    tabs_json: str = Form(...),
    rate_card_path: str = Form(""),
    agreement_pdf_path: str = Form(""),
    is_new: bool = Form(True),
):
    """
    Fill rates on real GoKwik dashboard.
    Data already extracted — just needs to be filled.

    Launches a visible browser, logs into GoKwik, navigates to Rate Capture,
    and fills the form automatically.
    """
    try:
        agreement = json.loads(agreement_json)
        tabs = json.loads(tabs_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from app.services.playwright_driver import fill_gokwik_dashboard

    result = await fill_gokwik_dashboard(
        tabs=tabs,
        agreement=agreement,
        merchant_name=merchant_name,
        rate_card_path=rate_card_path,
        agreement_pdf_path=agreement_pdf_path,
    )
    return result


@router.post("/fill-from-drive")
async def gokwik_fill_from_drive(
    merchant_name: str = Form(...),
    is_new: bool = Form(True),
):
    """
    Full automation: Search Drive → Download → Extract → Fill GoKwik.
    One input: merchant name. Everything else is automatic.
    """
    from app.services.playwright_driver import fill_gokwik_dashboard

    merchant = merchant_name.strip()
    if not merchant:
        raise HTTPException(status_code=400, detail="Merchant name required")

    steps = []
    agreement_path = None
    rate_card_path = None

    try:
        # ─── Step 1: Search Google Drive ──────────────
        steps.append({"phase": "search", "text": f"Searching Drive for '{merchant}'..."})

        ag_result = search_agreement_pdf(merchant)
        if not ag_result["files"]:
            return JSONResponse(content={
                "success": False,
                "message": f"No agreement PDF found for '{merchant}' in Drive.",
                "steps": steps,
            })

        ag_file = ag_result["files"][0]
        steps.append({"phase": "search", "text": f"Agreement: {ag_file['name']}"})

        rc_result = search_rate_card_pdf(merchant)
        if not rc_result["files"]:
            return JSONResponse(content={
                "success": False,
                "message": f"No rate card PDF found for '{merchant}' in Drive.",
                "steps": steps,
                "needs_selection": rc_result.get("needs_selection", False),
                "rate_card_candidates": rc_result.get("files", []),
                "agreement_found": ag_file,
            })

        rc_file = rc_result["files"][0]
        steps.append({"phase": "search", "text": f"Rate Card: {rc_file['name']}"})

        # ─── Step 2: Download PDFs ────────────────────
        steps.append({"phase": "download", "text": "Downloading from Drive..."})

        agreement_path, ag_name = download_file(ag_file["id"])
        if not agreement_path:
            return JSONResponse(content={
                "success": False,
                "message": f"Failed to download agreement: {ag_name}",
                "steps": steps,
            })

        rate_card_path, rc_name = download_file(rc_file["id"])
        if not rate_card_path:
            return JSONResponse(content={
                "success": False,
                "message": f"Failed to download rate card: {rc_name}",
                "steps": steps,
            })

        steps.append({"phase": "download", "text": "Both PDFs downloaded"})

        # ─── Step 3: Extract data ─────────────────────
        steps.append({"phase": "extract", "text": "AI extracting from PDFs..."})

        start_date = extract_start_date(agreement_path)
        agreement_info = None
        try:
            agreement_info = extract_agreement_info(agreement_path)
        except Exception:
            pass

        if not start_date and agreement_info:
            start_date = agreement_info.get("start_date")

        end_date = calculate_end_date(start_date) if start_date else None

        agreement = {
            "start_date": start_date or "",
            "end_date": end_date or "",
            "merchant_size": (agreement_info or {}).get("merchant_size", "Long Tail"),
            "merchant_type": (agreement_info or {}).get("merchant_type", "D2C"),
            "purchased_products": (agreement_info or {}).get("purchased_products", ["Checkout"]),
        }

        steps.append({"phase": "extract", "text": f"Agreement: {start_date} to {end_date}"})

        raw_rates = extract_rates(rate_card_path)
        if not raw_rates:
            return JSONResponse(content={
                "success": False,
                "message": "No rates found in rate card PDF.",
                "steps": steps,
                "agreement": agreement,
            })

        mapping = map_rates_to_dashboard(raw_rates)
        tabs = group_by_tab(mapping["mapped"])

        total_rates = sum(len(v) for v in tabs.values())
        steps.append({"phase": "extract", "text": f"Extracted {total_rates} rates from {len(tabs)} tabs"})

        # ─── Step 4: Fill GoKwik Dashboard ────────────
        steps.append({"phase": "fill", "text": "Filling real GoKwik dashboard..."})

        fill_result = await fill_gokwik_dashboard(
            tabs=tabs,
            agreement=agreement,
            merchant_name=merchant,
        )

        steps.extend(fill_result.get("steps", []))

        return {
            "success": fill_result["success"],
            "filled": fill_result.get("filled", 0),
            "failed": fill_result.get("failed", 0),
            "agreement": agreement,
            "tabs": tabs,
            "raw_rates_count": len(raw_rates),
            "agreement_file": ag_file["name"],
            "rate_card_file": rc_file["name"],
            "steps": steps,
            "screenshot": fill_result.get("screenshot"),
            "message": fill_result.get("message", ""),
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for path in [agreement_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
