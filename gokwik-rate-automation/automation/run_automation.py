"""
GoKwik Rate Capture Automation — End-to-End Pipeline.

Logs into real GoKwik dashboard, extracts data from PDFs, and fills
the Rate Capture form automatically.

Flow:
  1. Launch Chrome, login to real GoKwik (email + password + OTP)
  2. Navigate to Rate Capture via sidebar menu
  3. Select existing merchant OR create new agreement
  4. Extract rates from PDFs (via backend API or local files)
  5. Auto-fill agreement details + rates across all payment tabs
  6. Save as Draft for checker to confirm

Usage:
  # Full auto via Google Drive (backend must be running):
  python -m automation.run_automation --merchant "Jaipur Masala"

  # With local PDF files:
  python -m automation.run_automation --merchant "Sandbox" \\
      --agreement sample_agreement.pdf --rate-card sample_rate_card.pdf

  # Edit existing merchant (don't create new):
  python -m automation.run_automation --merchant "Jaipur Masala" --edit

  # Headless mode:
  python -m automation.run_automation --merchant "Jaipur" --headless

  # Specific sandbox user:
  python -m automation.run_automation --merchant "Jaipur" --user 2
"""

import argparse
import asyncio
import json
import sys
import os
import requests

from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.config import DASHBOARD_URL, API_BASE, PAGE_TIMEOUT, GOKWIK_URL, GOKWIK_EMAIL, GOKWIK_PASSWORD, GOKWIK_OTP
from automation.login import login_to_gokwik, navigate_to_rate_capture
from automation.gokwik_filler import fill_gokwik

SANDBOX_USERS = {
    1: {
        "email": os.getenv("SANDBOX_USER_1_EMAIL", "sandboxuser1@gokwik.co"),
        "password": os.getenv("SANDBOX_USER_1_PASSWORD", "Wb7y,=e.9NX9"),
        "otp": os.getenv("SANDBOX_USER_1_OTP", "123456"),
    },
    2: {
        "email": os.getenv("SANDBOX_USER_2_EMAIL", "sandboxuser2@gokwik.co"),
        "password": os.getenv("SANDBOX_USER_2_PASSWORD", "Wb7y,=e.9NX2"),
        "otp": os.getenv("SANDBOX_USER_2_OTP", "123456"),
    },
    3: {
        "email": os.getenv("SANDBOX_USER_3_EMAIL", "sandboxuser3@gokwik.co"),
        "password": os.getenv("SANDBOX_USER_3_PASSWORD", "Wb7y,=e.9NX3"),
        "otp": os.getenv("SANDBOX_USER_3_OTP", "123456"),
    },
}


