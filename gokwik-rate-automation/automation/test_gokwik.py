"""
Test: Login to real GoKwik dashboard and read Rate Capture page.

Uses email + password + OTP login (no saved session files needed).

Usage:
    python -m automation.test_gokwik
    python -m automation.test_gokwik --user 2
"""

import argparse
import asyncio
import os

from playwright.async_api import async_playwright

from automation.config import (
    GOKWIK_URL, GOKWIK_EMAIL, GOKWIK_PASSWORD, GOKWIK_OTP,
)
from automation.login import login_to_gokwik

PAYMENT_TABS = ['EMI', 'UPI', 'NetBanking', 'Wallet', 'Credit Card', 'Debit Card', 'BNPL', 'COD', 'Others', 'PPCOD']

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


async def main(email: str, password: str, otp: str):
    print("=" * 55)
    print("  GoKwik Dashboard - Login & Read Test")
    print("=" * 55)
    print(f"  Email: {email}")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        # Login with email + password + OTP
        success = await login_to_gokwik(page, email=email, password=password, otp=otp)

        if not success:
            print("\n[Test] Login failed! Check credentials.")
            await browser.close()
            return

        # Take screenshot of landing page
        await page.screenshot(path="gokwik_1_landing.png", full_page=True)
        print("[Test] Screenshot: gokwik_1_landing.png")

        # Find and click Rate Capture in sidebar
        print("[Test] Looking for Rate Capture in sidebar...")
        found_nav = False
        for nav_text in ['Rate Checkout', 'Rate Capture', 'Checkout Setup', 'rate capture']:
            try:
                await page.click(f"text={nav_text}", timeout=2000)
                await page.wait_for_timeout(3000)
                found_nav = True
                print(f"[Test] Clicked: {nav_text}")
                break
            except Exception:
                continue

        if not found_nav:
            # Try direct URL
            print("[Test] Trying direct URL for Rate Capture...")
            await page.goto(f"{GOKWIK_URL}/general/rateCapture", timeout=15000)
            await page.wait_for_timeout(3000)

        # Take screenshot after navigation
        await page.screenshot(path="gokwik_2_rate_capture.png", full_page=True)
        print("[Test] Screenshot: gokwik_2_rate_capture.png")

        # Read page content
        info = await page.evaluate("""() => {
            return {
                url: window.location.href,
                inputs: document.querySelectorAll('input').length,
                tables: document.querySelectorAll('table').length,
                selects: document.querySelectorAll('select').length,
                buttons: [...document.querySelectorAll('button')].map(b => b.textContent.trim()).filter(Boolean).slice(0, 20),
                labels: [...document.querySelectorAll('label,th,h3,h4')].map(el => el.textContent.trim()).filter(Boolean).slice(0, 30),
                allClickable: [...document.querySelectorAll('[role=tab], .ant-tabs-tab, [class*=tab]')].map(el => el.textContent.trim()).filter(Boolean).slice(0, 20),
            }
        }""")

        print(f"\n[Test] Page info:")
        print(f"  URL: {info['url']}")
        print(f"  Inputs: {info['inputs']}")
        print(f"  Tables: {info['tables']}")
        print(f"  Selects: {info['selects']}")
        print(f"  Buttons: {info['buttons']}")
        print(f"  Labels: {info['labels'][:15]}")
        print(f"  Tabs/clickable: {info['allClickable']}")

        # Try reading commission tables
        if info['tables'] > 0:
            print(f"\n[Test] Reading commission tables...")
            for tab_name in PAYMENT_TABS:
                try:
                    tab = page.get_by_text(tab_name, exact=True).first
                    if await tab.is_visible(timeout=1000):
                        await tab.click()
                        await page.wait_for_timeout(500)

                        rows = await page.query_selector_all("table tbody tr")
                        if rows:
                            print(f"\n  [{tab_name}] {len(rows)} row(s):")
                            for row in rows[:5]:
                                cells = await row.query_selector_all("td")
                                if len(cells) >= 3:
                                    method = (await cells[0].inner_text()).strip()
                                    comm_type = (await cells[1].inner_text()).strip()
                                    value = (await cells[2].inner_text()).strip()
                                    if method:
                                        print(f"    {method:20s} | {comm_type:12s} | {value}")
                except Exception:
                    pass

        print(f"\n[Test] Done! Browser open for inspection.")
        print(f"  Press Enter to close...")
        input()

        await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoKwik Login & Read Test")
    parser.add_argument("--user", type=int, choices=[1, 2, 3], help="Sandbox user number")
    parser.add_argument("--email", help="Override email")
    parser.add_argument("--password", help="Override password")
    parser.add_argument("--otp", help="Override OTP")
    args = parser.parse_args()

    if args.user:
        user = SANDBOX_USERS[args.user]
        email = args.email or user["email"]
        password = args.password or user["password"]
        otp = args.otp or user["otp"]
    else:
        email = args.email or GOKWIK_EMAIL
        password = args.password or GOKWIK_PASSWORD
        otp = args.otp or GOKWIK_OTP

    asyncio.run(main(email, password, otp))
