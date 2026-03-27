"""
GoKwik Dashboard Rate Filler — proven automation steps.

This module fills rates on the real GoKwik dashboard using Playwright.
Every step here was manually tested and verified via MCP Playwright tools.

Requires: browser_server.py running (Chrome with GoKwik login)

Flow:
  1. Open Rate Capture page
  2. Find merchant OR click "+ Add agreement"
  3. Upload rate card PDF
  4. Fill agreement fields (dates, size, type, products)
  5. Save → Checkout appears
  6. Expand Checkout
  7. Fill rates across all tabs
  8. Save checkout
  9. Leave as Draft (checker confirms later)
"""

import asyncio
import os
import logging
from typing import Optional

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

GOKWIK_URL = os.getenv("GOKWIK_DASHBOARD_URL", "https://sandbox-mdashboard.dev.gokwik.in")
RATE_CAPTURE_URL = f"{GOKWIK_URL}/general/rateCapture"
CDP_PORT = 9222

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _ss(name: str) -> str:
    return os.path.join(SCREENSHOT_DIR, f"{name}.png")


async def _connect() -> tuple:
    """Connect to the running browser server via CDP."""
    p = await async_playwright().start()
    try:
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
    except Exception as e:
        await p.stop()
        raise ConnectionError(
            f"Browser server not running. Start: python -m automation.browser_server\nError: {e}"
        )

    contexts = browser.contexts
    if not contexts:
        await p.stop()
        raise ConnectionError("No browser context. Restart browser_server.")

    page = contexts[0].pages[0] if contexts[0].pages else await contexts[0].new_page()
    return p, browser, page


