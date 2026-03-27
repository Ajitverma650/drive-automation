"""
GoKwik Auto-Fill API — the main endpoint that ties everything together.

POST /api/gokwik/fill-from-drive
  Input: { merchant_name: "Jaipur Masala" }
  Does:
    1. Search Google Drive for agreement + rate card PDFs
    2. Download both to temp files
    3. Extract dates from agreement PDF (page 2)
    4. Extract rates from rate card PDF (page 2)
    5. Fill real GoKwik dashboard via Playwright
    6. Return result with steps and screenshot

POST /api/gokwik/fill
  Input: { merchant_name, agreement, tabs, rate_card_path, is_new }
  Does: Just the Playwright fill step (data already extracted)
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
    is_new: bool = Form(True),
):
    """Fill rates on real GoKwik dashboard. Data already extracted."""
    from automation.gokwik_filler import fill_gokwik

    try:
        agreement = json.loads(agreement_json)
        tabs = json.loads(tabs_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    result = await fill_gokwik(
        merchant_name=merchant_name,
        rate_card_path=rate_card_path,
        agreement=agreement,
        tabs=tabs,
        is_new=is_new,
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
    from automation.gokwik_filler import fill_gokwik

    merchant = merchant_name.strip()
    if not merchant:
        raise HTTPException(status_code=400, detail="Merchant name required")

    steps = []
    agreement_path = None
    rate_card_path = None

    try:
        # ─── Step 1: Search Google Drive ──────────────
        steps.append({"phase": "search", "text": f"Searching Drive for '{merchant}'..."})

        # Find agreement PDF
        ag_result = search_agreement_pdf(merchant)
        if not ag_result["files"]:
            return JSONResponse(content={
                "success": False,
                "message": f"No agreement PDF found for '{merchant}' in Drive.",
                "steps": steps,
            })

        ag_file = ag_result["files"][0]
        steps.append({"phase": "search", "text": f"Agreement: {ag_file['name']}"})

        # Find rate card PDF
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
        steps.append({"phase": "extract", "text": "AI extracting from PDFs (page 2)..."})

        # Extract from agreement
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

        # Extract rates
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

        fill_result = await fill_gokwik(
            merchant_name=merchant,
            rate_card_path=rate_card_path,
            agreement=agreement,
            tabs=tabs,
            is_new=is_new,
        )

        # Merge steps
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
        # Cleanup temp files
        for path in [agreement_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        # Don't delete rate_card_path — it was used by Playwright
