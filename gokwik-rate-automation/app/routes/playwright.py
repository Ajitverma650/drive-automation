"""
Playwright routes — fill, verify, and confirm on real GoKwik dashboard.

These endpoints run Playwright headless Chrome in the background.
The frontend calls these after extraction is complete.
"""

import asyncio
import json
import traceback

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse

from app.services.playwright_driver import (
    fill_gokwik_dashboard,
    verify_gokwik_dashboard,
    confirm_gokwik_dashboard,
    has_session,
)
from app.services.comparison import compare_rates
from app.reporting.discrepancy_report import generate_report
from app.services.email import send_mismatch_report, is_email_configured

router = APIRouter(prefix="/api/playwright", tags=["Playwright"])


@router.get("/status")
async def playwright_status():
    """Check if Playwright is ready (GoKwik session exists)."""
    return {
        "ready": has_session(),
        "message": "GoKwik session saved. Ready to automate."
                   if has_session()
                   else "No session. Run: python -m automation.auth_gokwik",
    }


@router.post("/fill")
async def playwright_fill(
    tabs_json: str = Form(...),
    agreement_json: str = Form(...),
    merchant_name: str = Form("Unknown"),
):
    """
    Fill rates on real GoKwik dashboard using Playwright.

    Input:
      tabs_json: JSON string of tabs data { "EMI": [{method, rate}], ... }
      agreement_json: JSON string of agreement { start_date, end_date, ... }
      merchant_name: Merchant name
    """
    try:
        tabs = json.loads(tabs_json)
        agreement = json.loads(agreement_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    result = await fill_gokwik_dashboard(tabs, agreement, merchant_name)
    return result


@router.post("/verify")
async def playwright_verify(
    expected_json: str = Form(...),
    merchant_name: str = Form("Unknown"),
):
    """
    Read back rates from real GoKwik and compare against expected (PDF).

    Input:
      expected_json: JSON string of expected mapped rates
      merchant_name: Merchant name

    Returns: comparison result with discrepancies
    """
    try:
        expected_mapped = json.loads(expected_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Read back from GoKwik
    read_result = await verify_gokwik_dashboard(merchant_name)

    if not read_result["success"]:
        return {
            "success": False,
            "message": read_result["message"],
            "screenshot": read_result.get("screenshot"),
        }

    actual_rates = read_result["actual_rates"]

    # Compare expected vs actual
    discrepancies, matched_entries, total_modes = compare_rates(expected_mapped, actual_rates)
    report = generate_report(merchant_name, discrepancies, total_modes, matched_entries)

    # Auto-email on mismatch
    email_result = None
    if report["has_discrepancies"] and is_email_configured():
        email_result = send_mismatch_report(merchant_name, report)

    return {
        "success": True,
        "all_match": not report["has_discrepancies"],
        "report": report,
        "actual_rates": actual_rates,
        "total_read": read_result["total_read"],
        "screenshot": read_result.get("screenshot"),
        "email_sent": email_result,
        "message": f"Verified: {report['matched']} matched, {report['mismatched']} mismatched out of {total_modes}",
    }


@router.post("/confirm")
async def playwright_confirm():
    """Click Confirm on real GoKwik dashboard."""
    result = await confirm_gokwik_dashboard()
    return result


@router.get("/screenshot/{name}")
async def get_screenshot(name: str):
    """Serve a screenshot image."""
    import os
    screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "screenshots")
    path = os.path.join(screenshot_dir, f"{name}.png")
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Screenshot not found")