async def fill_gokwik(
    merchant_name: str,
    rate_card_path: str,
    agreement: dict,
    tabs: dict,
    is_new: bool = True,
) -> dict:
    """
    Fill rates on real GoKwik dashboard.

    Args:
        merchant_name: Merchant name to find in list (or create new)
        rate_card_path: Local path to rate card PDF (downloaded from Drive)
        agreement: { start_date, end_date, merchant_size, merchant_type, purchased_products }
        tabs: { "EMI": [{"method": "Credit Card", "rate": 0}], "UPI": [...], ... }
        is_new: True = click "+ Add agreement", False = find and edit existing

    Returns:
        { success, filled, failed, steps, screenshot, message }
    """
    steps = []
    p = None

    try:
        p, browser, page = await _connect()
        steps.append({"step": "connect", "status": "done", "text": "Connected to GoKwik browser"})

        # Navigate to Rate Capture
        await page.goto(RATE_CAPTURE_URL, timeout=30000)
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            return _fail("Not logged in. Login in browser_server window.", steps)

        # Wait for merchant list
        try:
            await page.wait_for_selector("text=Agreement / Addendum", timeout=10000)
        except Exception:
            return _fail("Rate Capture page did not load.", steps)

        steps.append({"step": "navigate", "status": "done", "text": "Rate Capture page loaded"})

        # ─── Step 1: Open merchant form ────────────────
        if is_new:
            # Click "+ Add agreement"
            await page.get_by_role("button", name="+ Add agreement").click()
            await page.wait_for_timeout(1000)
            steps.append({"step": "add_agreement", "status": "done", "text": "Clicked + Add agreement"})
        else:
            # Find merchant in list and click edit icon
            found = await _find_and_click_merchant(page, merchant_name)
            if not found:
                return _fail(f"Merchant '{merchant_name}' not found in list.", steps)
            steps.append({"step": "find_merchant", "status": "done", "text": f"Found merchant: {merchant_name}"})

        # Wait for form to load
        try:
            await page.wait_for_selector("text=Merchant agreement", timeout=5000)
        except Exception:
            return _fail("Agreement form did not open.", steps)

        # ─── Step 2: Upload rate card PDF ──────────────
        if rate_card_path and os.path.exists(rate_card_path):
            uploaded = await _upload_pdf(page, rate_card_path)
            if uploaded:
                steps.append({"step": "upload", "status": "done",
                              "text": f"Uploaded: {os.path.basename(rate_card_path)}"})
            else:
                steps.append({"step": "upload", "status": "warning", "text": "PDF upload failed"})

        # ─── Step 3: Fill agreement fields ─────────────
        filled_fields = await _fill_agreement_fields(page, agreement)
        steps.append({"step": "fill_agreement", "status": "done",
                      "text": f"Filled: {', '.join(filled_fields)}"})

        # ─── Step 4: Save agreement ────────────────────
        await page.get_by_role("button", name="Save").click()
        await page.wait_for_timeout(2000)

        # Check for errors
        error_toast = await page.query_selector("text=Not Allowed")
        if error_toast:
            error_text = await error_toast.inner_text()
            return _fail(f"Save failed: {error_text}", steps)

        steps.append({"step": "save_agreement", "status": "done", "text": "Agreement saved"})

        # ─── Step 5: Expand Checkout ───────────────────
        try:
            checkout_btn = page.get_by_role("button", name="right Checkout")
            expanded = await checkout_btn.get_attribute("aria-expanded") if await checkout_btn.is_visible(timeout=3000) else None
            if expanded == "false" or expanded is None:
                await checkout_btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # Wait for tabs
        try:
            await page.wait_for_selector('[role="tab"]', timeout=5000)
        except Exception:
            return _fail("Checkout tabs did not appear after saving.", steps)

        steps.append({"step": "expand_checkout", "status": "done", "text": "Checkout expanded with payment tabs"})

        # ─── Step 6: Fill all rates ────────────────────
        filled = 0
        failed = 0

        for tab_name, entries in tabs.items():
            if not entries:
                continue

            # Click the tab
            try:
                tab = page.get_by_role("tab", name=tab_name)
                await tab.click()
                await page.wait_for_timeout(600)
            except Exception:
                failed += len(entries)
                steps.append({"step": f"tab_{tab_name}", "status": "failed", "text": f"[{tab_name}] Tab not found"})
                continue

            tab_filled = 0
            for entry in entries:
                method = entry.get("method", "Default")
                rate = entry.get("rate", 0)

                success = await _add_commission_entry(page, tab_name, method, str(rate))
                if success:
                    filled += 1
                    tab_filled += 1
                else:
                    failed += 1

            steps.append({"step": f"tab_{tab_name}", "status": "done",
                          "text": f"[{tab_name}] {tab_filled}/{len(entries)} rates filled"})

        # ─── Step 7: Save checkout ─────────────────────
        # Click the last Save button (checkout save)
        save_buttons = page.get_by_role("button", name="Save")
        count = await save_buttons.count()
        if count > 1:
            await save_buttons.nth(count - 1).click()
        elif count == 1:
            await save_buttons.first.click()
        await page.wait_for_timeout(1500)

        steps.append({"step": "save_checkout", "status": "done", "text": "Checkout saved"})

        # Take screenshot
        ss = _ss("gokwik_fill_complete")
        await page.screenshot(path=ss, full_page=True)

        steps.append({"step": "done", "status": "done",
                      "text": f"Complete: {filled} filled, {failed} failed. Left as Draft for checker."})

        return {
            "success": True,
            "filled": filled,
            "failed": failed,
            "steps": steps,
            "screenshot": ss,
            "message": f"Filled {filled} rates on GoKwik ({failed} failed). Status: Draft.",
        }

    except ConnectionError as e:
        return _fail(str(e), steps)
    except Exception as e:
        logger.error(f"[GoKwik Filler] Error: {e}")
        return _fail(f"Error: {str(e)}", steps)
    finally:
        if p:
            await p.stop()


# ─── Helper Functions ──────────────────────────────────


def _fail(message: str, steps: list) -> dict:
    steps.append({"step": "error", "status": "failed", "text": message})
    return {
        "success": False,
        "filled": 0,
        "failed": 0,
        "steps": steps,
        "screenshot": None,
        "message": message,
    }


