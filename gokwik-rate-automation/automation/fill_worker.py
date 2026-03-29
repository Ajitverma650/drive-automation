"""
GoKwik Fill Worker — runs as a SEPARATE PROCESS to launch a visible browser.

Called by the backend via subprocess when "Fill GoKwik" is triggered.
Opens a visible Chrome window, logs in, fills rates, writes result to JSON.

Usage:
    python -m automation.fill_worker --data extraction_data.json --output result.json
"""

import argparse
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from automation.login import login_to_gokwik, navigate_to_rate_capture
from automation.config import GOKWIK_EMAIL, GOKWIK_PASSWORD, GOKWIK_OTP


async def run_fill(data_path: str, output_path: str):
    """Launch visible Chrome, login to GoKwik, fill rates, save result."""

    # Load extraction data
    with open(data_path, 'r') as f:
        data = json.load(f)

    merchant_name = data.get("merchant_name", "Unknown")
    agreement = data.get("agreement", {})
    tabs = data.get("tabs", {})
    rate_card_path = data.get("rate_card_path", "")
    agreement_pdf_path = data.get("agreement_pdf_path", "")

    result = {
        "success": False,
        "filled": 0,
        "failed": 0,
        "steps": [],
        "message": "",
    }

    print(f"[Fill Worker] Starting for merchant: {merchant_name}")
    print(f"[Fill Worker] Tabs: {list(tabs.keys())}")
    print(f"[Fill Worker] Total rates: {sum(len(v) for v in tabs.values())}")
    print(f"[Fill Worker] Rate card: {rate_card_path} (exists: {os.path.exists(rate_card_path) if rate_card_path else 'N/A'})")
    print(f"[Fill Worker] Agreement PDF: {agreement_pdf_path} (exists: {os.path.exists(agreement_pdf_path) if agreement_pdf_path else 'N/A'})")

    # Use agreement PDF for upload if rate card not available
    # GoKwik needs ANY PDF in the "Merchant Agreement" field
    upload_pdf = ""
    if rate_card_path and os.path.exists(rate_card_path):
        upload_pdf = rate_card_path
    elif agreement_pdf_path and os.path.exists(agreement_pdf_path):
        upload_pdf = agreement_pdf_path
    print(f"[Fill Worker] Will upload: {upload_pdf or 'placeholder'}")

    async with async_playwright() as p:
        # Launch VISIBLE browser
        print("[Fill Worker] Launching visible Chrome...")
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=30,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        try:
            # ─── Step 1: Login ────────────────────────
            print(f"[Fill Worker] Logging into GoKwik as {GOKWIK_EMAIL}...")
            success = await login_to_gokwik(page,
                                             email=GOKWIK_EMAIL,
                                             password=GOKWIK_PASSWORD,
                                             otp=GOKWIK_OTP)
            if not success:
                result["message"] = f"GoKwik login failed. URL: {page.url}"
                print(f"[Fill Worker] Login FAILED. URL: {page.url}")
                os.makedirs("screenshots", exist_ok=True)
                await page.screenshot(path="screenshots/worker_login_failed.png", full_page=True)
                # Keep browser open 10s so user can see what went wrong
                print("[Fill Worker] Keeping browser open for 10s...")
                await page.wait_for_timeout(10000)
                await browser.close()
                return result

            result["steps"].append({"step": "login", "status": "done", "text": "Logged into GoKwik"})
            print("[Fill Worker] Login successful!")
            print(f"[Fill Worker] Current URL: {page.url}")

            # ─── Step 2: Navigate to Rate Capture ─────
            if "rateCapture" not in page.url:
                print("[Fill Worker] Navigating to Rate Capture...")
                nav_ok = await navigate_to_rate_capture(page)
                if not nav_ok:
                    result["message"] = "Could not navigate to Rate Capture"
                    print("[Fill Worker] Navigation failed. Keeping browser open 10s...")
                    await page.wait_for_timeout(10000)
                    await browser.close()
                    return result
            else:
                print("[Fill Worker] Already on Rate Capture page")

            result["steps"].append({"step": "navigate", "status": "done", "text": "On Rate Capture page"})
            print(f"[Fill Worker] On Rate Capture: {page.url}")

            # Wait for page to fully load
            await page.wait_for_timeout(2000)

            # ─── Step 3: Fill the form ────────────────
            from automation.gokwik_filler import fill_gokwik

            print(f"[Fill Worker] Starting form fill... (upload: {upload_pdf or 'placeholder'})")
            fill_result = await fill_gokwik(
                merchant_name=merchant_name,
                rate_card_path=upload_pdf,
                agreement=agreement,
                tabs=tabs,
                is_new=True,
                page=page,
            )

            result["success"] = fill_result["success"]
            result["filled"] = fill_result.get("filled", 0)
            result["failed"] = fill_result.get("failed", 0)
            result["steps"].extend(fill_result.get("steps", []))
            result["message"] = fill_result.get("message", "")

            # Screenshot
            os.makedirs("screenshots", exist_ok=True)
            ss_path = "screenshots/gokwik_fill_complete.png"
            await page.screenshot(path=ss_path, full_page=True)
            result["screenshot"] = ss_path

            print(f"[Fill Worker] Done: {result['filled']} filled, {result['failed']} failed")

            # Keep browser open so user can review the filled form
            print("[Fill Worker] Keeping browser open 35s for review...")
            await page.wait_for_timeout(35000)

        except Exception as e:
            import traceback
            traceback.print_exc()
            result["message"] = f"Error: {str(e)}"
            print(f"[Fill Worker] ERROR: {e}")
            # Keep browser open on error so user can debug
            print("[Fill Worker] Error occurred. Keeping browser open 35s...")
            try:
                await page.wait_for_timeout(35000)
            except Exception:
                pass

        finally:
            await browser.close()
            print("[Fill Worker] Browser closed")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to extraction data JSON")
    parser.add_argument("--output", required=True, help="Path to write result JSON")
    args = parser.parse_args()

    result = asyncio.run(run_fill(args.data, args.output))

    # Write result
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"[Fill Worker] Result written to {args.output}")
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
