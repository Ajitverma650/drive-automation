# GoKwik Rate Capture Automation - How It Works

## Quick Start

### Option 1: Single Command (Recommended)

```bash
cd "Automation task"
python run.py
```

This starts both backend (:8000) and frontend (:5173) together. Press Ctrl+C to stop both.

### Option 2: Manual Start

**Terminal 1 — Backend:**
```bash
cd gokwik-rate-automation
pip install -r requirements.txt
python server.py
# Server starts at http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd gokwik-dashboard
npm install
npm run dev
# Dashboard opens at http://localhost:5173
```

### 3. Use It

1. Open http://localhost:5173 and click **Rate Capture** in the sidebar
2. Upload **Agreement PDF** (merchant agreement document)
3. Upload **Rate Card PDF** (payment rates document)
4. **Automation triggers automatically** — no buttons to click
5. Watch the animated pipeline as AI extracts, fills, and verifies everything

---

## Full Automation Flow (Step-by-Step)

### What Happens When You Upload Both PDFs

```
User uploads Agreement PDF + Rate Card PDF
         │
         ▼
┌─────────────────────────────────────────────┐
│ STEP 1: Auto-Detection                      │
│                                             │
│ RateCapture.jsx detects both files present. │
│ Sets autoRunTriggered = true.               │
│ AutomationPanel opens automatically.        │
│ Pipeline visualization appears.             │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ STEP 2: Upload Phase                        │
│ [Pipeline: ● Upload → ○ ○ ○ ○ ○]           │
│                                             │
│ AutomationPanel sends both PDFs to:         │
│ POST /api/auto-process (FormData)           │
│ Progress bar: 0% → 12%                     │
│ Thinking animation: "Uploading PDFs..."     │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ STEP 3: AI Extraction Phase                 │
│ [Pipeline: ✓ ● AI Extracting → ○ ○ ○ ○]    │
│                                             │
│ 🧠 AI analyzing Agreement PDF...            │
│  - Sends PDF text to GPT-4o-mini           │
│  - LLM returns: start_date, merchant_size, │
│    merchant_type, purchased_products        │
│  - Falls back to regex if LLM unavailable  │
│                                             │
│ 🧠 AI analyzing Rate Card PDF...            │
│  - LLM extracts [{mode, rate}, ...] array  │
│  - 3-tier fallback: LLM → table → regex    │
│                                             │
│ Progress bar: 12% → 50%                    │
│ Log: "AI analyzed Agreement PDF ✓"          │
│ Log: "AI analyzed Rate Card PDF ✓"          │
│ Log: "Extracted 16 payment modes from PDF"  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ STEP 4: Mapping Phase                       │
│ [Pipeline: ✓ ✓ ● Mapping → ○ ○ ○]          │
│                                             │
│ Maps 16 PDF modes to dashboard tabs:        │
│  "UPI"           → UPI / Default            │
│  "CC EMI"        → EMI / CC EMI             │
│  "Amex"          → Credit Card / Amex       │
│  "DC Below2K"    → Debit Card / Below 2K    │
│  etc.                                       │
│                                             │
│ Uses: exact match → alias → fuzzy match     │
│ Progress bar: 50% → 65%                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ STEP 5: Auto-Fill Phase                     │
│ [Pipeline: ✓ ✓ ✓ ● Auto-Fill → ○ ○]        │
│                                             │
│ Fills agreement form:                       │
│  - Merchant Size: Long Tail                 │
│  - Merchant Type: D2C                       │
│  - Products: Checkout                       │
│  - Start Date / End Date                    │
│                                             │
│ Fills 16 rates across 8 tabs:               │
│  [UPI] Default=2.5%, Credit Card=3%        │
│  [Credit Card] Default=2.5%, Amex=3%, ...  │
│  [EMI] CC EMI=0%, DC EMI=2.5%, ...         │
│                                             │
│ Rate table preview appears in UI            │
│ Progress bar: 65% → 82%                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ STEP 6: Verification Phase                  │
│ [Pipeline: ✓ ✓ ✓ ✓ ● Verifying → ○]        │
│                                             │
│ Cross-checks extracted rates against mapped │
│ dashboard values:                           │
│  1. Match by originalMode (exact)           │
│  2. Match by method + rate value            │
│  3. Match by method only (first unused)     │
│                                             │
│ Progress bar: 82% → 95%                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ STEP 7: Result Phase                        │
│ [Pipeline: ✓ ✓ ✓ ✓ ✓ ● Result]             │
│                                             │
│ If ALL MATCH (16/16):                       │
│  ┌─────────────────────────────────────┐    │
│  │ [✓] All Rates Verified   CONFIRMED  │    │
│  │     16/16 modes matched             │    │
│  └─────────────────────────────────────┘    │
│                                             │
│ If MISMATCH:                                │
│  ┌─────────────────────────────────────┐    │
│  │ [!] Discrepancies Found             │    │
│  │     14/16 matched — 2 mismatched    │    │
│  └─────────────────────────────────────┘    │
│  + CSV report generated for IT team         │
│                                             │
│ Progress bar: 100%                          │
│ [▶ Run Again] button appears                │
└─────────────────────────────────────────────┘
```