async def _find_and_click_merchant(page: Page, merchant_name: str) -> bool:
    """Find a merchant in the list and click its edit icon."""
    # Search in the table rows
    rows = await page.query_selector_all("table tbody tr")
    for row in rows:
        text = await row.inner_text()
        if merchant_name.lower() in text.lower():
            # Click the edit (form) icon in this row
            edit_icon = await row.query_selector('[aria-label="form"], img[alt="form"]')
            if edit_icon:
                await edit_icon.click()
                await page.wait_for_timeout(1500)
                return True
            # Fallback: try any clickable icon in the action column
            icons = await row.query_selector_all("img[cursor=pointer], span[role=img]")
            for icon in icons:
                label = await icon.get_attribute("aria-label") or ""
                if "form" in label or "edit" in label:
                    await icon.click()
                    await page.wait_for_timeout(1500)
                    return True

    # Try using Playwright's built-in locator
    try:
        row = page.get_by_role("row", name=merchant_name).first
        form_icon = row.get_by_label("form")
        await form_icon.click()
        await page.wait_for_timeout(1500)
        return True
    except Exception:
        pass

    return False


async def _upload_pdf(page: Page, file_path: str) -> bool:
    """Upload a PDF file to the Merchant agreement field."""
    try:
        # Check if there's already a file uploaded (has close-circle button)
        existing = await page.query_selector('[aria-label="close-circle"]')
        if existing:
            return True  # File already uploaded, skip

        # Click upload button and handle file chooser
        upload_btn = page.get_by_role("button", name="Click here to upload")
        if await upload_btn.is_visible(timeout=2000):
            async with page.expect_file_chooser() as fc_info:
                await upload_btn.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(file_path)
            await page.wait_for_timeout(1000)
            return True
    except Exception as e:
        logger.error(f"[GoKwik Filler] Upload failed: {e}")
    return False


async def _fill_agreement_fields(page: Page, agreement: dict) -> list:
    """Fill agreement form fields. Returns list of filled field names."""
    filled = []

    start_date = agreement.get("start_date", "")
    end_date = agreement.get("end_date", "")
    merchant_size = agreement.get("merchant_size", "")
    merchant_type = agreement.get("merchant_type", "")
    products = agreement.get("purchased_products", [])

    # Fill dates (DD/MM/YYYY format for Ant date picker)
    if start_date:
        date_str = _to_ddmmyyyy(start_date)
        try:
            date_input = page.get_by_role("textbox", name="Select date").first
            await date_input.click()
            await date_input.fill(date_str)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(300)
            filled.append(f"start={date_str}")
        except Exception:
            pass

    if end_date:
        date_str = _to_ddmmyyyy(end_date)
        try:
            date_input = page.get_by_role("textbox", name="Select date").nth(1)
            await date_input.click()
            await date_input.fill(date_str)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(300)
            filled.append(f"end={date_str}")
        except Exception:
            pass

    # Select Merchant Size
    if merchant_size:
        selected = await _select_ant_dropdown(page, merchant_size)
        if selected:
            filled.append(f"size={merchant_size}")

    # Select Merchant Type
    if merchant_type:
        selected = await _select_ant_dropdown(page, merchant_type)
        if selected:
            filled.append(f"type={merchant_type}")

    # Select Purchased Products
    if products:
        for product in products:
            selected = await _select_ant_dropdown(page, product)
            if selected:
                filled.append(f"product={product}")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(200)

    return filled


async def _select_ant_dropdown(page: Page, value: str) -> bool:
    """Select a value from an Ant Design dropdown that shows 'Select value'."""
    try:
        # Find unselected dropdowns showing "Select value"
        triggers = await page.query_selector_all(".ant-select:not(.ant-select-disabled)")
        for trigger in triggers:
            text = await trigger.inner_text()
            if "Select value" in text or "select value" in text.lower():
                await trigger.click()
                await page.wait_for_timeout(300)

                # Click the option
                option = page.get_by_title(value, exact=True).first
                try:
                    await option.click(timeout=2000)
                    await page.wait_for_timeout(200)
                    return True
                except Exception:
                    await page.keyboard.press("Escape")
                    continue
    except Exception as e:
        logger.error(f"[GoKwik Filler] Dropdown select '{value}' failed: {e}")
    return False