def call_extraction_api(agreement_pdf: str, rate_pdf: str, merchant_name: str) -> dict:
    """Call backend to extract data from local PDFs."""
    print(f"[API] Extracting from PDFs...")
    files = {
        'agreement_pdf': (os.path.basename(agreement_pdf), open(agreement_pdf, 'rb')),
        'rate_pdf': (os.path.basename(rate_pdf), open(rate_pdf, 'rb')),
    }
    resp = requests.post(f"{API_BASE}/api/auto-process",
                         files=files, data={'merchant_name': merchant_name}, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise Exception(f"Extraction failed: {result.get('error')}")
    print(f"[API] Extracted {result['raw_rates_count']} rates across {len(result.get('tabs', {}))} tabs")
    return result


def call_drive_api(merchant_name: str) -> dict:
    """Call backend to search Drive, download, and extract PDFs for a merchant."""
    print(f"[API] Fetching from Google Drive for '{merchant_name}'...")
    resp = requests.post(f"{API_BASE}/api/gokwik/fill-from-drive",
                         data={'merchant_name': merchant_name, 'is_new': 'true'}, timeout=120)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("success"):
        raise Exception(f"Drive fetch failed: {result.get('message')}")
    return result


async def run_pipeline(
    merchant_name: str,
    headless: bool = False,
    extraction_data: dict = None,
    email: str = None,
    password: str = None,
    otp: str = None,
    is_new: bool = True,
):
    """
    Main automation pipeline:
    1. Login to GoKwik (email + password + OTP)
    2. Navigate to Rate Capture via sidebar
    3. Fill rates from extracted data
    4. Save and report
    """
    async with async_playwright() as p:
        print(f"\n[Playwright] Launching Chrome {'(headless)' if headless else '(visible)'}...")
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=50,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        try:
            # ─── Step 1: Login ────────────────────────────
            print(f"[Playwright] Logging into GoKwik as {email}...")
            success = await login_to_gokwik(page, email=email, password=password, otp=otp)
            if not success:
                print("[Playwright] Login failed! Aborting.")
                await page.screenshot(path="login_failed.png", full_page=True)
                return

            print("[Playwright] Login successful!")

            # ─── Step 2: Navigate to Rate Capture via sidebar ─
            print("[Playwright] Navigating to Rate Capture via sidebar...")
            nav_success = await navigate_to_rate_capture(page)
            if not nav_success:
                print("[Playwright] Could not navigate to Rate Capture!")
                await page.screenshot(path="nav_failed.png", full_page=True)
                return

            print(f"[Playwright] On Rate Capture page: {page.url}")
            await page.screenshot(path="rate_capture_loaded.png", full_page=True)

            # ─── Step 3: Prepare extraction data ──────────
            if not extraction_data:
                print("[Playwright] No extraction data provided. Skipping auto-fill.")
                print("[Playwright] Use --agreement and --rate-card to provide PDFs")
                print("[Playwright] Or ensure backend is running for Drive mode")
                if not headless:
                    print("\n[Playwright] Browser open for manual use. Press Enter to close...")
                    input()
                await browser.close()
                return

            agreement = extraction_data.get("agreement", {})
            tabs = extraction_data.get("tabs", {})
            rate_card_path = extraction_data.get("rate_card_path", "")

            total_rates = sum(len(v) for v in tabs.items())
            print(f"\n[Playwright] Extraction data ready:")
            print(f"  Agreement: {agreement.get('start_date', 'N/A')} to {agreement.get('end_date', 'N/A')}")
            print(f"  Tabs: {list(tabs.keys())}")
            print(f"  Total rates: {total_rates}")

            # ─── Step 4: Fill the form ────────────────────
            print("\n" + "=" * 55)
            print("  AUTO-FILL: Filling Real GoKwik Dashboard")
            print("=" * 55)

            result = await fill_gokwik(
                merchant_name=merchant_name,
                rate_card_path=rate_card_path,
                agreement=agreement,
                tabs=tabs,
                is_new=is_new,
                page=page,
            )

            # ─── Step 5: Report results ───────────────────
            print("\n" + "=" * 55)
            if result["success"]:
                print(f"  [OK] FILLED: {result['filled']} rates")
                print(f"  [OK] Failed: {result['failed']}")
                print(f"  [OK] Status: Draft (ready for checker)")
            else:
                print(f"  [FAIL] {result['message']}")
            print("=" * 55)

            # Print step details
            for step in result.get("steps", []):
                icon = "✓" if step["status"] == "done" else "✗" if step["status"] == "failed" else "⚠"
                print(f"  {icon} {step['text']}")

            # Take final screenshot
            await page.screenshot(path="automation_complete.png", full_page=True)
            print(f"\n[Playwright] Screenshot: automation_complete.png")

            # Keep browser open for review in visible mode
            if not headless:
                if result["success"]:
                    confirm = input("\n  Confirm and finalize? (y/n): ").strip().lower()
                    if confirm == 'y':
                        try:
                            confirm_btn = page.get_by_role("button", name="Confirm")
                            await confirm_btn.click()
                            await page.wait_for_timeout(2000)
                            print("  [OK] CONFIRMED!")
                            await page.screenshot(path="confirmed.png", full_page=True)
                        except Exception as e:
                            print(f"  [WARN] Confirm failed: {e}")
                    else:
                        print("  Left as Draft.")
                print("\n[Playwright] Press Enter to close browser...")
                input()

        except Exception as e:
            print(f"\n[Playwright] ERROR: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path="error_screenshot.png", full_page=True)
            except Exception:
                pass
        finally:
            await browser.close()
            print("[Playwright] Browser closed")


def main():
    parser = argparse.ArgumentParser(description="GoKwik Rate Capture Automation")
    parser.add_argument("--merchant", required=True, help="Merchant name")
    parser.add_argument("--agreement", help="Path to Agreement PDF (local)")
    parser.add_argument("--rate-card", help="Path to Rate Card PDF (local)")
    parser.add_argument("--headless", action="store_true", help="Run without visible browser")
    parser.add_argument("--edit", action="store_true", help="Edit existing merchant (don't create new)")
    parser.add_argument("--user", type=int, choices=[1, 2, 3], help="Sandbox user number")
    parser.add_argument("--email", help="Override login email")
    parser.add_argument("--password", help="Override login password")
    parser.add_argument("--otp", help="Override login OTP")
    parser.add_argument("--drive", action="store_true", help="Fetch PDFs from Google Drive (requires backend)")
    args = parser.parse_args()

    # Resolve login credentials
    if args.user:
        user = SANDBOX_USERS[args.user]
        email = args.email or user["email"]
        password = args.password or user["password"]
        otp = args.otp or user["otp"]
    else:
        email = args.email or GOKWIK_EMAIL
        password = args.password or GOKWIK_PASSWORD
        otp = args.otp or GOKWIK_OTP

    is_new = not args.edit

    print("=" * 55)
    print("  GoKwik Rate Capture Automation")
    print("=" * 55)
    print(f"  Merchant:  {args.merchant}")
    print(f"  Mode:      {'Local PDFs' if args.agreement else 'Google Drive' if args.drive else 'Manual'}")
    print(f"  Action:    {'New agreement' if is_new else 'Edit existing'}")
    print(f"  Dashboard: {GOKWIK_URL} ({email})")
    print(f"  Browser:   {'Headless' if args.headless else 'Visible'}")
    print("=" * 55)

    # Extract data from PDFs
    extraction_data = None

    if args.agreement and args.rate_card:
        # Local PDF mode: extract via backend API
        try:
            extraction_data = call_extraction_api(args.agreement, args.rate_card, args.merchant)
        except Exception as e:
            print(f"[ERROR] Extraction failed: {e}")
            print("[ERROR] Make sure backend is running: python run.py")
            sys.exit(1)

    elif args.drive:
        # Google Drive mode: search + download + extract via backend
        try:
            extraction_data = call_drive_api(args.merchant)
        except Exception as e:
            print(f"[ERROR] Drive fetch failed: {e}")
            print("[ERROR] Make sure backend is running and Drive is configured")
            sys.exit(1)

    # Run the automation pipeline
    asyncio.run(run_pipeline(
        merchant_name=args.merchant,
        headless=args.headless,
        extraction_data=extraction_data,
        email=email,
        password=password,
        otp=otp,
        is_new=is_new,
    ))


if __name__ == "__main__":
    main()