---

## What the User Sees

### Visual Pipeline

The 6-step animated pipeline at the top shows progress:

```
○ Upload → ● AI Extracting → ○ Mapping → ○ Auto-Fill → ○ Verifying → ○ Result
              ↑ (active = purple glow + pulse ring + spinner)

✓ Upload → ✓ AI Extracting → ✓ Mapping → ● Auto-Fill → ○ Verifying → ○ Result
                                            ↑ (green = done, grey = pending)
```

### Thinking Animation

While the backend processes:
```
[Brain Icon] AI Rate Automation
Status: "AI is reading and understanding your PDFs..."
                                         ● ● ● Processing
```

### Progress Bar

```
████████████████████░░░░░░░░░░░  58%
       ↑ shimmer animation sweeps across
```

### Live Log (with timestamps and icons)

```
⚡ Initializing automation pipeline            10:30:01
⬆  Uploading sample_agreement.pdf              10:30:01
⬆  Uploading sample_rate_card.pdf              10:30:01
🧠 AI analyzing Agreement PDF...               10:30:02
🧠 AI analyzing Rate Card PDF...               10:30:03
✓  Start Date: 2026-03-01                      10:30:03
✓  End Date: 2029-03-01                        10:30:03
✓  Extracted 16 payment modes from PDF         10:30:03
✓  Mapped 16 modes to dashboard tabs           10:30:04
✓  Merchant Size: Long Tail                    10:30:04
✓  Merchant Type: D2C                          10:30:04
✓  Products: Checkout                          10:30:04
✓  Filling 16 rates across 8 tabs              10:30:04
✓  Agreement saved, Checkout section populated 10:30:05
🔍 Cross-checking dashboard vs PDF rates...    10:30:05
✓  Compared 16 modes: 16 matched, 0 mismatched 10:30:05
✨ ALL RATES MATCH — Auto-confirmed!           10:30:06
✨ Automation pipeline complete                10:30:06
```

### Rate Table Preview

After extraction, a table appears showing all mapped rates:

| Tab         | Method       | Rate | PDF Mode                      |
|-------------|-------------|------|-------------------------------|
| UPI         | Default     | 2.5% | UPI                           |
| UPI         | Credit Card | 3%   | UPI Credit Card (Rupay only)  |
| Credit Card | Default     | 2.5% | Credit Card                   |
| Credit Card | Amex        | 3%   | Amex                          |
| Credit Card | Diners      | 2.5% | Diners Credit Card            |
| Credit Card | Corporate   | 3%   | Corporate Credit Card         |
| Credit Card | International| 0%  | International CC              |
| Debit Card  | Below 2K    | 2.5% | DC Below2K                    |
| Debit Card  | Above 2K    | 2.5% | DC Above2K                    |
| EMI         | CC EMI      | 0%   | CC EMI                        |
| EMI         | DC EMI      | 2.5% | DC EMI                        |
| EMI         | Debit Card EMI| 0%  | Debit Card EMI                |
| EMI         | Cardless EMI| 0%   | Card Less EMI                 |
| NetBanking  | Default     | 2.5% | Net Banking                   |
| Wallet      | Default     | 2.5% | Wallets                       |
| BNPL        | Default     | 0%   | BNPL                          |

### Result Card

**All Match:**
```
┌────────────────────────────────────────────────────┐
│ [✓ green circle]  All Rates Verified    CONFIRMED  │
│                   16/16 modes matched              │
└────────────────────────────────────────────────────┘
```

**Discrepancies:**
```
┌────────────────────────────────────────────────────┐
│ [! red circle]  Discrepancies Found                │
│                 14/16 matched — 2 mismatched       │
└────────────────────────────────────────────────────┘
```

---

## OpenAI LLM Integration

### Why LLM?

