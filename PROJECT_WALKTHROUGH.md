# GoKwik Rate Capture Automation — Complete Project Walkthrough

## What This Project Does

This project automates the **Rate Capture** process for GoKwik merchants. Instead of manually reading PDF documents and typing 16+ payment rates into a dashboard, a user simply types a merchant name and everything happens automatically:

```
User types "Jaipur" → System finds PDFs in Google Drive → AI reads page 2
→ Extracts dates and 16 payment rates → Fills the dashboard → Verifies → Done
```

The entire process takes ~10 seconds instead of ~20 minutes of manual work.

---

## Project Structure

```
Automation task/
├── run.py                              # Single command to start everything
├── PROJECT_WALKTHROUGH.md              # This file
├── ARCHITECTURE.md                     # System architecture diagrams
├── HOW_IT_WORKS.md                     # Step-by-step usage guide
│
├── gokwik-rate-automation/             # BACKEND (Python FastAPI)
│   ├── server.py                       # Entry point (5 lines)
│   ├── .env                            # API keys, SMTP, Drive config
│   ├── credentials.json                # Google Drive OAuth (not in git)
│   ├── token.json                      # Google Drive auth token (not in git)
│   ├── requirements.txt
│   ├── auth_drive.py                   # One-time Google Drive auth script
│   ├── app/
│   │   ├── main.py                     # FastAPI app + CORS + routers
│   │   ├── config.py                   # All settings centralized
│   │   ├── routes/                     # API endpoints
│   │   │   ├── phase1.py              # Extract from PDFs
│   │   │   ├── phase2.py              # Verify rates
│   │   │   ├── auto_process.py        # Full pipeline (upload)
│   │   │   ├── drive.py               # Google Drive integration
│   │   │   └── email.py               # Email + health endpoints
│   │   ├── services/                   # Business logic
│   │   │   ├── comparison.py          # Rate comparison engine
│   │   │   ├── extraction.py          # Step builder
│   │   │   ├── email.py               # SMTP email sender
│   │   │   └── google_drive.py        # Drive search + download
│   │   ├── extraction/                 # PDF data extraction
│   │   │   ├── llm_extractor.py       # OpenAI GPT-4o-mini
│   │   │   ├── rate_parser.py         # 3-tier extraction
│   │   │   └── agreement_parser.py    # Date + agreement extraction
│   │   ├── transformation/
│   │   │   └── mode_mapping.py        # PDF modes → dashboard fields
│   │   └── reporting/
│   │       └── discrepancy_report.py  # CSV + summary reports
│   └── tests/
│       └── create_sample_pdfs.py
│
├── gokwik-dashboard/                   # FRONTEND (React + Vite)
│   ├── src/
│   │   ├── App.jsx                    # Main app
│   │   ├── App.css                    # All styles
│   │   ├── constants/
│   │   │   └── rateCapture.js         # All config, dropdown options
│   │   └── components/
│   │       ├── layout/                # Sidebar, TopBar
│   │       ├── dashboard/             # KPI cards, charts, tables
│   │       ├── common/                # ChipSelect, TagSelect, Toast
│   │       └── rate-capture/          # The main feature
│   │           ├── RateCapture.jsx    # State container
│   │           ├── AgreementSection.jsx
│   │           ├── CheckoutSection.jsx
│   │           ├── CommissionTable.jsx
│   │           ├── CommissionForm.jsx
│   │           ├── MerchantSelector.jsx
│   │           └── AutomationPanel.jsx # AI automation UI
│   └── package.json
```

---

## How It Works — Three Automation Modes

### Mode 1: One-Click Full Auto (Recommended)

**User provides:** Just a merchant name

```
Type "Jaipur" → Click "Auto Run"
         │
         ▼
Backend searches Google Drive:
  1. Agreement: "Jaipur" + "Agreement" → finds "72_Jaipur Masala Agreement.pdf"
  2. Rate Card: "Jaipur" + "Indicative Terms" → finds candidates
         │
         ▼ (if multiple rate cards found)
Frontend shows selection list → user picks the right one
         │
         ▼
Backend downloads both PDFs from Drive
         │
         ▼
AI extracts from page 2 of each PDF
         │
         ▼
Dashboard auto-filled → Verified → Confirm or Report
```

