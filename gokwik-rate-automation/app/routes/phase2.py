"""Phase 2 route: Compare dashboard rates against Rate PDF."""

import os
import json
import tempfile
import traceback

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.extraction.rate_parser import extract_rates
from app.transformation.mode_mapping import map_rates_to_dashboard
from app.services.comparison import compare_rates
from app.reporting.discrepancy_report import generate_report

router = APIRouter()


def _save_temp(upload: UploadFile) -> str:
    """Save an uploaded file to a temp path and return the path."""
    suffix = os.path.splitext(upload.filename or "file.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        content = upload.file.read()
        f.write(content)
        return f.name


@router.post("/api/phase2/verify")
async def phase2_verify(
    rate_pdf: UploadFile = File(...),
    dashboard_rates: str = Form(...),
    merchant_name: str = Form("Unknown Merchant"),
):
    """
    Phase 2 (Checker/Capture): Compare dashboard rates against Rate PDF.

    dashboard_rates should be JSON string of the format:
    {
        "EMI": [{"method": "Credit Card", "rate": 0, "originalMode": "CC EMI"}, ...],
        "UPI": [{"method": "Default", "rate": 2.5}, ...],
        ...
    }
    """
    rate_path = None

    try:
        rate_path = _save_temp(rate_pdf)

        # Extract expected rates from PDF
        raw_rates = extract_rates(rate_path)
        if not raw_rates:
            raise HTTPException(status_code=400, detail="No rate table found in Rate PDF")

        mapping_result = map_rates_to_dashboard(raw_rates)

        # Parse dashboard rates
        try:
            actual_tabs = json.loads(dashboard_rates)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid dashboard_rates JSON")

        # Compare using shared function
        discrepancies, matched_entries, total_modes = compare_rates(
            mapping_result["mapped"], actual_tabs
        )

        report = generate_report(merchant_name, discrepancies, total_modes, matched_entries)

        return {
            "success": True,
            "all_match": not report["has_discrepancies"],
            "action": "confirm" if not report["has_discrepancies"] else "email",
            "report": report,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if rate_path and os.path.exists(rate_path):
            try:
                os.unlink(rate_path)
            except OSError:
                pass
