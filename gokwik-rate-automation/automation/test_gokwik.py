"""
Simple test: Open real GoKwik dashboard and read Rate Capture page.

Usage:
    python -m automation.test_gokwik
"""

import asyncio
import os

from playwright.async_api import async_playwright

GOKWIK_BASE = "https://sandbox-mdashboard.dev.gokwik.in"
SESSION_FILE = os.path.join(os.path.dirname(__file__), "..", "gokwik_session.json")

PAYMENT_TABS = ['EMI', 'UPI', 'NetBanking', 'Wallet', 'Credit Card', 'Debit Card', 'BNPL', 'COD', 'Others', 'PPCOD']


async def main():
    if not os.path.exists(SESSION_FILE):
        print("No saved session found. Run first:")
        print("  python -m automation.auth_gokwik")
        return

    print("=" * 55)
    print("  GoKwik Dashboard - Read Test")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=SESSION_FILE,
            viewport={"width": 1400, "height": 900},
        )
        page = await context.new_page()

        # Navigate to base URL first
        print("[Test] Opening GoKwik dashboard...")
        await page.goto(GOKWIK_BASE, timeout=30000)
        await page.wait_for_timeout(3000)

        # Check if we need to login (session expired)
        current_url = page.url
        print(f"[Test] Current URL: {current_url}")

        if "login" in current_url.lower() or "auth" in current_url.lower():
            print("\n[Test] Session expired! Re-run:")
            print("  python -m automation.auth_gokwik")
            await browser.close()
            return

        # Take screenshot of landing page
        await page.screenshot(path="gokwik_1_landing.png", full_page=True)
        print("[Test] Screenshot: gokwik_1_landing.png")

        # Find and click Rate Capture / Rate Checkout in sidebar
        print("[Test] Looking for Rate Capture in sidebar...")
        sidebar_items = await page.query_selector_all("a, button, div[role='button'], span")
        found_nav = False
        for item in sidebar_items:
            text = (await item.inner_text()).strip().lower()
            if any(kw in text for kw in ['rate capture', 'rate checkout', 'ratecapture']):
                print(f"[Test] Found: '{text}' - clicking...")
                await item.click()
                await page.wait_for_timeout(3000)
                found_nav = True
                break

        if not found_nav:
            # Try clicking by text
            for nav_text in ['Rate Checkout', 'Rate Capture', 'Checkout Setup']:
                try:
                    await page.click(f"text={nav_text}", timeout=2000)
                    await page.wait_for_timeout(3000)
                    found_nav = True
                    print(f"[Test] Clicked: {nav_text}")
                    break
                except Exception:
                    continue

        if not found_nav:
            print("[Test] Could not find Rate Capture link. Printing all sidebar items...")
            all_text = await page.evaluate("""() => {
                return [...document.querySelectorAll('a, nav span, nav div, [class*=sidebar] span, [class*=sidebar] a, [class*=menu] span')]
                    .map(el => el.textContent.trim())
                    .filter(Boolean)
                    .filter((v, i, a) => a.indexOf(v) === i)
                    .slice(0, 30)
            }""")
            print(f"  Sidebar items: {all_text}")

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
    asyncio.run(main())
