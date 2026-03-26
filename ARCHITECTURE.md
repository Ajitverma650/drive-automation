# GoKwik Rate Capture Automation - Architecture

## System Overview

A full-stack automation system that extracts payment commission rates from merchant agreement PDFs using AI (OpenAI GPT-4o-mini) and auto-fills them into the GoKwik dashboard, then verifies accuracy — all triggered automatically on PDF upload with a rich animated UI.

```
+------------------------------------------------------------------+
|                        FRONTEND                                   |
|                  (React 19 + Vite 8)                              |
|                                                                   |
|  +--------------------+    +----------------------------------+   |
|  |   RateCapture      |    |     AutomationPanel              |   |
|  |   (Main Form)      |--->|     (Visual Orchestrator)        |   |
|  |                    |    |                                  |   |
|  | - Agreement upload |    | - 6-step phase pipeline          |   |
|  | - Rate Card upload |    |   (Upload > AI Extract > Map >   |   |
|  | - 10 payment tabs  |    |    Auto-Fill > Verify > Result)  |   |
|  | - Auto-triggers    |    | - Animated progress bar          |   |
|  |   on both uploads  |    | - Thinking dots animation        |   |
|  +--------------------+    | - Live log with slide-in steps   |   |
|                            | - Rate table preview              |   |
|                            | - Result card (match/mismatch)    |   |
|                            +----------------------------------+   |
|                                       |                           |
|                                       | HTTP POST (FormData)      |
+---------------------------------------|---------------------------+
                                        |
                                        v
+------------------------------------------------------------------+
|                        BACKEND                                    |
|                  (Python FastAPI)                                  |
|                                                                   |
|  +--------------------------------------------------------------+|
|  |          /api/auto-process (Main Endpoint)                   ||
|  |                                                              ||
|  |  1. Save uploaded PDFs to temp files                         ||
|  |  2. Extract agreement info (LLM primary -> regex fallback)   ||
|  |  3. Extract rates (LLM primary -> table -> regex fallback)   ||
|  |  4. Map 16 PDF modes to 8 dashboard tabs + specific methods  ||
|  |  5. Self-verify: compare extracted vs mapped rates           ||
|  |  6. Generate discrepancy report                              ||
|  |  7. Return all data for frontend auto-fill                   ||
|  +--------------------------------------------------------------+|
|                                                                   |
|  +-----------------+  +-------------------+  +-----------------+  |
|  | /api/phase1/    |  | /api/phase2/      |  | /api/health     |  |
|  | extract         |  | verify            |  | (health check)  |  |
|  | (standalone)    |  | (standalone)      |  +-----------------+  |
|  +-----------------+  +-------------------+                       |
+------------------------------------------------------------------+
```

## Tech Stack

| Layer     | Technology          | Purpose                          |
|-----------|--------------------|---------------------------------|
| Frontend  | React 19 + Vite 8 | Dashboard UI                    |
| Styling   | CSS Variables      | Theming, animations, transitions|
| Charts    | Recharts           | KPI visualizations              |
| Icons     | Lucide React       | 15+ icons (Brain, Zap, Shield..)|
| Backend   | FastAPI            | REST API server                 |
| PDF Parse | pdfplumber         | Table & text extraction fallback|
| LLM       | OpenAI GPT-4o-mini | Primary AI extraction engine    |
| Dates     | python-dateutil    | Date arithmetic (start + 3yr)   |
| Launcher  | run.py             | Single-command project starter  |

## Directory Structure

