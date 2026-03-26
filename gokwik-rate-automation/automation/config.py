"""
Playwright automation configuration.

Change DASHBOARD_URL to point to real GoKwik dashboard when ready.
Selectors are centralized here — update when GoKwik DOM changes.
"""

# ── Dashboard URL ─────────────────────────────────────
# Local dashboard (current)
DASHBOARD_URL = "http://localhost:5173"
# Real GoKwik dashboard (future)
# DASHBOARD_URL = "https://dashboard.gokwik.co"

# ── Backend API ───────────────────────────────────────
API_BASE = "http://localhost:8000"

# ── Timeouts ──────────────────────────────────────────
PAGE_TIMEOUT = 30000       # 30s for page loads
ACTION_TIMEOUT = 5000      # 5s for clicks/fills
TAB_SWITCH_DELAY = 500     # ms to wait after clicking a tab
ADD_ROW_DELAY = 300        # ms to wait after clicking Add
BETWEEN_TABS_DELAY = 300   # ms between filling different tabs

# ── Selectors (centralized — change here when DOM changes) ──

# Navigation
SEL_RATE_CAPTURE_NAV = "text=Rate Capture"
SEL_RUN_AUTOMATION = "text=Run Automation"

# Agreement Section
SEL_AGREEMENT_SECTION = "text=Agreement Details"
SEL_AGREEMENT_START_DATE = 'input[type="date"]:first-of-type'
SEL_AGREEMENT_END_DATE = 'input[type="date"]:nth-of-type(2)'
SEL_SAVE_AGREEMENT = "text=Save"

# Checkout Section
SEL_CHECKOUT_SECTION = "text=Checkout"

# Payment Tabs
PAYMENT_TABS = ['EMI', 'UPI', 'NetBanking', 'Wallet', 'Credit Card', 'Debit Card', 'BNPL', 'COD', 'Others', 'PPCOD']

# Commission Table
SEL_COMMISSION_TABLE = "table tbody"
SEL_COMMISSION_ROWS = "table tbody tr"

# Buttons
SEL_ADD_BUTTON = "text=Add"
SEL_SAVE_BUTTON = "text=Save"
SEL_CONFIRM_BUTTON = "text=Confirm"
