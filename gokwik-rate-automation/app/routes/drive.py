"""Google Drive routes: search and fetch rate card PDFs."""

import os
import traceback

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.google_drive import is_drive_configured, search_rate_card, download_file
from app.extraction.rate_parser import extract_rates
from app.extraction.agreement_parser import extract_start_date, extract_agreement_info, calculate_end_date
from app.transformation.mode_mapping import map_rates_to_dashboard, group_by_tab
from app.reporting.discrepancy_report import generate_report
from app.services.comparison import compare_rates
from app.services.extraction import build_phase1_steps
from app.services.email import send_mismatch_report, is_email_configured

router = APIRouter(prefix="/api/drive", tags=["Google Drive"])


def _save_temp(upload: UploadFile) -> str:
    """Save an uploaded file to a temp path."""
    import tempfile
    suffix = os.path.splitext(upload.filename or "file.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        content = upload.file.read()
        f.write(content)
        return f.name


@router.get("/status")
async def drive_status():
    """Check if Google Drive is configured."""
    configured = is_drive_configured()
    return {
        "configured": configured,
        "message": "Google Drive is configured" if configured else "Place credentials.json in project root",
    }


@router.get("/search")
async def drive_search(merchant: str = Query(..., description="Merchant name to search for")):
    """Search Google Drive for a merchant's rate card PDF."""
    if not merchant.strip():
        raise HTTPException(status_code=400, detail="Merchant name is required")

    result = search_rate_card(merchant.strip())
    return result


@router.post("/auto-process")
async def drive_auto_process(
    agreement_pdf: UploadFile = File(...),
    drive_file_id: str = Form(...),
    merchant_name: str = Form("Unknown Merchant"),
):
    """
    Full automation using agreement PDF upload + rate card from Google Drive.

    1. Downloads rate card PDF from Google Drive (by file ID)
    2. Extracts agreement info from uploaded agreement PDF
    3. Extracts rates from Drive-downloaded rate card
    4. Maps, verifies, returns same response as /api/auto-process
    """
    agreement_path = None
    rate_path = None

    try:
        # Save uploaded agreement PDF
        agreement_path = _save_temp(agreement_pdf)

        # Download rate card from Google Drive
        print(f"[Drive Auto] Downloading rate card: {drive_file_id}")
        rate_path = download_file(drive_file_id)
        if not rate_path:
            raise HTTPException(status_code=400, detail="Failed to download rate card from Google Drive")

        steps = []
        steps.append({"step": 1, "phase": "phase1", "action": "start",
                       "description": "Starting Phase 1: PDF extraction..."})
        steps.append({"step": 2, "phase": "phase1", "action": "drive_download",
                       "description": "Rate card downloaded from Google Drive"})

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
                "file_name": agreement_pdf.filename,
                "date_extraction_failed": True,
            }
        else:
            end_date = calculate_end_date(start_date)
            agreement_data = {
                "start_date": start_date, "end_date": end_date,
                "file_name": agreement_pdf.filename,
                "date_extraction_failed": False,
            }

        agreement_data.update({
            "merchant_size": (agreement_info or {}).get("merchant_size", "Long Tail"),
            "merchant_type": (agreement_info or {}).get("merchant_type", "D2C"),
            "agency": "",
            "agency_commission": "",
            "purchased_products": (agreement_info or {}).get("purchased_products", ["Checkout"]),
        })

        steps.append({"step": 3, "phase": "phase1", "action": "agreement_extracted",
                       "description": f"Agreement extracted: start={agreement_data['start_date']}"})

        # Extract from Rate PDF (downloaded from Drive)
        raw_rates = extract_rates(rate_path)

        if not raw_rates:
            return JSONResponse(content={
                "success": False,
                "error": "No rate table found in Drive rate card PDF.",
                "agreement": agreement_data,
                "rates": {"mapped": [], "unmapped": []},
                "tabs": {},
                "phase1_complete": False,
                "phase2_complete": False,
            }, status_code=200)

        mapping_result = map_rates_to_dashboard(raw_rates)
        tabs = group_by_tab(mapping_result["mapped"])

        steps.append({"step": 4, "phase": "phase1", "action": "rates_extracted",
                       "description": f"Extracted {len(raw_rates)} rates from Drive PDF"})

        phase1_steps = build_phase1_steps(agreement_data, tabs, mapping_result)
        steps.extend(phase1_steps)

        # Phase 2: Consistency verification
        dashboard_rates = {}
        for tab_name, entries in tabs.items():
            dashboard_rates[tab_name] = [
                {"method": e["method"], "rate": e["rate"], "originalMode": e["original_mode"]}
                for e in entries
            ]

        discrepancies, matched_entries, total_modes = compare_rates(
            mapping_result["mapped"], dashboard_rates
        )
        report = generate_report(merchant_name, discrepancies, total_modes, matched_entries)

        # Auto-email on mismatch
        email_result = None
        if report["has_discrepancies"] and is_email_configured():
            email_result = send_mismatch_report(merchant_name, report)

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
            "source": "google_drive",
            "steps": steps,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for path in [agreement_path, rate_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