```
Automation task/
├── run.py                            # Single-command launcher (both servers)
├── ARCHITECTURE.md                   # This file
├── HOW_IT_WORKS.md                   # Step-by-step usage guide
├── (rate_capture_docs).pdf           # Original requirements doc
│
├── gokwik-dashboard/                 # Frontend
│   ├── src/
│   │   ├── App.jsx                   # Main app with routing
│   │   ├── App.css                   # All styles (incl. animation CSS)
│   │   └── components/
│   │       ├── RateCapture.jsx       # Main rate entry form
│   │       ├── AutomationPanel.jsx   # Visual automation orchestrator
│   │       ├── Sidebar.jsx           # Navigation
│   │       ├── TopBar.jsx            # Header
│   │       ├── KpiCards.jsx          # KPI widgets
│   │       ├── RevenueChart.jsx      # GMV chart
│   │       ├── ConversionChart.jsx   # Funnel chart
│   │       ├── RTOAnalytics.jsx      # RTO comparison
│   │       ├── OrdersTable.jsx       # Orders list
│   │       └── PaymentMethods.jsx    # Payment distribution
│   ├── package.json
│   └── vite.config.js
│
├── gokwik-rate-automation/           # Backend
│   ├── server.py                     # FastAPI server (4 endpoints)
│   ├── .env                          # OPENAI_API_KEY=sk-proj-...
│   ├── requirements.txt              # Python dependencies
│   ├── create_sample_pdfs.py         # Test PDF generator
│   ├── extraction/                   # PDF data extraction
│   │   ├── llm_extractor.py          # OpenAI GPT-4o-mini extraction
│   │   ├── rate_parser.py            # Rate extraction (LLM -> table -> regex)
│   │   ├── agreement_parser.py       # Agreement extraction (LLM -> regex)
│   │   └── date_calculator.py        # start_date + 3 years
│   ├── transformation/               # Data mapping
│   │   ├── mode_mapping.py           # PDF modes -> dashboard tabs + methods
│   │   └── data_models.py            # Data classes
│   └── reporting/                    # Output
│       └── discrepancy_report.py     # CSV report generation
```

## API Endpoints

### POST `/api/auto-process` (Primary - Full Automation)

Runs the complete pipeline: extract + fill + verify in one request.

**Input:**
- `agreement_pdf` (file) - Merchant agreement PDF
- `rate_pdf` (file) - Rate card PDF
- `merchant_name` (string) - Merchant name

**Output:**
```json
{
  "success": true,
  "agreement": { "start_date": "2026-03-01", "end_date": "2029-03-01", ... },
  "tabs": { "UPI": [...], "EMI": [...], ... },
  "all_match": true,
  "report": { "matched": 16, "mismatched": 0, "summary": "..." },
  "phase1_complete": true,
  "phase2_complete": true,
  "steps": [...]
}
```

### POST `/api/phase1/extract` (Standalone Phase 1)
Extracts data from PDFs without verification.

### POST `/api/phase2/verify` (Standalone Phase 2)
Compares dashboard rates against PDF rates.

### GET `/api/health`
Health check.

## Extraction Strategy (3-Tier Fallback)

```
PDF Upload
    │
    ▼
┌─────────────────────┐
│ Tier 1: OpenAI LLM  │ ← Best accuracy, handles any layout
│ (GPT-4o-mini)       │   Requires OPENAI_API_KEY in .env
└─────────┬───────────┘
          │ fails?
          ▼
┌─────────────────────┐
│ Tier 2: pdfplumber  │ ← Table extraction
│ (Table detection)   │   Needs structured table headers
└─────────┬───────────┘
          │ fails?
          ▼
┌─────────────────────┐
│ Tier 3: Regex       │ ← Text pattern matching
│ (Line-by-line)      │   Handles "Mode Name  2.5%" format
└─────────────────────┘
```

## Payment Mode Mapping (16 modes → 8 tabs)

| PDF Mode                       | Dashboard Tab  | Method         |
|-------------------------------|----------------|----------------|
| UPI                           | UPI            | Default        |
| UPI Credit Card (Rupay only)  | UPI            | Credit Card    |
| DC Below2K                    | Debit Card     | Below 2K       |
| DC Above2K                    | Debit Card     | Above 2K       |
| Credit Card                   | Credit Card    | Default        |
| Amex                          | Credit Card    | Amex           |
| Diners Credit Card            | Credit Card    | Diners         |
| Corporate Credit Card         | Credit Card    | Corporate      |
| International CC              | Credit Card    | International  |
| CC EMI                        | EMI            | CC EMI         |
| DC EMI                        | EMI            | DC EMI         |
| Debit Card EMI                | EMI            | Debit Card EMI |
| Card Less EMI                 | EMI            | Cardless EMI   |
| Net Banking                   | NetBanking     | Default        |
| Wallets                       | Wallet         | Default        |
| BNPL                          | BNPL           | Default        |