async def _add_commission_entry(page: Page, tab_name: str, method: str, value: str) -> bool:
    """
    Add one commission entry in the current tab.
    Proven steps:
      1. Click Methods dropdown → select method
      2. Remove "Default" chip if present
      3. Fill value input
      4. Click Add
    """
    try:
        # Step 1: Open Methods dropdown (first ant-select in the active tab panel)
        tab_panel = page.get_by_role("tabpanel", name=tab_name) if tab_name in ["EMI", "UPI", "NetBanking", "Wallet", "BNPL", "COD"] else page.get_by_role("tabpanel").first

        # If method is "Default", just fill value and Add (Default is pre-selected)
        if method == "Default":
            # Fill value
            value_input = tab_panel.get_by_placeholder("Enter value") if tab_name in ["EMI", "UPI", "NetBanking", "Wallet", "BNPL", "COD"] else page.get_by_role("spinbutton", name="Enter value").first
            try:
                await value_input.fill(value)
            except Exception:
                # Fallback
                spinbuttons = await page.query_selector_all("input.ant-input-number-input")
                for sb in spinbuttons:
                    if await sb.is_visible():
                        await sb.fill(value)
                        break

            # Click Add
            await page.get_by_role("button", name="Add", exact=True).click()
            await page.wait_for_timeout(400)
            return True

        # Step 1: Click Methods dropdown to open it
        # The Methods/Network/Bank/Provider dropdown is the first ant-select in the tab's form row
        selects = await page.query_selector_all(".ant-select:not(.ant-select-disabled)")
        methods_select = None
        for sel in selects:
            if await sel.is_visible():
                parent_text = await sel.evaluate("el => el.closest('.ant-row')?.textContent || ''")
                if any(kw in parent_text.lower() for kw in ["method", "network", "bank", "provider"]):
                    methods_select = sel
                    break

        if not methods_select:
            # Fallback: click the first visible select in the tab area
            methods_select = selects[0] if selects else None

        if methods_select:
            await methods_select.click()
            await page.wait_for_timeout(300)

            # Step 2: Select the method from dropdown
            try:
                option = page.get_by_title(method, exact=True).first
                await option.click(timeout=3000)
                await page.wait_for_timeout(200)
            except Exception:
                await page.keyboard.press("Escape")
                return False

            # Close dropdown
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(200)

            # Step 3: Remove "Default" chip if it was pre-selected
            # Find close icons within the methods select area
            close_icons = await page.query_selector_all('[aria-label="close"]')
            for icon in close_icons:
                if await icon.is_visible():
                    # Check if this is the Default chip's close icon
                    parent = await icon.evaluate("el => el.closest('.ant-select-selection-item')?.textContent || ''")
                    if "Default" in parent:
                        await icon.click()
                        await page.wait_for_timeout(200)
                        break

        # Step 4: Fill value
        try:
            if tab_name in ["EMI", "UPI", "NetBanking", "Wallet", "BNPL", "COD"]:
                value_input = page.get_by_role("tabpanel", name=tab_name).get_by_placeholder("Enter value")
            else:
                value_input = page.get_by_role("spinbutton", name="Enter value").first
            await value_input.fill(value)
        except Exception:
            spinbuttons = await page.query_selector_all("input.ant-input-number-input")
            for sb in spinbuttons:
                if await sb.is_visible():
                    await sb.fill(value)
                    break

        await page.wait_for_timeout(200)

        # Step 5: Click Add
        await page.get_by_role("button", name="Add", exact=True).click()
        await page.wait_for_timeout(400)
        return True

    except Exception as e:
        logger.error(f"[GoKwik Filler] Add commission failed [{tab_name}] {method}={value}: {e}")
        return False


def _to_ddmmyyyy(date_str: str) -> str:
    """Convert YYYY-MM-DD to DD/MM/YYYY."""
    try:
        parts = date_str.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return date_str
