"""
Playwright driver — fills/verifies/confirms on real GoKwik dashboard.

Launches the fill_worker.py as a SEPARATE PROCESS so it can open a visible
Chrome browser window. The FastAPI server itself cannot launch GUI windows,
so the worker runs independently.
"""

import os
import sys
import json
import asyncio
import tempfile
import logging

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Path to the worker script — must run from gokwik-rate-automation root
WORKER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKER_MODULE = "automation.fill_worker"


def _screenshot_path(name: str) -> str:
    return os.path.join(SCREENSHOT_DIR, f"{name}.png")


def has_session() -> bool:
    """Always return False — we use subprocess mode, not persistent browser."""
    return False


async def fill_gokwik_dashboard(tabs: dict, agreement: dict, merchant_name: str, rate_card_path: str = "", agreement_pdf_path: str = "") -> dict:
    """
    Fill rates on real GoKwik dashboard by launching a visible browser subprocess.

    The subprocess:
    1. Opens a visible Chrome window (user can watch)
    2. Logs into GoKwik (email + password + OTP)
    3. Navigates to Rate Capture
    4. Fills all rates
    5. Returns result as JSON
    """
    data_file = None
    output_file = None

    try:
        # Write extraction data to temp file
        data = {
            "merchant_name": merchant_name,
            "agreement": agreement,
            "tabs": tabs,
            "rate_card_path": rate_card_path or "",
            "agreement_pdf_path": agreement_pdf_path or "",
        }

        data_path = os.path.join(SCREENSHOT_DIR, "_fill_data.json")
        output_path = os.path.join(SCREENSHOT_DIR, "_fill_result.json")

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Clear previous result
        if os.path.exists(output_path):
            os.unlink(output_path)

        # Launch worker as subprocess
        print(f"[Playwright Driver] Launching fill worker for '{merchant_name}'...")
        print(f"[Playwright Driver] Data: {data_path}")
        print(f"[Playwright Driver] Output: {output_path}")

        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", WORKER_MODULE,
            "--data", data_path,
            "--output", output_path,
            cwd=WORKER_DIR,
        )

        # Wait for worker to complete (timeout: 3 minutes)
        # stdout/stderr go directly to server console (no encoding issues)
        try:
            await asyncio.wait_for(process.wait(), timeout=180)
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False, "filled": 0, "failed": 0,
                "steps": [], "screenshot": None,
                "message": "GoKwik fill timed out (3 min). Browser may have gotten stuck.",
            }

        # Read result
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            print(f"[Playwright Driver] Worker result: filled={result.get('filled')}, failed={result.get('failed')}")
            return result
        else:
            return {
                "success": False, "filled": 0, "failed": 0,
                "steps": [], "screenshot": None,
                "message": f"Worker process exited with code {process.returncode}. Check server console for errors.",
            }

    except Exception as e:
        logger.error(f"[Playwright Driver] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False, "filled": 0, "failed": 0,
            "steps": [], "screenshot": None,
            "message": f"Error launching browser: {str(e)}",
        }

    finally:
        # Cleanup temp files
        for path in [data_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


async def verify_gokwik_dashboard(merchant_name: str, expected_tabs: dict = None, target_merchant: str = "", rate_card_name: str = "") -> dict:
    """Launch verify_worker as subprocess to read back and verify rates on GoKwik."""
    VERIFY_MODULE = "automation.verify_worker"

    try:
        data = {
            "merchant_name": merchant_name,
            "tabs": expected_tabs or {},
            "target_merchant": target_merchant or merchant_name,
            "rate_card_name": rate_card_name,
        }

        data_path = os.path.join(SCREENSHOT_DIR, "_verify_data.json")
        output_path = os.path.join(SCREENSHOT_DIR, "_verify_result.json")

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        if os.path.exists(output_path):
            os.unlink(output_path)

        print(f"[Playwright Driver] Launching verify worker for '{merchant_name}'...")

        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", VERIFY_MODULE,
            "--data", data_path,
            "--output", output_path,
            cwd=WORKER_DIR,
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=240)
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False, "actual_rates": {}, "total_read": 0,
                "screenshot": None, "message": "Verify timed out (4 min)",
            }

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return result
        else:
            return {
                "success": False, "actual_rates": {}, "total_read": 0,
                "screenshot": None,
                "message": f"Verify worker exited with code {process.returncode}",
            }

    except Exception as e:
        return {
            "success": False, "actual_rates": {}, "total_read": 0,
            "screenshot": None, "message": f"Error: {str(e)}",
        }
    finally:
        for path in [data_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


async def confirm_gokwik_dashboard() -> dict:
    """Confirm on GoKwik — placeholder for future implementation."""
    return {
        "success": False,
        "message": "Confirm requires active browser session. Use the browser window directly.",
    }
