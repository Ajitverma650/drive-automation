"""Email service for sending mismatch reports to IT support team."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from app.config import get_smtp_config

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    """Check if email is properly configured."""
    return get_smtp_config() is not None


def send_mismatch_report(
    merchant_name: str,
    report: dict,
    extra_recipients: list[str] = None,
) -> dict:
    """
    Send a mismatch report email to the IT support team.

    Args:
        merchant_name: Name of the merchant
        report: Report dict from generate_report()
        extra_recipients: Additional email addresses to send to

    Returns:
        {"success": bool, "message": str, "sent_to": list}
    """
    config = get_smtp_config()
    if not config:
        return {
            "success": False,
            "message": "Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO in .env",
            "sent_to": [],
        }

    now = datetime.now().strftime("%d/%m/%Y %H:%M IST")
    matched = report.get("matched", 0)
    mismatched = report.get("mismatched", 0)
    total = report.get("total", 0)
    discrepancies = report.get("discrepancies", [])

    # Build recipient list
    recipients = list(config["to"])
    if extra_recipients:
        recipients.extend([e.strip() for e in extra_recipients if e.strip()])
    recipients = list(set(recipients))  # deduplicate

    # ─── Build email ─────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[ALERT] Rate Mismatch - {merchant_name} ({mismatched} discrepancies)"
    msg["From"] = config["from"]
    msg["To"] = ", ".join(recipients)
    if config["cc"]:
        msg["Cc"] = ", ".join(config["cc"])

    # Plain text body
    plain_body = report.get("summary", "")

    # HTML body (rich email)
    disc_rows = ""
    for d in discrepancies:
        disc_rows += f"""
        <tr style="background: #fff5f5;">
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{d.get('mode', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{d.get('tab', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{d.get('method', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #27ae60; font-weight: 600;">{d.get('expected_rate', '')}%</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #e74c3c; font-weight: 600;">{d.get('actual_rate', '')}%</td>
        </tr>"""

    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #2d3436; max-width: 700px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 24px 32px; border-radius: 12px 12px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 20px;">Rate Capture - Mismatch Alert</h1>
            <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0 0; font-size: 14px;">Automated verification detected discrepancies</p>
        </div>

        <div style="background: #fff; padding: 24px 32px; border: 1px solid #e0e0e0; border-top: none;">
            <table style="width: 100%; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 4px 0; color: #636e72;">Merchant:</td>
                    <td style="padding: 4px 0; font-weight: 600;">{merchant_name}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #636e72;">Date:</td>
                    <td style="padding: 4px 0;">{now}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #636e72;">Verified by:</td>
                    <td style="padding: 4px 0;">Rate Capture Automation (Phase 2)</td>
                </tr>
            </table>

            <div style="display: flex; gap: 16px; margin-bottom: 24px;">
                <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; flex: 1; border-left: 4px solid #27ae60;">
                    <div style="font-size: 28px; font-weight: 700; color: #27ae60;">{matched}</div>
                    <div style="font-size: 12px; color: #636e72; margin-top: 4px;">Matched</div>
                </div>
                <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; flex: 1; border-left: 4px solid #e74c3c;">
                    <div style="font-size: 28px; font-weight: 700; color: #e74c3c;">{mismatched}</div>
                    <div style="font-size: 12px; color: #636e72; margin-top: 4px;">Mismatched</div>
                </div>
                <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; flex: 1; border-left: 4px solid #3498db;">
                    <div style="font-size: 28px; font-weight: 700; color: #3498db;">{total}</div>
                    <div style="font-size: 12px; color: #636e72; margin-top: 4px;">Total Modes</div>
                </div>
            </div>

            <h3 style="color: #e74c3c; margin-bottom: 12px;">Discrepancies</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #ddd;">Mode</th>
                        <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #ddd;">Tab</th>
                        <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #ddd;">Method</th>
                        <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #ddd;">Expected (PDF)</th>
                        <th style="padding: 10px 12px; text-align: left; border-bottom: 2px solid #ddd;">Actual (Dashboard)</th>
                    </tr>
                </thead>
                <tbody>
                    {disc_rows}
                </tbody>
            </table>

            <div style="background: #ffeaa7; border-radius: 8px; padding: 16px; margin-top: 24px;">
                <strong>Action Required:</strong>
                <ol style="margin: 8px 0 0 0; padding-left: 20px;">
                    <li>Maker to correct the above modes in the dashboard</li>
                    <li>Re-run Phase 1 for corrections</li>
                    <li>Re-run Phase 2 to verify</li>
                    <li>Do NOT click Confirm until all rates match</li>
                </ol>
            </div>
        </div>

        <div style="background: #f8f9fa; padding: 16px 32px; border-radius: 0 0 12px 12px; border: 1px solid #e0e0e0; border-top: none; text-align: center; color: #b2bec3; font-size: 12px;">
            Sent by GoKwik Rate Capture Automation | This is an automated message
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Attach CSV report
    csv_content = report.get("csv_content", "")
    if csv_content:
        csv_attachment = MIMEBase("application", "octet-stream")
        csv_attachment.set_payload(csv_content.encode("utf-8"))
        encoders.encode_base64(csv_attachment)
        filename = f"rate_mismatch_{merchant_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        csv_attachment.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(csv_attachment)

    # ─── Send email ─────────────────────────────────
    all_recipients = recipients + config["cc"]

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=15) as server:
            server.starttls()
            server.login(config["user"], config["password"])
            server.sendmail(config["from"], all_recipients, msg.as_string())

        print(f"[Email] Mismatch report sent to {', '.join(all_recipients)}")
        return {
            "success": True,
            "message": f"Report sent to {len(all_recipients)} recipient(s)",
            "sent_to": all_recipients,
        }

    except smtplib.SMTPAuthenticationError:
        msg = "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env"
        logger.error(f"[Email] {msg}")
        return {"success": False, "message": msg, "sent_to": []}

    except smtplib.SMTPException as e:
        msg = f"SMTP error: {e}"
        logger.error(f"[Email] {msg}")
        return {"success": False, "message": msg, "sent_to": []}

    except Exception as e:
        msg = f"Email failed: {e}"
        logger.error(f"[Email] {msg}")
        return {"success": False, "message": msg, "sent_to": []}
