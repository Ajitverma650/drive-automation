"""
Page Object Model for REAL GoKwik Dashboard — Rate Capture page.

Framework: Ant Design (ant-form, ant-select, ant-tabs, ant-collapse, ant-upload)
URL: sandbox-mdashboard.dev.gokwik.in/general/rateCapture

DOM structure:
  - Tabs: .ant-tabs-tab with text EMI, UPI, etc. (each appears twice)
  - Table: table with headers Methods, Comission type, Value, Actions
  - Selects: .ant-select (9 total — method, commission type, merchant size, etc.)
  - Buttons: Confirm, Save, Add, + Add more, Save
  - Date pickers: .ant-picker (ant-picker-dropdown for calendar)
"""

from playwright.async_api import Page

PAYMENT_TABS = ['EMI', 'UPI', 'NetBanking', 'Wallet', 'Credit Card', 'Debit Card', 'BNPL', 'COD', 'Others', 'PPCOD']

TAB_DELAY = 600
ADD_DELAY = 500
FILL_DELAY = 300


class GoKwikRateCapturePage:
    def __init__(self, page: Page):
        self.page = page

    async def wait_ready(self):
        """Wait for Rate Capture page to fully load."""
        try:
            await self.page.wait_for_selector("text=Merchant agreement", timeout=15000)
            await self.page.wait_for_timeout(1000)
            print("[GoKwik] Rate Capture page loaded")
            return True
        except Exception:
            print("[GoKwik] Page did not load")
            return False

    async def wait_for_checkout(self):
        """Wait for Checkout section with payment tabs."""
        try:
            await self.page.wait_for_selector(".ant-tabs-tab", timeout=10000)
            await self.page.wait_for_timeout(500)
            print("[GoKwik] Checkout section with tabs visible")
            return True
        except Exception:
            print("[GoKwik] Checkout tabs not found")
            return False

    # ─── Agreement Section ─────────────────────────────

    async def fill_agreement_dates(self, start_date: str, end_date: str):
        """Fill date picker inputs. Format: YYYY-MM-DD."""
        try:
            # Ant Design date pickers: .ant-picker input
            pickers = await self.page.query_selector_all(".ant-picker input")
            if len(pickers) >= 2:
                # Clear and fill start date
                await pickers[0].click()
                await pickers[0].fill("")
                await pickers[0].fill(self._format_date_for_picker(start_date))
                await pickers[0].press("Enter")
                await self.page.wait_for_timeout(300)

                # Clear and fill end date
                await pickers[1].click()
                await pickers[1].fill("")
                await pickers[1].fill(self._format_date_for_picker(end_date))
                await pickers[1].press("Enter")
                await self.page.wait_for_timeout(300)

                print(f"[GoKwik] Dates: {start_date} to {end_date}")
        except Exception as e:
            print(f"[GoKwik] Date fill failed: {e}")

    async def select_merchant_size(self, value: str):
        """Select Merchant Size from Ant Design dropdown."""
        await self._select_ant_dropdown_by_label("Merchant size", value)

    async def select_merchant_type(self, value: str):
        """Select Merchant Type from Ant Design dropdown."""
        await self._select_ant_dropdown_by_label("Merchant type", value)

    async def fill_agreement(self, agreement: dict):
        """Fill all agreement fields."""
        start = agreement.get("start_date", "")
        end = agreement.get("end_date", "")
        size = agreement.get("merchant_size", "Long Tail")
        mtype = agreement.get("merchant_type", "D2C")

        if start and end:
            await self.fill_agreement_dates(start, end)
        if size:
            await self.select_merchant_size(size)
        if mtype:
            await self.select_merchant_type(mtype)

        print(f"[GoKwik] Agreement filled")

    async def click_save_agreement(self):
        """Click first Save button."""
        saves = self.page.locator("button:has-text('Save')")
        if await saves.count() > 0:
            await saves.first.click()
            await self.page.wait_for_timeout(1500)
            print("[GoKwik] Agreement saved")

    # ─── Payment Tabs ──────────────────────────────────

    async def click_tab(self, tab_name: str) -> bool:
        """Click a payment tab (Ant Design tabs)."""
        try:
            # Ant tabs: .ant-tabs-tab has the text
            tabs = await self.page.query_selector_all(".ant-tabs-tab")
            for tab in tabs:
                text = (await tab.inner_text()).strip()
                if text == tab_name:
                    await tab.click()
                    await self.page.wait_for_timeout(TAB_DELAY)
                    return True

            # Fallback: get_by_text
            await self.page.get_by_text(tab_name, exact=True).first.click()
            await self.page.wait_for_timeout(TAB_DELAY)
            return True
        except Exception:
            print(f"[GoKwik] Could not click tab: {tab_name}")
            return False

    # ─── Commission Entry ──────────────────────────────

    async def add_commission(self, method: str, value: str) -> bool:
        """
        Add one commission entry on real GoKwik:
        1. Open Methods ant-select → select method
        2. Value input → enter rate
        3. Click Add button
        """
        try:
            # Step 1: Select method from the Methods dropdown
            # The first ant-select in the active tab area is the Methods dropdown
            method_selected = await self._select_first_ant_dropdown(method)
            if not method_selected:
                print(f"[GoKwik] Could not select method: {method}")
                return False
            await self.page.wait_for_timeout(FILL_DELAY)

            # Step 2: Find the value input and fill it
            # Look for input near the "Value" label or placeholder
            value_input = self.page.locator("input[placeholder*='value' i], input[placeholder*='Value' i]").first
            try:
                if await value_input.is_visible(timeout=2000):
                    await value_input.click()
                    await value_input.fill("")
                    await value_input.fill(str(value))
                    await self.page.wait_for_timeout(FILL_DELAY)
            except Exception:
                # Fallback: try any number input
                num_inputs = await self.page.query_selector_all("input[type='number']")
                if num_inputs:
                    await num_inputs[-1].click()
                    await num_inputs[-1].fill(str(value))

            # Step 3: Click Add
            add_btn = self.page.locator("button:has-text('Add')").first
            if await add_btn.is_visible(timeout=2000):
                await add_btn.click()
                await self.page.wait_for_timeout(ADD_DELAY)
                return True

        except Exception as e:
            print(f"[GoKwik] add_commission failed: {e}")
        return False

    async def fill_all_rates(self, tabs: dict) -> dict:
        """Fill all rates across all tabs."""
        filled = 0
        failed = 0
        details = []

        for tab_name, entries in tabs.items():
            if not entries or tab_name not in PAYMENT_TABS:
                continue

            clicked = await self.click_tab(tab_name)
            if not clicked:
                for e in entries:
                    failed += 1
                    details.append({"tab": tab_name, "method": e["method"], "rate": e["rate"], "status": "tab_not_found"})
                continue

            tab_filled = 0
            for entry in entries:
                method = entry.get("method", "Default")
                rate = entry.get("rate", 0)
                success = await self.add_commission(method, str(rate))
                if success:
                    filled += 1
                    tab_filled += 1
                    details.append({"tab": tab_name, "method": method, "rate": rate, "status": "filled"})
                else:
                    failed += 1
                    details.append({"tab": tab_name, "method": method, "rate": rate, "status": "failed"})

            print(f"[GoKwik] [{tab_name}] {tab_filled}/{len(entries)} filled")

        print(f"[GoKwik] Total: {filled} filled, {failed} failed")
        return {"filled": filled, "failed": failed, "details": details}

    async def click_save_checkout(self):
        """Click last Save button (checkout section)."""
        saves = self.page.locator("button:has-text('Save')")
        count = await saves.count()
        if count > 1:
            await saves.nth(count - 1).click()
        elif count == 1:
            await saves.first.click()
        await self.page.wait_for_timeout(1000)
        print("[GoKwik] Checkout saved")

    async def click_confirm(self) -> bool:
        """Click Confirm button."""
        try:
            confirm = self.page.locator("button:has-text('Confirm')").first
            if await confirm.is_visible(timeout=3000):
                await confirm.click()
                await self.page.wait_for_timeout(1000)
                print("[GoKwik] Confirmed!")
                return True
        except Exception:
            pass
        print("[GoKwik] Confirm not clickable")
        return False

    # ─── Phase 2: Read Back Rates ──────────────────────

    async def read_all_rates(self) -> dict:
        """Read ALL commission values from ALL tabs."""
        actual = {}

        for tab_name in PAYMENT_TABS:
            clicked = await self.click_tab(tab_name)
            if not clicked:
                continue

            entries = []
            # The commission table: first table on the page (not calendar tables)
            tables = await self.page.query_selector_all("table")
            commission_table = None
            for t in tables:
                headers = await t.query_selector_all("th")
                for h in headers:
                    text = (await h.inner_text()).strip()
                    if text == "Methods":
                        commission_table = t
                        break
                if commission_table:
                    break

            if commission_table:
                rows = await commission_table.query_selector_all("tbody tr")
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 3:
                        try:
                            method = (await cells[0].inner_text()).strip()
                            value = (await cells[2].inner_text()).strip()
                            if method and method.lower() not in ('no data', '-', ''):
                                rate = float(value) if value else 0.0
                                entries.append({"method": method, "rate": rate})
                        except (ValueError, IndexError):
                            continue

            if entries:
                actual[tab_name] = entries

        total = sum(len(v) for v in actual.values())
        print(f"[GoKwik] Read back {total} rates from {len(actual)} tabs")
        return actual

    async def take_screenshot(self, name: str = "gokwik") -> str:
        path = f"{name}.png"
        await self.page.screenshot(path=path, full_page=True)
        print(f"[GoKwik] Screenshot: {path}")
        return path

    # ─── Ant Design Helpers ────────────────────────────

    def _format_date_for_picker(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to DD/MM/YYYY for Ant picker."""
        try:
            parts = date_str.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            return date_str

    async def _select_ant_dropdown_by_label(self, label_text: str, value: str):
        """Select value in an Ant Design Select near a label."""
        try:
            # Find the label
            labels = await self.page.query_selector_all("label")
            target_label = None
            for lbl in labels:
                text = (await lbl.inner_text()).strip().lower()
                if label_text.lower() in text:
                    target_label = lbl
                    break

            if not target_label:
                print(f"[GoKwik] Label '{label_text}' not found")
                return

            # Navigate up to form-item, then find .ant-select
            form_item = await target_label.evaluate_handle("el => el.closest('.ant-form-item') || el.parentElement.parentElement")
            select = await form_item.query_selector(".ant-select")

            if select:
                await select.click()
                await self.page.wait_for_timeout(300)
                # Click the option in the dropdown
                option = self.page.locator(f".ant-select-item-option:has-text('{value}')").first
                await option.click(timeout=3000)
                await self.page.wait_for_timeout(200)
                print(f"[GoKwik] Selected {label_text}: {value}")
        except Exception as e:
            print(f"[GoKwik] Could not select '{value}' for '{label_text}': {e}")

    async def _select_first_ant_dropdown(self, value: str) -> bool:
        """
        Select a value from the first visible Ant Select dropdown
        (the Methods dropdown in the current tab).
        """
        try:
            # Find all ant-selects that are NOT disabled and NOT hidden
            selects = await self.page.query_selector_all(".ant-select:not(.ant-select-disabled)")

            # We want the Methods select — it's typically in the commission add row
            # Filter to ones that are visible and in the active tab content
            for sel in selects:
                is_visible = await sel.is_visible()
                if not is_visible:
                    continue

                # Check if this select is near a "Methods" label
                parent = await sel.evaluate_handle("el => el.closest('.ant-form-item') || el.closest('.ant-row') || el.parentElement")
                parent_text = await parent.evaluate("el => el.textContent || ''")

                if "method" in parent_text.lower() or "Methods" in parent_text:
                    await sel.click()
                    await self.page.wait_for_timeout(300)

                    # Click the option
                    option = self.page.locator(f".ant-select-item-option:has-text('{value}')").first
                    try:
                        await option.click(timeout=3000)
                        await self.page.wait_for_timeout(200)
                        return True
                    except Exception:
                        # Close dropdown if option not found
                        await self.page.keyboard.press("Escape")
                        continue

            # Fallback: click first ant-select and try
            first_select = self.page.locator(".ant-select:not(.ant-select-disabled)").first
            await first_select.click()
            await self.page.wait_for_timeout(300)
            option = self.page.locator(f".ant-select-item-option:has-text('{value}')").first
            await option.click(timeout=3000)
            return True

        except Exception as e:
            print(f"[GoKwik] Dropdown select failed for '{value}': {e}")
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            return False