### Mode 2: Manual Upload + Google Drive Rate Card

**User provides:** Agreement PDF (upload) + Rate card name (search Drive)

```
Upload Agreement PDF manually
Switch Rate Card to "Google Drive" tab
Search merchant name → select file from results
Automation triggers → extracts → fills → verifies
```

### Mode 3: Full Manual Upload

**User provides:** Both PDFs (upload)

```
Upload Agreement PDF
Upload Rate Card PDF
Automation triggers automatically when both are present
```

---

## Backend — How Each Piece Works

### API Endpoints (11 total)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/phase1/extract` | POST | Extract from uploaded PDFs |
| `/api/phase2/verify` | POST | Compare PDF vs dashboard rates |
| `/api/auto-process` | POST | Full pipeline with uploaded files |
| `/api/drive/status` | GET | Is Google Drive configured? |
| `/api/drive/search?merchant=X` | GET | Search Drive for PDFs |
| `/api/drive/auto-process` | POST | Agreement upload + Drive rate card |
| `/api/drive/full-auto` | POST | Just merchant name → everything |
| `/api/drive/full-auto-select` | POST | Continue after user picks rate card |
| `/api/send-report` | POST | Manually send email report |
| `/api/email-status` | GET | Is email configured? |

### PDF Extraction — 3-Tier Fallback

```
PDF uploaded
    │
    ▼ (extract text from PAGE 2 ONLY — saves tokens)
    │
    ├── Tier 1: OpenAI GPT-4o-mini (LLM)
    │   - Sends ~500 tokens (page 2 text only)
    │   - Returns structured JSON
    │   - Cost: ~$0.0002 per call
    │   - Handles any PDF layout
    │
    ├── Tier 2: pdfplumber (table detection)  ← if LLM fails
    │   - Finds table with "Modes" + "Commercials" headers
    │   - Parses rows into {mode, rate}
    │   - Free, no API call
    │
    └── Tier 3: Regex (line-by-line)  ← if table detection fails
        - Matches patterns like "UPI 2.5%"
        - Free, no API call
```

### Why Page 2 Only?

```python
# app/config.py
RATE_PAGE = 2       # Rate Card: rates table is on page 2
AGREEMENT_PAGE = 2  # Agreement: execution date is on page 2

# How it works (app/extraction/llm_extractor.py):
def _extract_text_from_pdf(pdf_path, target_page=2):
    with pdfplumber.open(pdf_path) as pdf:
        # pdf.pages[1] = page 2 (0-indexed)
        pages_to_process = [pdf.pages[target_page - 1]]
        # Only this page's text is sent to OpenAI
```

Token comparison:
- All pages (14 pages): ~15,000 tokens = $0.002
- Page 2 only: ~500 tokens = $0.0001
- **Savings: 95% fewer tokens, 20x cheaper**

### Payment Mode Mapping

The Rate Card PDF has mode names like "CC EMI", "DC Below2K", "Amex". The GoKwik dashboard has specific tabs and dropdown values. The mapping connects them:

```
PDF Mode                    → Dashboard Tab    → Dropdown Method
────────────────────────     ──────────────     ────────────────
UPI                         → UPI              → Default
UPI Credit Card (Rupay)     → UPI              → Credit Card
DC Below2K                  → Debit Card       → Below 2K
DC Above2K                  → Debit Card       → Above 2K
Credit Card                 → Credit Card      → Default
Amex                        → Credit Card      → Amex
Diners Credit Card          → Credit Card      → Diners
Corporate Credit Card       → Credit Card      → Corporate
International CC            → Credit Card      → International
CC EMI                      → EMI              → Credit Card
DC EMI                      → EMI              → Debit Card
Debit Card EMI              → EMI              → Debit Card
Card Less EMI               → EMI              → Cardless
Net Banking                 → NetBanking       → Default
Wallets                     → Wallet           → Default
BNPL                        → BNPL             → Default
```

