"""
Long-running Playwright browser server.

Keeps ONE Chrome browser open with GoKwik session.
The FastAPI backend connects to this browser for fill/verify/confirm.

Logs in automatically with email + password + OTP (no persistent profiles needed).

Usage:
    python -m automation.browser_server
    python -m automation.browser_server --user 2   # Use sandbox user 2

Flow:
    1. Opens Chrome (visible)
    2. Logs in automatically with email + password + OTP
    3. FastAPI backend uses this browser via CDP
    4. Ctrl+C to stop
"""

import argparse
import asyncio
import os

from playwright.async_api import async_playwright

from automation.config import GOKWIK_URL, GOKWIK_EMAIL, GOKWIK_PASSWORD, GOKWIK_OTP
from automation.login import login_to_gokwik

CDP_PORT = 9222  # Chrome DevTools Protocol port

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
    print("  GoKwik Browser Server")
    print("=" * 55)
    print(f"  GoKwik URL:  {GOKWIK_URL}")
    print(f"  CDP Port:    {CDP_PORT}")
    print(f"  Login:       {email}")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                f"--remote-debugging-port={CDP_PORT}",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        # Login with email + password + OTP
        success = await login_to_gokwik(page, email=email, password=password, otp=otp)

        if not success:
            print("\n[Server] Login FAILED. Check credentials.")
            print("[Server] Keeping browser open for manual inspection...")
            print("[Server] Press Ctrl+C to stop.\n")
        else:
            print(f"\n[Server] Logged in! URL: {page.url}")

        print(f"[Server] CDP running on port {CDP_PORT}")
        print(f"[Server] Press Ctrl+C to stop.\n")

        # Save CDP endpoint for the backend to use
        cdp_file = os.path.join(os.path.dirname(__file__), "..", "gokwik_cdp.txt")
        with open(cdp_file, "w") as f:
            f.write(f"http://localhost:{CDP_PORT}")
        print(f"[Server] CDP endpoint saved to: {os.path.abspath(cdp_file)}")

        # Keep running until Ctrl+C
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n[Server] Shutting down...")
        finally:
            try:
                os.remove(cdp_file)
            except Exception:
                pass
            await browser.close()
            print("[Server] Browser closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoKwik Browser Server")
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
