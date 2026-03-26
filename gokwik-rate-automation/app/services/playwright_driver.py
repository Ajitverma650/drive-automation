"""
Playwright driver — connects to the long-running browser server.

The browser_server.py keeps Chrome open with GoKwik login.
This driver connects via CDP (Chrome DevTools Protocol) to reuse that session.
"""

import os
import logging
from typing import Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

GOKWIK_BASE = os.getenv("GOKWIK_DASHBOARD_URL", "https://sandbox-mdashboard.dev.gokwik.in")
GOKWIK_RATE_CAPTURE = f"{GOKWIK_BASE}/general/rateCapture"
CDP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gokwik_cdp.txt")
CDP_PORT = 9222
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _screenshot_path(name: str) -> str:
    return os.path.join(SCREENSHOT_DIR, f"{name}.png")


def has_session() -> bool:
    """Check if browser server is running by testing CDP port."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', CDP_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


async def _get_page():
    """Connect to the running browser server and get the GoKwik page."""
    p = await async_playwright().start()

    try:
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
    except Exception as e:
        await p.stop()
        raise ConnectionError(
            f"Browser server not running. Start it first:\n"
            f"  python -m automation.browser_server\n"
            f"Error: {e}"
        )

    # Get existing context and page
    contexts = browser.contexts
    if not contexts:
        await p.stop()
        raise ConnectionError("No browser context found. Restart browser_server.")

    pages = contexts[0].pages
    if not pages:
        page = await contexts[0].new_page()
    else:
        page = pages[0]

    return p, browser, page


async def fill_gokwik_dashboard(tabs: dict, agreement: dict, merchant_name: str) -> dict:
    """Fill rates on real GoKwik using the running browser."""
    from automation.gokwik_page import GoKwikRateCapturePage

    p = None
    try:
        p, browser, page = await _get_page()

        # Navigate to Rate Capture
        print(f"[Playwright] Navigating to Rate Capture...")
        await page.goto(GOKWIK_RATE_CAPTURE, timeout=30000)
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            return {
                "success": False, "filled": 0, "failed": 0, "details": [],
                "screenshot": None,
                "message": "Not logged in. Login in the browser server window.",
            }

        gk = GoKwikRateCapturePage(page)
        ready = await gk.wait_ready()
        if not ready:
            ss = _screenshot_path("fill_not_ready")
            await gk.take_screenshot(ss.replace('.png', ''))
            return {
                "success": False, "filled": 0, "failed": 0, "details": [],
                "screenshot": ss,
                "message": "Rate Capture page did not load",
            }

        # Fill agreement
        await gk.fill_agreement(agreement)
        await gk.click_save_agreement()
        await page.wait_for_timeout(1000)

        # Wait for checkout
        has_checkout = await gk.wait_for_checkout()
        if not has_checkout:
            ss = _screenshot_path("fill_no_checkout")
            await gk.take_screenshot(ss.replace('.png', ''))
            return {
                "success": False, "filled": 0, "failed": 0, "details": [],
                "screenshot": ss,
                "message": "Checkout section did not appear after saving",
            }

        # Fill all rates
        result = await gk.fill_all_rates(tabs)

        # Save checkout
        await gk.click_save_checkout()

        ss = _screenshot_path("fill_complete")
        await page.screenshot(path=ss, full_page=True)

        return {
            "success": True,
            "filled": result["filled"],
            "failed": result["failed"],
            "details": result["details"],
            "screenshot": ss,
            "message": f"Filled {result['filled']} rates on GoKwik ({result['failed']} failed)",
        }

    except ConnectionError as e:
        return {
            "success": False, "filled": 0, "failed": 0, "details": [],
            "screenshot": None, "message": str(e),
        }
    except Exception as e:
        logger.error(f"[Playwright] Fill failed: {e}")
        return {
            "success": False, "filled": 0, "failed": 0, "details": [],
            "screenshot": None, "message": f"Error: {str(e)}",
        }
    finally:
        if p:
            await p.stop()


async def verify_gokwik_dashboard(merchant_name: str) -> dict:
    """Read back all rates from real GoKwik (Phase 2)."""
    from automation.gokwik_page import GoKwikRateCapturePage

    p = None
    try:
        p, browser, page = await _get_page()

        # Make sure we're on Rate Capture
        if "rateCapture" not in page.url:
            await page.goto(GOKWIK_RATE_CAPTURE, timeout=30000)
            await page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            return {
                "success": False, "actual_rates": {}, "total_read": 0,
                "screenshot": None, "message": "Not logged in.",
            }

        gk = GoKwikRateCapturePage(page)
        await gk.wait_ready()

        has_checkout = await gk.wait_for_checkout()
        if not has_checkout:
            return {
                "success": False, "actual_rates": {}, "total_read": 0,
                "screenshot": None, "message": "No checkout tabs visible.",
            }

        # Read back all rates
        actual_rates = await gk.read_all_rates()
        total = sum(len(v) for v in actual_rates.values())

        ss = _screenshot_path("verify_readback")
        await page.screenshot(path=ss, full_page=True)

        return {
            "success": True,
            "actual_rates": actual_rates,
            "total_read": total,
            "screenshot": ss,
            "message": f"Read {total} rates from GoKwik",
        }

    except ConnectionError as e:
        return {
            "success": False, "actual_rates": {}, "total_read": 0,
            "screenshot": None, "message": str(e),
        }
    except Exception as e:
        logger.error(f"[Playwright] Verify failed: {e}")
        return {
            "success": False, "actual_rates": {}, "total_read": 0,
            "screenshot": None, "message": f"Error: {str(e)}",
        }
    finally:
        if p:
            await p.stop()


async def confirm_gokwik_dashboard() -> dict:
    """Click Confirm on real GoKwik."""
    from automation.gokwik_page import GoKwikRateCapturePage

    p = None
    try:
        p, browser, page = await _get_page()

        gk = GoKwikRateCapturePage(page)
        confirmed = await gk.click_confirm()

        ss = _screenshot_path("confirmed")
        await page.screenshot(path=ss, full_page=True)

        return {
            "success": confirmed,
            "screenshot": ss,
            "message": "Confirmed!" if confirmed else "Could not click Confirm",
        }

    except ConnectionError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}
    finally:
        if p:
            await p.stop()
