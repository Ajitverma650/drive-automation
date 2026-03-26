"""
One-time GoKwik dashboard login script.
Opens Chrome → you login manually → saves session for future automation.

Usage:
    python -m automation.auth_gokwik
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

GOKWIK_URL = "https://sandbox-mdashboard.dev.gokwik.in"
SESSION_FILE = os.path.join(os.path.dirname(__file__), "..", "gokwik_session.json")


async def main():
    print("=" * 55)
    print("  GoKwik Dashboard - Save Login Session")
    print("=" * 55)
    print(f"  URL: {GOKWIK_URL}")
    print(f"  Session file: {os.path.abspath(SESSION_FILE)}")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        print("\n[Auth] Opening GoKwik dashboard...")
        await page.goto(GOKWIK_URL)

        print("\n" + "-" * 55)
        print("  LOGIN MANUALLY in the browser window.")
        print("  Navigate to the Rate Capture page.")
        print("  Then come back here and press ENTER.")
        print("-" * 55)
        input("\n  Press ENTER after you've logged in and see Rate Capture page...")

        # Verify we're on the right page
        current_url = page.url
        print(f"\n[Auth] Current URL: {current_url}")

        # Save session (cookies + localStorage)
        await context.storage_state(path=SESSION_FILE)
        print(f"[Auth] Session saved to: {os.path.abspath(SESSION_FILE)}")

        print("\n" + "=" * 55)
        print("  Session saved! Future runs will skip login.")
        print("  Run: python -m automation.test_gokwik")
        print("=" * 55)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
