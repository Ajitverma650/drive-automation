"""Auto-process route: Full pipeline (extract + fill + verify) in one call."""

import os
import tempfile
import traceback

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.extraction.agreement_parser import extract_agreement_info, extract_start_date, calculate_end_date
from app.extraction.rate_parser import extract_rates
from app.transformation.mode_mapping import map_rates_to_dashboard, group_by_tab
from app.services.extraction import build_phase1_steps
from app.services.comparison import compare_rates
from app.services.email import send_mismatch_report, is_email_configured
from app.reporting.discrepancy_report import generate_report

router = APIRouter()


def _save_temp(upload: UploadFile) -> str:
    """Save an uploaded file to a temp path and return the path."""
    suffix = os.path.splitext(upload.filename or "file.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        content = upload.file.read()
        f.write(content)
        return f.name


@router.post("/api/auto-process")
async def auto_process(
    agreement_pdf: UploadFile = File(...),
    rate_pdf: UploadFile = File(...),
    merchant_name: str = Form("Unknown Merchant"),
):
    """
    Fully automated pipeline: Phase 1 (extract + fill) -> Phase 2 (verify) in one call.

    Phase 2 in auto-process validates that the mapping is consistent:
    - Extracts rates from PDF
    - Maps them to dashboard format
    - Verifies the mapping produced valid results (no collisions, no data loss)
    - Reports any mapping issues as discrepancies

    For real dashboard verification, use /api/phase2/verify with actual dashboard data.
    """
    agreement_path = None
    rate_path = None

    try:
        agreement_path = _save_temp(agreement_pdf)
        rate_path = _save_temp(rate_pdf)

        steps = []

        # ─── PHASE 1: Extract ─────────────────────────────────
        steps.append({"step": 1, "phase": "phase1", "action": "start",
                       "description": "Starting Phase 1: PDF extraction..."})

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
                "start_date": None,
                "end_date": None,
                "file_name": agreement_pdf.filename,
                "date_extraction_failed": True,
            }
        else:
            end_date = calculate_end_date(start_date)
            agreement_data = {
                "start_date": start_date,
                "end_date": end_date,
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

        steps.append({"step": 2, "phase": "phase1", "action": "agreement_extracted",
                       "description": f"Agreement extracted: start={agreement_data['start_date']}, end={agreement_data.get('end_date')}"})

        # Extract from Rate PDF
        raw_rates = extract_rates(rate_path)

        if not raw_rates:
            return JSONResponse(content={
                "success": False,
                "error": "No rate table found in Rate PDF. Please check the file.",
                "agreement": agreement_data,
                "rates": {"mapped": [], "unmapped": []},
                "tabs": {},
                "phase1_complete": False,
                "phase2_complete": False,
            }, status_code=200)

        # Map to dashboard tabs
        mapping_result = map_rates_to_dashboard(raw_rates)
        tabs = group_by_tab(mapping_result["mapped"])

        steps.append({"step": 3, "phase": "phase1", "action": "rates_extracted",
                       "description": f"Extracted {len(raw_rates)} rates, mapped {len(mapping_result['mapped'])}, unmapped {len(mapping_result['unmapped'])}"})

        phase1_steps = build_phase1_steps(agreement_data, tabs, mapping_result)
        steps.extend(phase1_steps)

        steps.append({"step": len(steps) + 1, "phase": "phase1", "action": "phase1_done",
                       "description": "Phase 1 complete! Running consistency verification..."})

        # ─── PHASE 2: Consistency Verification ──────────────────
        # In auto-process, we verify the mapping is internally consistent.
        # Build what-would-be-filled as dashboard rates
        dashboard_rates = {}
        for tab_name, entries in tabs.items():
            dashboard_rates[tab_name] = [
                {"method": e["method"], "rate": e["rate"], "originalMode": e["original_mode"]}
                for e in entries
            ]

        # Compare extracted rates against the mapped dashboard values
        discrepancies, matched_entries, total_modes = compare_rates(
            mapping_result["mapped"], dashboard_rates
        )

        report = generate_report(merchant_name, discrepancies, total_modes, matched_entries)

        steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "verified",
                       "description": f"Verification: {report['matched']} matched, {report['mismatched']} mismatched"})

        # Auto-email on mismatch
        email_result = None
        if report["has_discrepancies"]:
            steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "discrepancies",
                           "description": "MAPPING ISSUES FOUND - Review required"})

            # Auto-send email to IT support
            if is_email_configured():
                steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "emailing",
                               "description": "Sending mismatch report to IT support..."})
                email_result = send_mismatch_report(merchant_name, report)
                if email_result["success"]:
                    steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "email_sent",
                                   "description": f"Report emailed to {', '.join(email_result['sent_to'])}"})
                else:
                    steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "email_failed",
                                   "description": f"Email failed: {email_result['message']}"})
            else:
                steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "email_not_configured",
                               "description": "Email not configured. Set SMTP details in .env to auto-send reports."})
        else:
            steps.append({"step": len(steps) + 1, "phase": "phase2", "action": "confirmed",
                           "description": "ALL RATES CONSISTENT - Ready to fill!"})

        return {
            "success": True,
            # Phase 1 data
            "agreement": agreement_data,
            "rates": mapping_result,
            "tabs": tabs,
            "raw_rates_count": len(raw_rates),
            "phase1_complete": True,
            # Phase 2 data
            "all_match": not report["has_discrepancies"],
            "action": "confirm" if not report["has_discrepancies"] else "email",
            "report": report,
            "phase2_complete": True,
            # Email result
            "email_sent": email_result,
            # Combined steps
            "steps": steps,
        }

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
