"""
Page Object Model for the Rate Capture page.

Two strategies:
  Strategy 1 (inject): Inject extracted data directly into React state via JS.
                       Fast, reliable, works with any React app.
  Strategy 2 (fill):   Click through DOM elements one by one.
                       Slower, fragile, but mirrors real user behavior.

Phase 2 (read back) always uses Strategy 2 — reads actual DOM values.
"""

import asyncio
import json
from playwright.async_api import Page

from automation.config import (
    TAB_SWITCH_DELAY, ADD_ROW_DELAY, BETWEEN_TABS_DELAY,
    PAYMENT_TABS,
)


class RateCapturePage:
    def __init__(self, page: Page):
        self.page = page

    async def wait_ready(self):
        """Wait for the Rate Capture page to be fully loaded."""
        await self.page.wait_for_selector("text=Agreement Details", timeout=10000)
        print("[Playwright] Rate Capture page loaded")

    # ─── Strategy 1: Inject via AutomationPanel ───────

    async def inject_via_automation(self, extraction_data: dict):
        """
        Trigger the automation by:
        1. Click "Run Automation" to open the panel
        2. Upload PDFs programmatically (set file inputs)
        3. Let the frontend auto-fill handle everything

        But since we already have the extracted data from the API,
        we can inject it directly by simulating what handlePhase1Complete does.
        """
        data_json = json.dumps(extraction_data)

        # Inject the extraction data into the React component's state
        # by dispatching a custom event that RateCapture listens to
        result = await self.page.evaluate(f"""() => {{
            // Find the React fiber root and trigger phase1 complete
            const data = {data_json};

            // Strategy: dispatch custom event with the data
            window.__PLAYWRIGHT_EXTRACTION_DATA__ = data;
            window.dispatchEvent(new CustomEvent('playwright-phase1', {{ detail: data }}));

            return {{ injected: true, tabs: Object.keys(data.tabs || {{}}) }};
        }}""")

        print(f"[Playwright] Data injected: {result}")
        return result

    # ─── Strategy 2: Fill via DOM (for real GoKwik) ───

    async def wait_for_checkout(self):
        """Wait for Checkout section and payment tabs to appear."""
        try:
            await self.page.wait_for_selector("text=Checkout", timeout=10000)
            await self.page.wait_for_timeout(500)
            await self.page.wait_for_selector("text=EMI", timeout=5000)
            print("[Playwright] Checkout section visible")
        except Exception:
            print("[Playwright] Warning: Checkout section slow to appear")

    async def click_payment_tab(self, tab_name: str):
        """Click a payment tab."""
        selectors = [
            f".rc-tab-btn:has-text('{tab_name}')",
            f"button:has-text('{tab_name}')",
        ]
        for sel in selectors:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click()
                    await self.page.wait_for_timeout(TAB_SWITCH_DELAY)
                    return
            except Exception:
                continue
        print(f"[Playwright] Warning: could not click tab '{tab_name}'")

    # ─── Phase 2: Read Back Values (THE KEY PART) ─────

    async def read_all_rates(self) -> dict:
        """
        Read ALL commission values from ALL tabs on the dashboard.
        This is the REAL Phase 2 — reads what's ACTUALLY on screen.

        Returns: {
            "EMI": [{"method": "Credit Card", "rate": 0}, ...],
            "UPI": [{"method": "Default", "rate": 2.5}, ...],
        }
        """
        actual_rates = {}

        for tab_name in PAYMENT_TABS:
            try:
                await self.click_payment_tab(tab_name)
            except Exception:
                continue

            entries = []
            rows = await self.page.query_selector_all("table tbody tr")

            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) >= 3:
                    try:
                        method_text = (await cells[0].inner_text()).strip()
                        value_text = (await cells[2].inner_text()).strip()

                        if not method_text or method_text.lower() in ('methods', 'no data'):
                            continue

                        rate = float(value_text) if value_text else 0.0
                        entries.append({
                            "method": method_text,
                            "rate": rate,
                        })
                    except (ValueError, IndexError):
                        continue

            if entries:
                actual_rates[tab_name] = entries
            await self.page.wait_for_timeout(200)

        total = sum(len(v) for v in actual_rates.values())
        print(f"[Playwright] Read back {total} rates from {len(actual_rates)} tabs")
        return actual_rates

    async def read_agreement_dates(self) -> dict:
        """Read the agreement dates from the form."""
        dates = {}
        try:
            date_inputs = await self.page.query_selector_all('input[type="date"]')
            if len(date_inputs) >= 2:
                dates["start_date"] = await date_inputs[0].input_value()
                dates["end_date"] = await date_inputs[1].input_value()
        except Exception:
            pass
        return dates

    async def click_confirm(self):
        """Click the Confirm button."""
        try:
            confirm = self.page.locator("button:has-text('Confirm')").first
            await confirm.click()
            await self.page.wait_for_timeout(500)
            print("[Playwright] Confirmed!")
            return True
        except Exception:
            print("[Playwright] Confirm button not found")
            return False

    async def take_screenshot(self, name: str = "screenshot"):
        """Take a full-page screenshot."""
        path = f"{name}.png"
        await self.page.screenshot(path=path, full_page=True)
        print(f"[Playwright] Screenshot saved: {path}")
        return path
