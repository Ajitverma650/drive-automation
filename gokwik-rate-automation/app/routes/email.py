"""Email and health-check routes."""

import json

from fastapi import APIRouter, Form, HTTPException

from app.services.email import send_mismatch_report, is_email_configured

router = APIRouter()


@router.post("/api/send-report")
async def send_report_email(
    merchant_name: str = Form(...),
    report_json: str = Form(...),
    extra_emails: str = Form(""),
):
    """
    Manually send a mismatch report email.
    Use this if auto-email failed or you want to send to additional recipients.
    """
    try:
        report = json.loads(report_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid report JSON")

    extras = [e.strip() for e in extra_emails.split(",") if e.strip()] if extra_emails else []

    result = send_mismatch_report(merchant_name, report, extra_recipients=extras)
    return result


@router.get("/api/email-status")
async def email_status():
    """Check if email is configured."""
    configured = is_email_configured()
    return {
        "configured": configured,
        "message": "Email is configured and ready" if configured else "Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO in .env",
    }


@router.get("/api/health")
async def health():
    return {"status": "ok", "service": "gokwik-rate-automation"}
