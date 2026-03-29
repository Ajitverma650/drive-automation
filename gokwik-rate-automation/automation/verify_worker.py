"""
GoKwik Phase 2 Verify Worker — runs as a SEPARATE PROCESS.

Uses a DIFFERENT sandbox user (checker) to:
1. Login to GoKwik with sandboxuser2
2. Navigate to Rate Capture
3. Switch to the same merchant
4. Find the uploaded agreement and click edit
5. Read all values from the checkout form
6. Compare with expected PDF data
7. If all match → click Confirm
8. Keep browser open for review

Usage:
    python -m automation.verify_worker --data verify_data.json --output result.json
"""

import argparse
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from automation.login import login_to_gokwik, navigate_to_rate_capture
from automation.gokwik_filler import _switch_merchant
from automation.gokwik_page import GoKwikRateCapturePage

# Use sandboxuser2 for verification (different from filler's user1)
VERIFY_EMAIL = os.getenv("SANDBOX_USER_2_EMAIL", "sandboxuser2@gokwik.co")
VERIFY_PASSWORD = os.getenv("SANDBOX_USER_2_PASSWORD", "Wb7y,=e.9NX2")
VERIFY_OTP = os.getenv("SANDBOX_USER_2_OTP", "123456")


async def run_verify(data_path: str, output_path: str):
    """Login as checker, find agreement, read rates, verify, confirm."""

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    merchant_name = data.get("merchant_name", "Unknown")
    expected_tabs = data.get("tabs", {})
    target_merchant = data.get("target_merchant", merchant_name)
    agreement_name = data.get("agreement_name", "")  # exact PDF filename uploaded in Phase 1
    rate_card_name = data.get("rate_card_name", "")

    result = {
        "success": False,
        "matched": 0,
        "mismatched": 0,
        "total": 0,
        "discrepancies": [],
        "actual_rates": {},
        "steps": [],
        "confirmed": False,
        "message": "",
    }

    print(f"[Verify Worker] Starting verification for: {merchant_name}")
    print(f"[Verify Worker] Target merchant: {target_merchant}")
    print(f"[Verify Worker] Expected tabs: {list(expected_tabs.keys())}")
    print(f"[Verify Worker] Checker user: {VERIFY_EMAIL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        try:
            # ─── Step 1: Login as checker (user2) ─────
            print(f"[Verify Worker] Logging in as checker: {VERIFY_EMAIL}...")
            success = await login_to_gokwik(page,
                                             email=VERIFY_EMAIL,
                                             password=VERIFY_PASSWORD,
                                             otp=VERIFY_OTP)
            if not success:
                result["message"] = f"Checker login failed. URL: {page.url}"
                print(f"[Verify Worker] Login FAILED")
                await page.wait_for_timeout(10000)
                return result

            result["steps"].append({"step": "login", "status": "done",
                                    "text": f"Checker logged in as {VERIFY_EMAIL}"})
            print("[Verify Worker] Login successful!")

            # ─── Step 2: Navigate to Rate Capture ─────
            await navigate_to_rate_capture(page)
            result["steps"].append({"step": "navigate", "status": "done",
                                    "text": "On Rate Capture page"})

            # ─── Step 3: Switch to target merchant ────
            await _switch_merchant(page, target_merchant)
            await page.wait_for_timeout(2000)
            result["steps"].append({"step": "switch_merchant", "status": "done",
                                    "text": f"Switched to {target_merchant}"})

            # ─── Step 4: Find and click the agreement ─
            print(f"[Verify Worker] Looking for agreement: '{rate_card_name or agreement_name}'...")
            found = await _find_agreement_by_name(page, rate_card_name or agreement_name)
            if not found:
                result["message"] = "No agreement found to verify"
                result["steps"].append({"step": "find_agreement", "status": "failed",
                                        "text": "No agreement found"})
                await page.wait_for_timeout(15000)
                return result

            result["steps"].append({"step": "find_agreement", "status": "done",
                                    "text": "Opened latest agreement"})
            print("[Verify Worker] Agreement opened")

            # ─── Step 5: Expand Checkout and read rates ─
            try:
                checkout_btn = page.get_by_role("button", name="right Checkout")
                if await checkout_btn.is_visible(timeout=3000):
                    expanded = await checkout_btn.get_attribute("aria-expanded")
                    if expanded != "true":
                        await checkout_btn.click()
                        await page.wait_for_timeout(1000)
            except Exception:
                pass

            # Wait for tabs
            try:
                await page.wait_for_selector('[role="tab"]', timeout=5000)
            except Exception:
                result["message"] = "Checkout tabs not found"
                await page.wait_for_timeout(15000)
                return result

            result["steps"].append({"step": "expand_checkout", "status": "done",
                                    "text": "Checkout section expanded"})

            # Read all rates from each tab
            gk = GoKwikRateCapturePage(page)
            actual_rates = await gk.read_all_rates()
            total_read = sum(len(v) for v in actual_rates.values())
            result["actual_rates"] = actual_rates
            result["steps"].append({"step": "read_rates", "status": "done",
                                    "text": f"Read {total_read} rates from {len(actual_rates)} tabs"})
            print(f"[Verify Worker] Read {total_read} rates")

            # ─── Step 6: Compare with expected ────────
            matched = 0
            mismatched = 0
            total = 0
            discrepancies = []

            for tab_name, expected_entries in expected_tabs.items():
                actual_entries = actual_rates.get(tab_name, [])

                for exp in expected_entries:
                    total += 1
                    exp_method = exp.get("method", "Default")
                    exp_rate = float(exp.get("rate", 0))

                    # Find matching entry in actual
                    found_match = False
                    for act in actual_entries:
                        act_rate = float(act.get("rate", 0))
                        act_method = act.get("method", "Default")

                        # Match by method name or by rate value (since method may be Default)
                        if act_method == exp_method or abs(act_rate - exp_rate) < 0.01:
                            if abs(act_rate - exp_rate) < 0.01:
                                matched += 1
                            else:
                                mismatched += 1
                                discrepancies.append({
                                    "tab": tab_name,
                                    "method": exp_method,
                                    "expected": exp_rate,
                                    "actual": act_rate,
                                })
                            found_match = True
                            break

                    if not found_match:
                        mismatched += 1
                        discrepancies.append({
                            "tab": tab_name,
                            "method": exp_method,
                            "expected": exp_rate,
                            "actual": "NOT FOUND",
                        })

            result["matched"] = matched
            result["mismatched"] = mismatched
            result["total"] = total
            result["discrepancies"] = discrepancies

            print(f"[Verify Worker] Comparison: {matched}/{total} matched, {mismatched} mismatched")

            if mismatched == 0 and matched > 0:
                result["steps"].append({"step": "verify", "status": "done",
                                        "text": f"ALL {matched} RATES VERIFIED!"})

                # ─── Step 7: Click Confirm ────────────
                print("[Verify Worker] All rates match! Clicking Confirm...")
                try:
                    confirm_btn = page.get_by_role("button", name="Confirm")
                    if await confirm_btn.is_visible(timeout=3000):
                        await confirm_btn.click()
                        await page.wait_for_timeout(2000)
                        result["confirmed"] = True
                        result["steps"].append({"step": "confirm", "status": "done",
                                                "text": "CONFIRMED by checker!"})
                        print("[Verify Worker] CONFIRMED!")
                except Exception as e:
                    result["steps"].append({"step": "confirm", "status": "warning",
                                            "text": f"Confirm failed: {e}"})
            else:
                result["steps"].append({"step": "verify", "status": "failed",
                                        "text": f"{mismatched} DISCREPANCIES found"})
                for d in discrepancies:
                    print(f"[Verify Worker] MISMATCH [{d['tab']}] {d['method']}: expected {d['expected']}, got {d['actual']}")

            result["success"] = True
            result["message"] = f"Verified: {matched}/{total} matched" + (", CONFIRMED" if result["confirmed"] else "")

            # Screenshot
            os.makedirs("screenshots", exist_ok=True)
            await page.screenshot(path="screenshots/verify_complete.png", full_page=True)

            # Keep browser open for review
            print("[Verify Worker] Keeping browser open 35s for review...")
            await page.wait_for_timeout(35000)

        except Exception as e:
            import traceback
            traceback.print_exc()
            result["message"] = f"Error: {str(e)}"
            print(f"[Verify Worker] ERROR: {e}")
            await page.wait_for_timeout(15000)

        finally:
            await browser.close()
            print("[Verify Worker] Browser closed")

    return result


async def _find_agreement_by_name(page, pdf_name: str) -> bool:
    """Find the specific agreement we uploaded in Phase 1 by matching PDF filename."""
    try:
        rows = page.locator("table tbody tr")
        count = await rows.count()

        if count == 0:
            print("[Verify Worker] No agreements in table")
            return False

        # Search through all rows to find the one matching our uploaded PDF
        target_row = None
        for i in range(count):
            row = rows.nth(i)
            row_text = await row.inner_text()

            if "no data" in row_text.lower():
                continue

            # Match by PDF filename (partial match — Drive filenames get prefixed with _drive_)
            # Also match if the row contains "Draft" (our upload is always Draft)
            if pdf_name:
                # Clean up name for matching: remove _drive_ prefix, spaces/underscores
                clean_pdf = pdf_name.replace("_drive_", "").replace("_", " ").lower()
                clean_row = row_text.replace("_", " ").lower()

                if any(part in clean_row for part in clean_pdf.split() if len(part) > 3):
                    target_row = row
                    print(f"[Verify Worker] Matched row {i}: {row_text[:80]}...")
                    break
            else:
                # No name provided — use first Draft row
                if "draft" in row_text.lower():
                    target_row = row
                    print(f"[Verify Worker] Using first Draft row: {row_text[:80]}...")
                    break

        if not target_row:
            # Fallback: just use the first row
            first_row = rows.first
            first_text = await first_row.inner_text()
            if "no data" not in first_text.lower():
                target_row = first_row
                print(f"[Verify Worker] Fallback to first row: {first_text[:80]}...")

        if not target_row:
            print("[Verify Worker] No matching agreement found")
            return False

        # Click the edit icon in the matched row
        return await _click_edit_icon(page, target_row)

    except Exception as e:
        print(f"[Verify Worker] Find agreement failed: {e}")
        return False


async def _click_edit_icon(page, row) -> bool:
    """Click the edit/form icon in an agreement row."""
    # Try labeled icons first
    for label in ["edit", "form", "file-add"]:
        try:
            icon = row.get_by_label(label)
            if await icon.is_visible(timeout=1000):
                await icon.click()
                print(f"[Verify Worker] Clicked '{label}' icon")
                await page.wait_for_timeout(2000)
                return True
        except Exception:
            continue

    # Fallback: click icons in the Action cell (second-to-last or last td)
    try:
        cells = row.locator("td")
        cell_count = await cells.count()

        # Action column is typically second-to-last
        for cell_idx in [cell_count - 2, cell_count - 1]:
            if cell_idx < 0:
                continue
            action_cell = cells.nth(cell_idx)
            icons = action_cell.locator("img, span[role='img']")
            icon_count = await icons.count()

            if icon_count >= 2:
                # Second icon is usually edit
                await icons.nth(1).click()
                print(f"[Verify Worker] Clicked icon[1] in cell[{cell_idx}]")
                await page.wait_for_timeout(2000)
                return True
            elif icon_count == 1:
                await icons.nth(0).click()
                print(f"[Verify Worker] Clicked icon[0] in cell[{cell_idx}]")
                await page.wait_for_timeout(2000)
                return True
    except Exception as e:
        print(f"[Verify Worker] Fallback click failed: {e}")

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to verify data JSON")
    parser.add_argument("--output", required=True, help="Path to write result JSON")
    args = parser.parse_args()

    result = asyncio.run(run_verify(args.data, args.output))

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"[Verify Worker] Result written to {args.output}")
    sys.exit(0 if result.get("confirmed") else 1)


if __name__ == "__main__":
    main()