These dropdown values EXACTLY match the real GoKwik dashboard options.

### Phase 1 vs Phase 2

```
Phase 1 (Maker):    PDF → Extract → Fill Dashboard     (WRITING)
Phase 2 (Checker):  PDF → Extract → Compare Dashboard  (READING + CHECKING)

Phase 1 answers: "What rates should be in the dashboard?"
Phase 2 answers: "Are the dashboard rates correct?"
```

In the current auto-process, Phase 2 verifies that the mapping didn't lose or corrupt data. In a Playwright/extension setup, Phase 2 would compare against the real GoKwik dashboard values.

### Google Drive Integration

```
credentials.json (OAuth2 client) → auth_drive.py (one-time login) → token.json (saved)

Search strategy for Agreement PDF:
  1. "{merchant} Agreement"    → "Jaipur Agreement"
  2. "{merchant} MSA"          → "Jaipur MSA"
  3. "{merchant} signed"       → "Jaipur signed"

Search strategy for Rate Card PDF:
  1. "{merchant} Indicative"   → "Jaipur Indicative"
  2. "{merchant} Terms"        → "Jaipur Terms"
  3. "{merchant} Rate"         → "Jaipur Rate"
  4. Fallback: any "Indicative Terms" file → user picks

Edge case: Rate cards often don't have merchant name in filename.
  Solution: fallback shows all "Indicative Terms" PDFs and asks user to select.
```

### Email on Mismatch

When Phase 2 finds discrepancies:
1. HTML email with rich table (Expected vs Actual rates)
2. CSV attachment with all entries (matched + mismatched)
3. Auto-sent to EMAIL_TO from .env
4. Manual "Send Report" button as fallback

---

## Frontend — How Each Component Works

### Component Hierarchy

```
App.jsx
  ├── Sidebar.jsx (navigation)
  ├── TopBar.jsx (header)
  ├── Dashboard components (KPI, charts, tables)
  └── RateCapture.jsx (STATE CONTAINER - 502 lines)
        ├── MerchantSelector.jsx (merchant tabs + action buttons)
        ├── AutomationPanel.jsx (AI automation UI - 750+ lines)
        │     ├── Merchant name input + "Auto Run" button
        │     ├── 6-step phase pipeline visualization
        │     ├── Progress bar with shimmer animation
        │     ├── File status pills
        │     ├── Live automation log with timestamps
        │     ├── Rate table preview
        │     ├── Drive file selection dropdown
        │     └── Result card (Confirm/Edit/RunAgain/SendReport)
        ├── AgreementSection.jsx (agreement form)
        │     ├── Agreement PDF upload
        │     ├── Rate Card: Upload / Google Drive toggle
        │     ├── Drive search input + results dropdown
        │     └── Date, size, type, agency, products fields
        ├── CheckoutSection.jsx (checkout form)
        │     ├── Pricing dates, fees
        │     ├── 10 payment tabs
        │     └── CommissionForm.jsx (add row)
        │         └── CommissionTable.jsx (entries table)
```

### State Management

All state lives in `RateCapture.jsx` via `merchantStore`:

```javascript
merchantStore = {
  "sandbox": {
    agreement: { startDate, endDate, merchantSize, merchantType, ... },
    agreementSaved: false,
    checkout: { pricingStartDate, pricingEndDate, ... },
    tabData: {
      EMI: { commissions: [{method: "Credit Card", value: "0"}, ...] },
      UPI: { commissions: [{method: "Default", value: "2.5"}, ...] },
      // ... 10 tabs total
    }
  },
  "jaipur-masala": { ... },
  // ... per-merchant state
}
```

Key design decision: `handlePhase1Complete` updates all state in a **single atomic `setMerchantStore` call** to prevent stale state bugs (previously, separate setState calls caused dates to not fill).

### Auto-Fill Flow (Frontend)

