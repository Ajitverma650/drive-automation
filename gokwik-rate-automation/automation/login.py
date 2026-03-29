"""
GoKwik Dashboard — Programmatic Login (Email + Password + OTP).

Tested against real GoKwik sandbox login page:
  - Step 1: Email input → "Next" button
  - Step 2: Password input → "Next" button
  - Step 3: OTP input (******) → "Next" button
  - Redirects to /executive-summary on success

Usage:
    from automation.login import login_to_gokwik
    await login_to_gokwik(page)
"""

from playwright.async_api import Page

from automation.config import (
    GOKWIK_URL,
    GOKWIK_EMAIL,
    GOKWIK_PASSWORD,
    GOKWIK_OTP,
    LOGIN_TIMEOUT,
)


async def login_to_gokwik(
    page: Page,
    email: str = None,
    password: str = None,
    otp: str = None,
) -> bool:
    """
    Log into GoKwik dashboard with email + password + OTP.

    Uses the exact selectors verified on the real GoKwik sandbox dashboard.
    Each step uses a "Next" button (not Login/Submit).

    Args:
        page: Playwright page instance
        email: Override email (defaults to config)
        password: Override password (defaults to config)
        otp: Override OTP (defaults to config)

    Returns:
        True if login succeeded, False otherwise.
    """
    email = email or GOKWIK_EMAIL
    password = password or GOKWIK_PASSWORD
    otp = otp or GOKWIK_OTP

    print(f"[Login] Navigating to {GOKWIK_URL}...")
    await page.goto(GOKWIK_URL, timeout=LOGIN_TIMEOUT)
    await page.wait_for_timeout(2000)

    # Check if already logged in (not on login page)
    if "login" not in page.url.lower() and "verify-otp" not in page.url.lower():
        print("[Login] Already logged in!")
        return True

    print(f"[Login] On login page: {page.url}")
    print(f"[Login] Logging in as {email}...")

    # ─── Step 1: Enter Email ─────────────────────────────
    try:
        email_input = page.locator('input[placeholder*="email" i]').first
        await email_input.wait_for(state="visible", timeout=LOGIN_TIMEOUT)
        await email_input.click()
        await email_input.fill(email)
        print(f"[Login] Email entered: {email}")
        await page.wait_for_timeout(500)

        # Click "Next" button (becomes enabled after email typed)
        next_btn = page.locator('button:has-text("Next"):not([disabled])')
        await next_btn.wait_for(state="visible", timeout=5000)
        await next_btn.click()
        print("[Login] Email submitted via Next")
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"[Login] Email step failed: {e}")
        # Fallback: try generic selectors
        try:
            fallback = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]').first
            await fallback.fill(email)
            await page.wait_for_timeout(500)
            await page.locator('button:has-text("Next"), button[type="submit"]').first.click()
            await page.wait_for_timeout(2000)
        except Exception:
            pass

    # ─── Step 2: Enter Password ──────────────────────────
    try:
        password_input = page.locator('input[type="password"]').first
        await password_input.wait_for(state="visible", timeout=LOGIN_TIMEOUT)
        await password_input.click()
        await password_input.fill(password)
        print("[Login] Password entered")
        await page.wait_for_timeout(500)

        # Click "Next" button
        next_btn = page.locator('button:has-text("Next"):not([disabled])')
        await next_btn.wait_for(state="visible", timeout=5000)
        await next_btn.click()
        print("[Login] Password submitted via Next")
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"[Login] Password step failed: {e}")
        pass

    # ─── Step 3: Enter OTP (capture token from API response) ────
    auth_token = None

    async def capture_otp_response(response):
        nonlocal auth_token
        if "verify-otp" in response.url and response.status == 200:
            try:
                data = await response.json()
                token = data.get("data", {}).get("token", "")
                if token:
                    auth_token = token
                    print(f"[Login] Captured auth token from API ({len(token)} chars)")
            except Exception:
                pass

    page.on("response", capture_otp_response)

    try:
        # Wait for OTP page (/verify-otp)
        await page.wait_for_url("**/verify-otp**", timeout=10000)
        print(f"[Login] On OTP page: {page.url}")

        # OTP input
        otp_input = page.locator('input[placeholder="******"]').first
        await otp_input.wait_for(state="visible", timeout=LOGIN_TIMEOUT)
        await otp_input.click()
        await page.wait_for_timeout(200)
        await otp_input.fill(otp)
        print(f"[Login] OTP entered: {otp}")
        await page.wait_for_timeout(500)

        # Click Next
        next_btn = page.locator('button:has-text("Next"):not([disabled])')
        await next_btn.wait_for(state="visible", timeout=5000)
        await next_btn.click()
        print("[Login] OTP submitted via Next button")
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"[Login] OTP step failed: {e}")
        try:
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000)
        except Exception:
            pass

    # Remove listener
    page.remove_listener("response", capture_otp_response)

    # ─── Verify Login Success ────────────────────────────
    final_url = page.url
    print(f"[Login] Final URL: {final_url}")

    if "login" not in final_url.lower() and "verify-otp" not in final_url.lower():
        print("[Login] Login successful!")
        return True

    # OTP API returned 200 + token but React didn't navigate.
    # Inject the token into localStorage and force-navigate.
    if auth_token:
        print("[Login] Injecting captured token into localStorage...")
        await page.evaluate(f"""() => {{
            localStorage.setItem('token', '{auth_token}');
            localStorage.setItem('auth_token', '{auth_token}');
            localStorage.setItem('gk_token', '{auth_token}');
        }}""")
        await page.wait_for_timeout(500)

        # Also set as cookie
        await page.context.add_cookies([{
            "name": "token",
            "value": auth_token,
            "domain": "sandbox-mdashboard.dev.gokwik.in",
            "path": "/",
        }])
        print("[Login] Token injected. Force-navigating...")
    else:
        print("[Login] No token captured. Trying force-navigate anyway...")

    # Force-navigate to Rate Capture
    await page.goto(f"{GOKWIK_URL}/general/rateCapture", timeout=30000)
    await page.wait_for_timeout(3000)

    final_url = page.url
    print(f"[Login] After force-navigate: {final_url}")

    if "login" not in final_url.lower() and "verify-otp" not in final_url.lower():
        print("[Login] Login successful (after token injection)!")
        return True

    # Try executive-summary
    await page.goto(f"{GOKWIK_URL}/executive-summary", timeout=30000)
    await page.wait_for_timeout(3000)

    final_url = page.url
    if "login" not in final_url.lower() and "verify-otp" not in final_url.lower():
        print("[Login] Login successful!")
        return True

    # Last resort: check what keys the app actually uses in localStorage
    print("[Login] Debugging localStorage...")
    ls_keys = await page.evaluate("() => Object.keys(localStorage)")
    print(f"[Login] localStorage keys: {ls_keys}")

    print("[Login] Login failed — could not establish session")
    await page.screenshot(path="login_failed.png", full_page=True)
    return False


async def navigate_to_rate_capture(page: Page) -> bool:
    """
    Navigate to Rate Capture using sidebar menu (avoids session loss from URL navigation).

    Uses: Admin → Rate Capture in the sidebar.
    """
    try:
        # Click Admin in sidebar to expand submenu
        admin_menu = page.get_by_role("menuitem", name="Admin")
        await admin_menu.click()
        await page.wait_for_timeout(500)

        # Click Rate Capture in the submenu
        rate_capture = page.get_by_role("menuitem", name="Rate Capture")
        await rate_capture.click()
        await page.wait_for_timeout(2000)

        # Verify we're on Rate Capture page
        if "rateCapture" in page.url:
            print("[Login] Navigated to Rate Capture via sidebar")
            return True

        print(f"[Login] Navigation failed, URL: {page.url}")
        return False
    except Exception as e:
        print(f"[Login] Sidebar navigation failed: {e}")
        # Fallback: direct URL (may cause session issues)
        try:
            await page.goto(f"{GOKWIK_URL}/general/rateCapture", timeout=30000)
            await page.wait_for_timeout(2000)
            if "rateCapture" in page.url:
                return True
        except Exception:
            pass
        return False
