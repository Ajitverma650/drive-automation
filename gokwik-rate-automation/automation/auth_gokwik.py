"""
GoKwik Dashboard — Programmatic Login (Email + Password + OTP).

No more manual login or persistent browser profiles.
Logs in automatically using credentials from .env.

Usage:
    python -m automation.auth_gokwik
    python -m automation.auth_gokwik --user 2     # Use SANDBOX_USER_2
    python -m automation.auth_gokwik --email X --password Y --otp Z
"""

import argparse
import asyncio
import os

from playwright.async_api import async_playwright

from automation.config import GOKWIK_URL, GOKWIK_EMAIL, GOKWIK_PASSWORD, GOKWIK_OTP
from automation.login import login_to_gokwik

# Sandbox test users
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
    print("  GoKwik Dashboard — Login Test")
    print("=" * 55)
    print(f"  URL:   {GOKWIK_URL}")
    print(f"  Email: {email}")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        success = await login_to_gokwik(page, email=email, password=password, otp=otp)

        if success:
            print("\n[Auth] Login successful! Navigating to Rate Capture...")
            await page.goto(f"{GOKWIK_URL}/general/rateCapture")
            await page.wait_for_timeout(3000)
            await page.screenshot(path="gokwik_session_test.png", full_page=True)
            print("[Auth] Screenshot: gokwik_session_test.png")
            print(f"[Auth] Final URL: {page.url}")
        else:
            print("\n[Auth] Login FAILED. Check credentials or screenshot.")

        print("\n  Press Enter to close browser...")
        input()
        await browser.close()

    print("\n" + "=" * 55)
    print("  Done!")
    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoKwik Login Test")
    parser.add_argument("--user", type=int, choices=[1, 2, 3], help="Sandbox user number (1, 2, or 3)")
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