```
Backend returns JSON:
{
  agreement: { start_date: "2021-12-01", merchant_size: "Long Tail", ... },
  tabs: {
    EMI: [{ method: "Credit Card", rate: 0, original_mode: "CC EMI" }],
    UPI: [{ method: "Default", rate: 2.5, original_mode: "UPI" }],
    ...
  }
}
         │
         ▼
handlePhase1Complete(data) in RateCapture.jsx:
  - Sets agreement fields (dates, size, type, products)
  - Marks agreement as saved → reveals checkout section
  - Fills checkout pricing dates
  - Fills all 10 payment tab commissions
  - ALL in one atomic state update
```

---

## Configuration (.env)

```bash
# Required
OPENAI_API_KEY=sk-proj-...          # GPT-4o-mini for PDF extraction

# Optional: Google Drive
GOOGLE_DRIVE_CREDENTIALS=credentials.json
GOOGLE_DRIVE_FOLDER_ID=             # Restrict search to specific folder

# Optional: Email on mismatch
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password     # Gmail App Password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=it-support@gokwik.co
EMAIL_CC=
```

---

## Running the Project

### Option 1: Single Command

```bash
python run.py
# Starts backend (:8000) + frontend (:5173)
```

### Option 2: Manual

```bash
# Terminal 1: Backend
cd gokwik-rate-automation
pip install -r requirements.txt
python server.py

# Terminal 2: Frontend
cd gokwik-dashboard
npm install
npm run dev
```

### First-Time Google Drive Setup

```bash
cd gokwik-rate-automation
python auth_drive.py
# Opens browser → Google login → grant access → token.json saved
```

---

## Security

| Item | Protected By |
|---|---|
| OpenAI API key | `.env` (gitignored) |
| Google OAuth credentials | `credentials.json` (gitignored) |
| Google auth token | `token.json` (gitignored) |
| SMTP password | `.env` (gitignored) |
| Uploaded PDFs | Temp files, deleted after processing |
| PDF text to OpenAI | Only page 2 sent, not full document |

---

## Cost Per Merchant

| Component | Cost |
|---|---|
| Agreement extraction (page 2, ~500 tokens) | $0.00008 |
| Rate extraction (page 2, ~800 tokens) | $0.00012 |
| Google Drive API (search + download) | Free |
| Email (SMTP) | Free |
| **Total per merchant** | **~$0.0002** |

Processing 1000 merchants costs approximately $0.20.

---

## Edge Cases Handled

| Scenario | How It's Handled |
|---|---|
| PDF has no rates on page 2 | Falls back to all pages |
| LLM unavailable / API key invalid | Falls back to pdfplumber → regex |
| Multiple dates in agreement | Picks date from agreement body text, not signatures |
| Duplicate modes in PDF | Warns, deduplicates exact dupes, keeps different rates |
| Rate > 100% or < 0% | Rejected as invalid |
| DC EMI + Debit Card EMI collision | Both map to EMI/Debit Card, matched by original_mode |
| Rate card has no merchant name | Fallback search for "Indicative Terms" → user picks |
| Google Drive not authenticated | Shows "Run auth_drive.py" message |
| Email not configured | Shows warning, "Send Report" button for manual retry |
| Large PDF (> 50MB) | Blocked at download |
| Empty PDF | Detected and rejected |
| Invalid date format | Tries DD/MM/YYYY (Indian) first, then MM/DD/YYYY |
| React double-render (Strict Mode) | `runningRef` guard prevents duplicate API calls |
| Stale state in multi-setState | Single atomic `setMerchantStore` update |

---

## Future: Real GoKwik Dashboard Integration

The current system works on a local dashboard clone. To automate the real GoKwik dashboard:

| Approach | How | Effort |
|---|---|---|
| **Playwright** | Python script opens Chrome, fills real GoKwik page | 2-3 days |
| **Chrome Extension** | Injects into GoKwik page, fills from inside browser | 3-4 days |

The backend stays 100% the same. Only the "delivery mechanism" changes — instead of filling React state, it fills real DOM elements on the GoKwik page.

```
Current:  Backend JSON → React setState → Local dashboard filled
Future:   Backend JSON → Playwright/Extension → Real GoKwik dashboard filled
                         → Reads back values → Phase 2 compares → Real verification
```
