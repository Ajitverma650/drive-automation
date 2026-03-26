"""Google Drive routes: search, fetch, and full-auto rate capture."""

import os
import traceback

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.google_drive import (
    is_drive_configured, search_rate_card, search_agreement_pdf,
    search_rate_card_pdf, download_file,
)
from app.extraction.rate_parser import extract_rates
from app.extraction.agreement_parser import extract_start_date, extract_agreement_info, calculate_end_date
from app.transformation.mode_mapping import map_rates_to_dashboard, group_by_tab
from app.reporting.discrepancy_report import generate_report
from app.services.comparison import compare_rates
from app.services.extraction import build_phase1_steps
from app.services.email import send_mismatch_report, is_email_configured

router = APIRouter(prefix="/api/drive", tags=["Google Drive"])


def _save_temp(upload: UploadFile) -> str:
    import tempfile
    suffix = os.path.splitext(upload.filename or "file.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(upload.file.read())
        return f.name


def _cleanup(*paths):
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


def _run_extraction(agreement_path, rate_path, agreement_filename, rate_filename, merchant_name, steps):
    """Shared extraction logic for both drive endpoints."""
    # Extract from Agreement PDF
    start_date = extract_start_date(agreement_path)
    agreement_info = None
    try:
        agreement_info = extract_agreement_info(agreement_path)
    except Exception:
        pass

    if not start_date and agreement_info:
        start_date = agreement_info.get("start_date")

    if not start_date:
        agreement_data = {
            "start_date": None, "end_date": None,
            "file_name": agreement_filename,
            "date_extraction_failed": True,
        }
    else:
        end_date = calculate_end_date(start_date)
        agreement_data = {
            "start_date": start_date, "end_date": end_date,
            "file_name": agreement_filename,
            "date_extraction_failed": False,
        }

    agreement_data.update({
        "merchant_size": (agreement_info or {}).get("merchant_size", "Long Tail"),
        "merchant_type": (agreement_info or {}).get("merchant_type", "D2C"),
        "agency": "",
        "agency_commission": "",
        "purchased_products": (agreement_info or {}).get("purchased_products", ["Checkout"]),
    })

    steps.append({"step": len(steps) + 1, "phase": "phase1", "action": "agreement_extracted",
                   "description": f"Agreement: start={agreement_data['start_date']}, end={agreement_data.get('end_date')}"})

    # Extract from Rate PDF
    raw_rates = extract_rates(rate_path)

    if not raw_rates:
        return {
            "success": False,
            "error": f"No rate table found in {rate_filename}. Check if page 2 has rates.",
            "agreement": agreement_data,
            "rates": {"mapped": [], "unmapped": []},
            "tabs": {},
            "phase1_complete": False,
            "phase2_complete": False,
            "steps": steps,
        }

    mapping_result = map_rates_to_dashboard(raw_rates)
    tabs = group_by_tab(mapping_result["mapped"])

    steps.append({"step": len(steps) + 1, "phase": "phase1", "action": "rates_extracted",
                   "description": f"Extracted {len(raw_rates)} rates, mapped {len(mapping_result['mapped'])}"})

    phase1_steps = build_phase1_steps(agreement_data, tabs, mapping_result)
    steps.extend(phase1_steps)

    # Phase 2: Verify
    dashboard_rates = {}
    for tab_name, entries in tabs.items():
        dashboard_rates[tab_name] = [
            {"method": e["method"], "rate": e["rate"], "originalMode": e["original_mode"]}
            for e in entries
        ]

    discrepancies, matched_entries, total_modes = compare_rates(mapping_result["mapped"], dashboard_rates)
    report = generate_report(merchant_name, discrepancies, total_modes, matched_entries)

    # Auto-email on mismatch
    email_result = None
    if report["has_discrepancies"] and is_email_configured():
        email_result = send_mismatch_report(merchant_name, report)

    steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "verified",
                   "description": f"Verification: {report['matched']} matched, {report['mismatched']} mismatched"})

    return {
        "success": True,
        "agreement": agreement_data,
        "rates": mapping_result,
        "tabs": tabs,
        "raw_rates_count": len(raw_rates),
        "phase1_complete": True,
        "all_match": not report["has_discrepancies"],
        "action": "confirm" if not report["has_discrepancies"] else "email",
        "report": report,
        "phase2_complete": True,
        "email_sent": email_result,
        "steps": steps,
    }


