"""
Long-running Playwright browser server.

Keeps ONE Chrome browser open with GoKwik session.
The FastAPI backend connects to this browser for fill/verify/confirm.

Uses a persistent user-data directory so login cookies survive restarts.
After the first login, subsequent starts will auto-login.

Usage:
    python -m automation.browser_server

Flow:
    1. Opens Chrome (visible) with persistent profile
    2. First time: login to GoKwik with Google, press Enter
    3. Next times: auto-logged-in from saved cookies
    4. FastAPI backend uses this browser via CDP
    5. Ctrl+C to stop
"""

import asyncio
import os
import signal
import sys

from playwright.async_api import async_playwright

GOKWIK_URL = "https://sandbox-mdashboard.dev.gokwik.in"
CDP_PORT = 9222  # Chrome DevTools Protocol port

# Persistent profile directory — cookies/sessions survive restarts
USER_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "browser_data",
)


async def main():
    print("=" * 55)
    print("  GoKwik Browser Server")
    print("=" * 55)
    print(f"  GoKwik URL:  {GOKWIK_URL}")
    print(f"  CDP Port:    {CDP_PORT}")
    print(f"  Profile Dir: {USER_DATA_DIR}")
    print("=" * 55)

    os.makedirs(USER_DATA_DIR, exist_ok=True)

    async with async_playwright() as p:
        # Launch with persistent context — cookies are saved to disk
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=[
                f"--remote-debugging-port={CDP_PORT}",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )

        # Use existing page or create one
        page = context.pages[0] if context.pages else await context.new_page()

        # Navigate to GoKwik
        await page.goto(GOKWIK_URL)
        await page.wait_for_timeout(3000)

        # Check if already logged in (not redirected to login page)
        if "login" in page.url.lower():
            print("\n" + "-" * 55)
            print("  Not logged in yet (first time or session expired)")
            print("  1. Login to GoKwik with Google in the browser")
            print("  2. Navigate to Rate Capture page")
            print("  3. Press ENTER here when ready")
            print("-" * 55)
            input("\n  Press ENTER after login...")
        else:
            print("\n  Auto-logged in from saved session!")

        print(f"\n[Server] Logged in! URL: {page.url}")
        print(f"[Server] CDP running on port {CDP_PORT}")
        print(f"[Server] Browser will stay open.")
        print(f"[Server] Cookies saved to: {USER_DATA_DIR}")
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
            await context.close()
            print("[Server] Browser closed. Session saved.")


if __name__ == "__main__":
    asyncio.run(main())
