"""
Long-running Playwright browser server.

Keeps ONE Chrome browser open with GoKwik session.
The FastAPI backend connects to this browser for fill/verify/confirm.

Usage:
    python -m automation.browser_server

Flow:
    1. Opens Chrome (visible)
    2. You login to GoKwik with Google
    3. Navigate to Rate Capture
    4. Press Enter → browser stays open
    5. FastAPI backend uses this browser via CDP
    6. Ctrl+C to stop
"""

import asyncio
import os
import signal
import sys

from playwright.async_api import async_playwright

GOKWIK_URL = "https://sandbox-mdashboard.dev.gokwik.in"
CDP_PORT = 9222  # Chrome DevTools Protocol port


async def main():
    print("=" * 55)
    print("  GoKwik Browser Server")
    print("=" * 55)
    print(f"  GoKwik URL: {GOKWIK_URL}")
    print(f"  CDP Port:   {CDP_PORT}")
    print("=" * 55)

    async with async_playwright() as p:
        # Launch Chrome with CDP (remote debugging) enabled
        # This allows the FastAPI backend to connect to this browser
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

        # Navigate to GoKwik
        await page.goto(GOKWIK_URL)
        await page.wait_for_timeout(2000)

        print("\n" + "-" * 55)
        print("  1. Login to GoKwik with Google in the browser")
        print("  2. Navigate to Rate Capture page")
        print("  3. Press ENTER here when ready")
        print("-" * 55)
        input("\n  Press ENTER after login...")

        print(f"\n[Server] Logged in! URL: {page.url}")
        print(f"[Server] CDP running on port {CDP_PORT}")
        print(f"[Server] Browser will stay open.")
        print(f"[Server] Press Ctrl+C to stop.\n")

        # Save CDP endpoint for the backend to use
        ws_endpoint = browser.contexts[0].pages[0].url  # not needed, we use CDP port
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
    asyncio.run(main())