@router.get("/status")
async def drive_status():
    return {
        "configured": is_drive_configured(),
        "message": "Google Drive is configured and authenticated" if is_drive_configured()
                   else "Run `python auth_drive.py` first to authenticate",
    }


@router.get("/search")
async def drive_search(merchant: str = Query(..., description="Merchant name to search for")):
    if not merchant.strip():
        raise HTTPException(status_code=400, detail="Merchant name is required")
    return search_rate_card(merchant.strip())


@router.post("/auto-process")
async def drive_auto_process(
    agreement_pdf: UploadFile = File(...),
    drive_file_id: str = Form(...),
    merchant_name: str = Form("Unknown Merchant"),
):
    """Agreement uploaded manually + Rate card from Google Drive."""
    agreement_path = None
    rate_path = None

    try:
        agreement_path = _save_temp(agreement_pdf)

        # Download rate card from Drive
        rate_path, rate_filename = download_file(drive_file_id)
        if not rate_path:
            raise HTTPException(status_code=400, detail=f"Failed to download from Drive: {rate_filename}")

        steps = [
            {"step": 1, "phase": "phase1", "action": "start", "description": "Starting automation..."},
            {"step": 2, "phase": "phase1", "action": "drive_download", "description": f"Rate card from Drive: {rate_filename}"},
        ]

        result = _run_extraction(agreement_path, rate_path, agreement_pdf.filename, rate_filename, merchant_name, steps)
        result["source"] = "drive_rate_card"
        result["rate_card_file_name"] = rate_filename
        return result if result["success"] else JSONResponse(content=result, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _cleanup(agreement_path, rate_path)


@router.post("/full-auto")
async def drive_full_auto(
    merchant_name: str = Form(...),
):
    """
    FULL AUTOMATION: Just provide merchant name.
    Searches Google Drive for both Agreement + Rate Card PDFs,
    downloads, extracts, fills, and verifies — all automatically.
    """
    agreement_path = None
    rate_path = None

    try:
        merchant = merchant_name.strip()
        if not merchant:
            raise HTTPException(status_code=400, detail="Merchant name is required")

        steps = [{"step": 1, "phase": "search", "action": "start",
                   "description": f"Searching Google Drive for '{merchant}'..."}]

        # ─── Step 1: Search for Agreement PDF ─────────────
        agreement_result = search_agreement_pdf(merchant)
        if not agreement_result["success"] or not agreement_result["files"]:
            return JSONResponse(content={
                "success": False,
                "error": f"No Agreement PDF found for '{merchant}'. Upload manually or check Drive folder.",
                "search_results": {"agreement": agreement_result, "rate_card": None},
                "phase1_complete": False,
                "phase2_complete": False,
                "steps": steps,
            }, status_code=200)

        agreement_file = agreement_result["files"][0]  # pick most recent
        steps.append({"step": 2, "phase": "search", "action": "agreement_found",
                       "description": f"Found Agreement: {agreement_file['name']}"})

        # ─── Step 2: Search for Rate Card PDF ─────────────
        rate_result = search_rate_card_pdf(merchant)
        if not rate_result["success"] or not rate_result["files"]:
            return JSONResponse(content={
                "success": False,
                "error": f"No Rate Card PDF found for '{merchant}'. Upload manually or check Drive folder.",
                "search_results": {"agreement": agreement_result, "rate_card": rate_result},
                "agreement_found": agreement_file,
                "phase1_complete": False,
                "phase2_complete": False,
                "steps": steps,
            }, status_code=200)

        # Edge case: multiple rate cards found, no exact match — ask user to pick
        if rate_result.get("needs_selection") and len(rate_result["files"]) > 1:
            steps.append({"step": 3, "phase": "search", "action": "needs_selection",
                           "description": f"Multiple rate cards found ({len(rate_result['files'])}). Please select one."})
            return JSONResponse(content={
                "success": False,
                "needs_selection": True,
                "error": f"Multiple rate cards found. Please select the correct one for '{merchant}'.",
                "search_results": {"agreement": agreement_result, "rate_card": rate_result},
                "agreement_found": agreement_file,
                "rate_card_candidates": rate_result["files"],
                "phase1_complete": False,
                "phase2_complete": False,
                "steps": steps,
            }, status_code=200)

        rate_file = rate_result["files"][0]  # pick most recent / best match
        steps.append({"step": 3, "phase": "search", "action": "rate_card_found",
                       "description": f"Found Rate Card: {rate_file['name']}"})

        # ─── Step 3: Download both PDFs ───────────────────
        steps.append({"step": 4, "phase": "download", "action": "downloading",
                       "description": "Downloading PDFs from Google Drive..."})

        agreement_path, ag_name = download_file(agreement_file["id"])
        if not agreement_path:
            return JSONResponse(content={
                "success": False,
                "error": f"Failed to download Agreement: {ag_name}",
                "phase1_complete": False, "phase2_complete": False, "steps": steps,
            }, status_code=200)

        rate_path, rc_name = download_file(rate_file["id"])
        if not rate_path:
            _cleanup(agreement_path)
            return JSONResponse(content={
                "success": False,
                "error": f"Failed to download Rate Card: {rc_name}",
                "phase1_complete": False, "phase2_complete": False, "steps": steps,
            }, status_code=200)

        steps.append({"step": 5, "phase": "download", "action": "downloaded",
                       "description": "Both PDFs downloaded successfully"})

        # ─── Step 4: Extract + Map + Verify ───────────────
        steps.append({"step": 6, "phase": "phase1", "action": "extracting",
                       "description": "AI extracting data from PDFs (page 2 only)..."})

        result = _run_extraction(
            agreement_path, rate_path,
            agreement_file["name"], rate_file["name"],
            merchant, steps
        )

        # Add metadata
        result["source"] = "google_drive_full_auto"
        result["agreement_file_name"] = agreement_file["name"]
        result["rate_card_file_name"] = rate_file["name"]
        result["search_results"] = {
            "agreement": agreement_result,
            "rate_card": rate_result,
        }

        return result if result.get("success") else JSONResponse(content=result, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _cleanup(agreement_path, rate_path)


@router.post("/full-auto-select")
async def drive_full_auto_select(body: dict):
    """
    Continue full-auto after user selects a rate card from candidates.
    Accepts agreement_file_id + rate_card_file_id (both Drive IDs).
    """
    agreement_path = None
    rate_path = None

    try:
        merchant = body.get("merchant_name", "Unknown")
        agreement_id = body.get("agreement_file_id")
        rate_card_id = body.get("rate_card_file_id")

        if not agreement_id or not rate_card_id:
            raise HTTPException(status_code=400, detail="Both agreement_file_id and rate_card_file_id are required")

        steps = [{"step": 1, "phase": "download", "action": "start",
                   "description": "Downloading selected PDFs from Google Drive..."}]

        agreement_path, ag_name = download_file(agreement_id)
        if not agreement_path:
            raise HTTPException(status_code=400, detail=f"Failed to download Agreement: {ag_name}")

        rate_path, rc_name = download_file(rate_card_id)
        if not rate_path:
            _cleanup(agreement_path)
            raise HTTPException(status_code=400, detail=f"Failed to download Rate Card: {rc_name}")

        steps.append({"step": 2, "phase": "download", "action": "downloaded",
                       "description": f"Downloaded: {ag_name} + {rc_name}"})

        result = _run_extraction(agreement_path, rate_path, ag_name, rc_name, merchant, steps)
        result["source"] = "google_drive_full_auto_select"
        result["agreement_file_name"] = ag_name
        result["rate_card_file_name"] = rc_name
        return result if result.get("success") else JSONResponse(content=result, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _cleanup(agreement_path, rate_path)
