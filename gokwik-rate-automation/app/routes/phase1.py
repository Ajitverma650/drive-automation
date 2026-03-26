"""Phase 1 route: Extract data from Agreement + Rate PDFs."""

import os
import tempfile
import traceback

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.extraction.agreement_parser import extract_start_date, calculate_end_date
from app.extraction.rate_parser import extract_rates
from app.transformation.mode_mapping import map_rates_to_dashboard, group_by_tab
from app.services.extraction import build_phase1_steps

router = APIRouter()


def _save_temp(upload: UploadFile) -> str:
    """Save an uploaded file to a temp path and return the path."""
    suffix = os.path.splitext(upload.filename or "file.pdf")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        content = upload.file.read()
        f.write(content)
        return f.name


@router.post("/api/phase1/extract")
async def phase1_extract(
    agreement_pdf: UploadFile = File(...),
    rate_pdf: UploadFile = File(...),
):
    """
    Phase 1 (Maker/Entry): Extract data from both PDFs.
    Returns all data needed to auto-fill the dashboard.
    """
    agreement_path = None
    rate_path = None

    try:
        agreement_path = _save_temp(agreement_pdf)
        rate_path = _save_temp(rate_pdf)

        # Extract from Agreement PDF
        start_date = extract_start_date(agreement_path)
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
            "merchant_size": "Long Tail",
            "merchant_type": "D2C",
            "agency": "",
            "agency_commission": "",
            "purchased_products": ["Checkout"],
        })

        # Extract from Rate PDF
        raw_rates = extract_rates(rate_path)

        if not raw_rates:
            return JSONResponse(content={
                "success": False,
                "error": "No rate table found in Rate PDF. Please check the file.",
                "agreement": agreement_data,
                "rates": {"mapped": [], "unmapped": []},
                "tabs": {},
            }, status_code=200)

        mapping_result = map_rates_to_dashboard(raw_rates)
        tabs = group_by_tab(mapping_result["mapped"])

        return {
            "success": True,
            "agreement": agreement_data,
            "rates": mapping_result,
            "tabs": tabs,
            "raw_rates_count": len(raw_rates),
            "steps": build_phase1_steps(agreement_data, tabs, mapping_result),
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
