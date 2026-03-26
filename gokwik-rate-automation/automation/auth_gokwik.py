"""
GoKwik Dashboard — Save Login Session.

Uses a dedicated Playwright browser profile that persists login.
First run: login manually. After that: stays logged in permanently.

Usage:
    python -m automation.auth_gokwik
"""

import asyncio
import os

from playwright.async_api import async_playwright

GOKWIK_URL = "https://sandbox-mdashboard.dev.gokwik.in"
BROWSER_PROFILE = os.path.join(os.path.dirname(__file__), "..", "gokwik_browser_profile")


async def main():
    print("=" * 55)
    print("  GoKwik Dashboard — Login & Save")
    print("=" * 55)
    print(f"  Profile: {os.path.abspath(BROWSER_PROFILE)}")
    print("=" * 55)

    async with async_playwright() as p:
        # Use persistent context — this saves ALL browser data
        # (cookies, localStorage, sessionStorage, IndexedDB)
        # between runs. Like a real browser profile.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE,
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(GOKWIK_URL)
        await page.wait_for_timeout(3000)

        url = page.url
        print(f"\n[Auth] Current URL: {url}")

        if "login" not in url.lower():
            print("[Auth] Already logged in from previous session!")
            print("[Auth] Navigating to Rate Capture...")
            await page.goto(f"{GOKWIK_URL}/general/rateCapture")
            await page.wait_for_timeout(2000)
        else:
            print("\n" + "-" * 55)
            print("  Login to GoKwik in the browser window.")
            print("  Navigate to Rate Capture page.")
            print("  Then press ENTER here.")
            print("-" * 55)
            input("\n  Press ENTER when done...")

        print(f"\n[Auth] Final URL: {page.url}")
        await context.close()

    print("\n" + "=" * 55)
    print("  Login saved in browser profile!")
    print("  Next runs will be auto-logged-in.")
    print("  Test: python -m automation.test_gokwik")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