## Frontend Visual Architecture

### AutomationPanel Components

```
┌──────────────────────────────────────────────────┐
│ [Brain Icon] AI Rate Automation                  │
│ Status: "AI is reading and understanding..."     │
│                                    [... Processing]│
├──────────────────────────────────────────────────┤
│ Phase Pipeline (6 steps):                        │
│ ○ Upload → ● AI Extracting → ○ Mapping →        │
│ ○ Auto-Fill → ○ Verifying → ○ Result             │
├──────────────────────────────────────────────────┤
│ ████████████████████░░░░░░░░░░░  58%             │
├──────────────────────────────────────────────────┤
│ [✓ agreement.pdf] [✓ rate_card.pdf]              │
├──────────────────────────────────────────────────┤
│ Live Log:                          12 steps      │
│ ┌──────────────────────────────────────────────┐ │
│ │ ⚡ Initializing automation pipeline  10:30:01│ │
│ │ ⬆ Uploading agreement.pdf           10:30:01│ │
│ │ 🧠 AI analyzing Agreement PDF...    10:30:02│ │
│ │ 🧠 AI analyzing Rate Card PDF...    10:30:03│ │
│ │ ✓ Start Date: 2026-03-01            10:30:03│ │
│ │ ✓ Extracted 16 payment modes         10:30:03│ │
│ │ ...                                          │ │
│ └──────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────┤
│ Extracted Rates (16 modes):                      │
│ ┌────────────┬────────────┬──────┬─────────────┐ │
│ │ Tab        │ Method     │ Rate │ PDF Mode    │ │
│ ├────────────┼────────────┼──────┼─────────────┤ │
│ │ UPI        │ Default    │ 2.5% │ UPI         │ │
│ │ Credit Card│ Amex       │ 3%   │ Amex        │ │
│ │ EMI        │ CC EMI     │ 0%   │ CC EMI      │ │
│ └────────────┴────────────┴──────┴─────────────┘ │
├──────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐ │
│ │ [✓] All Rates Verified    16/16   CONFIRMED  │ │
│ └──────────────────────────────────────────────┘ │
│ [▶ Run Again]                                    │
└──────────────────────────────────────────────────┘
```

### CSS Animations Used

| Animation              | Purpose                              |
|-----------------------|--------------------------------------|
| `ap-gradient-shift`   | Rainbow gradient on top border        |
| `ap-dot-pulse`        | Thinking dots (3-dot bounce)          |
| `ap-pulse-ring`       | Active phase icon glow ring           |
| `ap-shimmer`          | Progress bar shine sweep              |
| `ap-step-slide`       | Log entries slide in from left        |
| `ap-result-pop`       | Result card scale-in on completion    |
| `ap-spin`             | Loader spinner rotation               |

## Frontend State Architecture

```
merchantStore (per-merchant)
├── agreement         # Agreement form fields
│   ├── merchantAgreementFile (File object - preserved, never overwritten)
│   ├── startDate / endDate
│   ├── merchantSize / merchantType
│   └── purchasedProducts
├── agreementSaved    # Controls checkout section visibility
├── checkout          # Pricing dates, fees
└── tabData           # Per-payment-tab commission data
    ├── EMI: { commissions: [{method: "CC EMI", value: "0"}, ...] }
    ├── UPI: { commissions: [{method: "Default", value: "2.5"}, ...] }
    ├── Credit Card: { commissions: [{method: "Amex", value: "3"}, ...] }
    └── ... (10 tabs total)
```

## Security Notes

- OpenAI API key stored in `.env` (not committed to git)
- CORS configured for local development (`allow_origins=["*"]`)
- Temp files cleaned up after processing (finally blocks)
- PDF text sent to OpenAI for extraction — ensure compliance with data policies
- File objects validated as `instanceof File` before FormData upload