| Feature              | pdfplumber (regex) | OpenAI LLM        |
|---------------------|-------------------|--------------------|
| Structured tables   | Works             | Works              |
| Unstructured text   | Fails             | Works              |
| Varied layouts      | Fails             | Works              |
| Fuzzy mode names    | Limited           | Excellent          |
| Date in paragraphs  | Limited patterns  | Understands context|
| Scanned PDFs (OCR)  | No                | If text extracted  |

### Configuration

Add your OpenAI API key to `gokwik-rate-automation/.env`:

```
OPENAI_API_KEY=sk-proj-your-full-api-key-here
```

The code checks both `OPENAI_API_KEY` and `OPEN_AI_KEY` for backward compatibility.

### Model Used

- **GPT-4o-mini** — fast, cheap, accurate for structured extraction
- Temperature: 0 (deterministic output)
- Max tokens: 2000 (rates), 500 (agreement)

### Fallback Behavior

If the OpenAI key is missing or invalid:
1. System logs: `[LLM Extractor] Rate extraction failed: ...`
2. Automatically falls back to pdfplumber/regex
3. Everything still works — LLM is optional, not required

---

## Testing

### Using Sample PDFs

```bash
cd gokwik-rate-automation

# Generate test PDFs
pip install reportlab
python create_sample_pdfs.py
# Creates: sample_agreement.pdf, sample_rate_card.pdf

# Test the full pipeline
curl -X POST http://localhost:8000/api/auto-process \
  -F "agreement_pdf=@sample_agreement.pdf" \
  -F "rate_pdf=@sample_rate_card.pdf" \
  -F "merchant_name=TestMerchant"
```

### Expected Result

```json
{
  "success": true,
  "phase1_complete": true,
  "phase2_complete": true,
  "all_match": true,
  "raw_rates_count": 16,
  "report": { "matched": 16, "mismatched": 0 }
}
```

### Test Individual Endpoints

```bash
# Phase 1 only (extract)
curl -X POST http://localhost:8000/api/phase1/extract \
  -F "agreement_pdf=@sample_agreement.pdf" \
  -F "rate_pdf=@sample_rate_card.pdf"

# Phase 2 only (verify)
curl -X POST http://localhost:8000/api/phase2/verify \
  -F "rate_pdf=@sample_rate_card.pdf" \
  -F "dashboard_rates={\"UPI\":[{\"method\":\"Default\",\"rate\":2.5}]}" \
  -F "merchant_name=TestMerchant"

# Health check
curl http://localhost:8000/api/health
```

---

## Supported Payment Modes (16 Total)

| # | PDF Mode Name                  | Rate  | Dashboard Tab | Method         |
|---|-------------------------------|-------|---------------|----------------|
| 1 | UPI                           | 2.5%  | UPI           | Default        |
| 2 | UPI Credit Card (Rupay only)  | 3%    | UPI           | Credit Card    |
| 3 | DC Below2K                    | 2.5%  | Debit Card    | Below 2K       |
| 4 | DC Above2K                    | 2.5%  | Debit Card    | Above 2K       |
| 5 | Credit Card                   | 2.5%  | Credit Card   | Default        |
| 6 | Amex                          | 3%    | Credit Card   | Amex           |
| 7 | Diners Credit Card            | 2.5%  | Credit Card   | Diners         |
| 8 | Corporate Credit Card         | 3%    | Credit Card   | Corporate      |
| 9 | International CC              | 0%    | Credit Card   | International  |
| 10| CC EMI                        | 0%    | EMI           | CC EMI         |
| 11| DC EMI                        | 2.5%  | EMI           | DC EMI         |
| 12| Debit Card EMI                | 0%    | EMI           | Debit Card EMI |
| 13| Card Less EMI                 | 0%    | EMI           | Cardless EMI   |
| 14| Net Banking                   | 2.5%  | NetBanking    | Default        |
| 15| Wallets                       | 2.5%  | Wallet        | Default        |
| 16| BNPL                          | 0%    | BNPL          | Default        |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| 404 on /api/auto-process | Server running old code | Restart: `python server.py` |
| LLM extraction failed (401) | Invalid/truncated API key | Check `.env` has complete `OPENAI_API_KEY` |
| "No rate table found" | PDF format not recognized | Check PDF has rate data; regex handles "Mode Rate%" lines |
| CORS error | Backend not running | Start backend on port 8000 |
| Automation doesn't auto-trigger | Only one PDF uploaded | Upload BOTH agreement + rate card PDFs |
| Methods show "Default" everywhere | Old mode_mapping.py | Restart backend to pick up updated mapping |
| Double execution in dev | React Strict Mode | Normal in dev; `runningRef` guard prevents actual duplication |
| Progress bar stuck | Backend slow / API key slow | Wait for LLM response; check terminal for errors |
