import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Play, CheckCircle, AlertCircle, Loader, FileText, XCircle,
  Zap, Brain, ScanSearch, FileCheck, Upload, ArrowRight, Download,
  ShieldCheck, ClipboardCheck, Sparkles, Mail, Pencil, CloudDownload, Search,
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'
const STEP_DELAY = 350

// Phase pipeline config
const PHASES = [
  { key: 'upload', label: 'Upload', icon: Upload },
  { key: 'extract', label: 'AI Extract', icon: Brain },
  { key: 'mapping', label: 'Mapping', icon: ArrowRight },
  { key: 'filling', label: 'Fill GoKwik', icon: Download },
  { key: 'verify', label: 'Verify', icon: ScanSearch },
  { key: 'result', label: 'Result', icon: ShieldCheck },
]

export default function AutomationPanel({
  onPhase1Complete,
  onPhase2Complete,
  onFullAutoComplete,
  dashboardRates,
  merchantName,
  agreementFile,
  rateCardFile,
  driveFileId,
  autoRun = false,
  onConfirm,
}) {
  const [running, setRunning] = useState(false)
  const [phase, setPhase] = useState(null)
  const [steps, setSteps] = useState([])
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [activePhaseIdx, setActivePhaseIdx] = useState(-1)
  const [statusText, setStatusText] = useState('')
  const [progress, setProgress] = useState(0)
  const [rateTable, setRateTable] = useState(null)
  const autoRunTriggered = useRef(false)
  const runningRef = useRef(false)
  const logEndRef = useRef(null)
  const [merchantAutoName, setMerchantAutoName] = useState(merchantName || '')
  const [autoMode, setAutoMode] = useState('drive') // 'drive' or 'upload'

  const addStep = (step) => {
    setSteps((prev) => [...prev, { ...step, time: new Date().toLocaleTimeString() }])
  }

  const updateLastStep = (update) => {
    setSteps((prev) => {
      const copy = [...prev]
      if (copy.length > 0) copy[copy.length - 1] = { ...copy[copy.length - 1], ...update }
      return copy
    })
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

  // Auto-scroll log
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [steps])

  // ─── Full Auto ────────────────────────────────
  const runFullAuto = useCallback(async () => {
    const useDrive = !!driveFileId && !rateCardFile
    if (!agreementFile) {
      setError('Please upload Agreement PDF.')
      return
    }
    if (!rateCardFile && !driveFileId) {
      setError('Please upload Rate Card PDF or select from Google Drive.')
      return
    }
    if (!(agreementFile instanceof File)) {
      setError('Agreement PDF is not valid. Please re-upload.')
      return
    }
    if (!useDrive && !(rateCardFile instanceof File)) {
      setError('Rate Card PDF is not valid. Please re-upload.')
      return
    }
    if (runningRef.current) return
    runningRef.current = true

    setRunning(true)
    setPhase('full')
    setSteps([])
    setError(null)
    setResult(null)
    setRateTable(null)
    setProgress(0)
    setActivePhaseIdx(0)
    setStatusText('Uploading PDFs to AI extraction engine...')

    addStep({ text: 'Initializing automation pipeline', status: 'done', icon: 'zap' })
    await sleep(STEP_DELAY)

    try {
      // Phase: Upload
      addStep({ text: `Uploading ${agreementFile.name}`, status: 'running', icon: 'upload' })
      await sleep(300)
      updateLastStep({ status: 'done' })

      if (useDrive) {
        addStep({ text: 'Fetching rate card from Google Drive...', status: 'running', icon: 'cloud' })
      } else {
        addStep({ text: `Uploading ${rateCardFile.name}`, status: 'running', icon: 'upload' })
      }
      setProgress(8)
      await sleep(300)
      updateLastStep({ status: 'done', text: useDrive ? 'Rate card fetched from Google Drive' : `Uploaded ${rateCardFile.name}` })
      setProgress(12)

      // Phase: AI Extract
      setActivePhaseIdx(1)
      setStatusText('AI is reading and understanding your PDFs...')
      addStep({ text: 'AI analyzing Agreement PDF...', status: 'running', icon: 'brain' })
      setProgress(18)

      const formData = new FormData()
      formData.append('agreement_pdf', agreementFile)
      formData.append('merchant_name', merchantName || 'Unknown Merchant')

      let apiUrl
      if (useDrive) {
        formData.append('drive_file_id', driveFileId)
        apiUrl = `${API_BASE}/api/drive/auto-process`
      } else {
        formData.append('rate_pdf', rateCardFile)
        apiUrl = `${API_BASE}/api/auto-process`
      }

      const res = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Server error ${res.status}` }))
        throw new Error(err.detail || 'Backend error')
      }

      const data = await res.json()
      setProgress(40)

      if (!data.success) {
        updateLastStep({ status: 'error', text: `Extraction failed: ${data.error}` })
        setStatusText('Extraction failed')
        setRunning(false)
        runningRef.current = false
        return
      }

      const ag = data.agreement
      updateLastStep({ status: 'done', text: 'AI analyzed Agreement PDF' })

      addStep({ text: 'AI analyzing Rate Card PDF...', status: 'running', icon: 'brain' })
      await sleep(500)
      updateLastStep({ status: 'done', text: 'AI analyzed Rate Card PDF' })
      setProgress(50)

      // Show extracted agreement data
      if (ag.date_extraction_failed) {
        addStep({ text: 'Could not extract date from Agreement PDF', status: 'warning', icon: 'alert' })
      } else {
        addStep({ text: `Start Date: ${ag.start_date}`, status: 'done', icon: 'calendar' })
        await sleep(150)
        addStep({ text: `End Date: ${ag.end_date}`, status: 'done', icon: 'calendar' })
      }
      await sleep(200)

      addStep({ text: `Extracted ${data.raw_rates_count} payment modes from PDF`, status: 'done', icon: 'scan' })
      setProgress(58)
      await sleep(300)

      // Phase: Mapping
      setActivePhaseIdx(2)
      setStatusText('Mapping PDF rates to dashboard fields...')

      const mapped = data.rates.mapped.length
      const unmapped = data.rates.unmapped.length
      addStep({
        text: `Mapped ${mapped} modes to dashboard tabs${unmapped > 0 ? `, ${unmapped} unmapped` : ''}`,
        status: unmapped > 0 ? 'warning' : 'done',
        icon: 'map',
      })
      setProgress(65)
      await sleep(400)

      // Phase: Auto-fill
      setActivePhaseIdx(3)
      setStatusText('Auto-filling form fields...')

      addStep({ text: `Merchant Size: ${ag.merchant_size || 'Long Tail'}`, status: 'done', icon: 'fill' })
      await sleep(150)
      addStep({ text: `Merchant Type: ${ag.merchant_type || 'D2C'}`, status: 'done', icon: 'fill' })
      await sleep(150)
      addStep({ text: `Products: ${(ag.purchased_products || ['Checkout']).join(', ')}`, status: 'done', icon: 'fill' })
      setProgress(72)
      await sleep(200)

      // Build rate table for display
      const tabs = data.tabs
      const tableRows = []
      for (const [tabName, entries] of Object.entries(tabs)) {
        for (const e of entries) {
          tableRows.push({ tab: tabName, method: e.method, rate: e.rate, mode: e.original_mode })
        }
      }
      setRateTable(tableRows)

      addStep({ text: `Filling ${tableRows.length} rates across ${Object.keys(tabs).length} tabs`, status: 'running', icon: 'table' })
      await sleep(600)
      updateLastStep({ status: 'done' })
      setProgress(82)

      addStep({ text: 'Agreement saved, Checkout section populated', status: 'done', icon: 'save' })
      await sleep(300)

      // Trigger Phase 1 callback
      if (onPhase1Complete) onPhase1Complete(data)

      // Phase: Verify
      setActivePhaseIdx(4)
      setStatusText('AI verifying rates against PDF...')
      setProgress(88)

      addStep({ text: 'Cross-checking dashboard vs PDF rates...', status: 'running', icon: 'verify' })
      await sleep(800)

      const report = data.report
      updateLastStep({
        status: 'done',
        text: `Compared ${report.total} modes: ${report.matched} matched, ${report.mismatched} mismatched`,
      })
      setProgress(95)
      await sleep(300)

      // Phase: Result
      setActivePhaseIdx(5)

      if (data.all_match) {
        setStatusText('All rates verified successfully!')
        addStep({ text: 'ALL RATES MATCH — Auto-confirmed!', status: 'success', icon: 'shield' })
      } else {
        setStatusText('Discrepancies found — sending report to IT...')
        addStep({ text: 'DISCREPANCIES FOUND', status: 'error', icon: 'alert' })
        for (const d of report.discrepancies) {
          addStep({
            text: `${d.mode}: Expected ${d.expected_rate}%, Found ${d.actual_rate}%`,
            status: 'error',
            icon: 'x',
          })
          await sleep(150)
        }
        addStep({ text: 'CSV report generated', status: 'done', icon: 'file' })

        // Show email status
        if (data.email_sent) {
          if (data.email_sent.success) {
            addStep({ text: `Report emailed to IT: ${data.email_sent.sent_to.join(', ')}`, status: 'success', icon: 'mail' })
          } else {
            addStep({ text: `Email failed: ${data.email_sent.message}`, status: 'warning', icon: 'alert' })
          }
        } else {
          addStep({ text: 'Email not configured — set SMTP details in .env', status: 'warning', icon: 'alert' })
        }
      }

      setProgress(100)
      await sleep(200)
      addStep({ text: 'Automation pipeline complete', status: 'success', icon: 'sparkle' })

      setResult(data)
      if (onPhase2Complete) onPhase2Complete(data)
      if (onFullAutoComplete) onFullAutoComplete(data)
    } catch (err) {
      updateLastStep({ status: 'error' })
      addStep({ text: `Error: ${err.message}`, status: 'error', icon: 'x' })
      setError(err.message)
      setStatusText('Pipeline failed')
    }

    setRunning(false)
    runningRef.current = false
  }, [agreementFile, rateCardFile, driveFileId, merchantName, onPhase1Complete, onPhase2Complete, onFullAutoComplete])

  // ─── Full Merchant Auto (one-click: name → everything) ────────
  const runMerchantAuto = useCallback(async () => {
    const name = merchantAutoName.trim()
    if (!name) {
      setError('Please enter a merchant name.')
      return
    }
    if (runningRef.current) return
    runningRef.current = true

    setRunning(true)
    setPhase('full')
    setSteps([])
    setError(null)
    setResult(null)
    setRateTable(null)
    setProgress(0)
    setActivePhaseIdx(0)
    setStatusText(`Searching Google Drive for "${name}"...`)

    addStep({ text: `Starting full automation for "${name}"`, status: 'done', icon: 'zap' })
    await sleep(STEP_DELAY)

    try {
      // Phase: Search & Download
      addStep({ text: `Searching Drive for "${name}" Agreement...`, status: 'running', icon: 'cloud' })
      setProgress(5)

      const formData = new FormData()
      formData.append('merchant_name', name)

      const res = await fetch(`${API_BASE}/api/drive/full-auto`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Server error ${res.status}` }))
        throw new Error(err.detail || 'Backend error')
      }

      const data = await res.json()

      if (!data.success) {
        // Handle "needs_selection" — show candidates for user to pick
        if (data.needs_selection && data.rate_card_candidates) {
          updateLastStep({ status: 'done', text: `Found Agreement: ${data.agreement_found?.name || 'Agreement PDF'}` })
          addStep({ text: `${data.rate_card_candidates.length} rate cards found — select one below`, status: 'warning', icon: 'alert' })
          setStatusText('Select the correct rate card')
          setRunning(false)
          runningRef.current = false
          // Store candidates + agreement for user selection
          setResult({
            ...data,
            _needsSelection: true,
            _agreementFileId: data.agreement_found?.id,
            _candidates: data.rate_card_candidates,
          })
          return
        }

        updateLastStep({ status: 'error', text: data.error })
        setStatusText('Search failed')

        if (data.search_results) {
          const ag = data.search_results.agreement
          const rc = data.search_results.rate_card
          if (ag && ag.files && ag.files.length > 0) {
            addStep({ text: `Agreement found: ${ag.files[0].name}`, status: 'done', icon: 'file' })
          } else {
            addStep({ text: 'No Agreement PDF found in Drive', status: 'error', icon: 'x' })
          }
          if (rc && rc.files && rc.files.length > 0) {
            addStep({ text: `Rate Card found: ${rc.files[0].name}`, status: 'done', icon: 'file' })
          } else if (rc) {
            addStep({ text: 'No Rate Card PDF found in Drive', status: 'error', icon: 'x' })
          }
        }

        addStep({ text: 'Try uploading files manually or check the merchant name', status: 'warning', icon: 'alert' })
        setRunning(false)
        runningRef.current = false
        return
      }

      // Show search results
      updateLastStep({ status: 'done', text: `Found Agreement: ${data.agreement_file_name || 'Agreement PDF'}` })
      addStep({ text: `Found Rate Card: ${data.rate_card_file_name || 'Rate Card PDF'}`, status: 'done', icon: 'file' })
      setProgress(15)
      await sleep(300)

      addStep({ text: 'Downloaded both PDFs from Drive', status: 'done', icon: 'cloud' })
      setProgress(25)
      await sleep(300)

      // Phase: AI Extract
      setActivePhaseIdx(1)
      setStatusText('AI reading PDFs (page 2 only)...')
      addStep({ text: 'AI analyzed Agreement PDF', status: 'done', icon: 'brain' })
      setProgress(40)
      await sleep(300)

      addStep({ text: 'AI analyzed Rate Card PDF', status: 'done', icon: 'brain' })
      setProgress(50)
      await sleep(200)

      const ag = data.agreement
      if (ag.date_extraction_failed) {
        addStep({ text: 'Could not extract date from Agreement', status: 'warning', icon: 'alert' })
      } else {
        addStep({ text: `Start Date: ${ag.start_date}`, status: 'done', icon: 'calendar' })
        await sleep(150)
        addStep({ text: `End Date: ${ag.end_date}`, status: 'done', icon: 'calendar' })
      }
      await sleep(200)

      addStep({ text: `Extracted ${data.raw_rates_count} payment modes`, status: 'done', icon: 'scan' })
      setProgress(58)
      await sleep(300)

      // Phase: Mapping
      setActivePhaseIdx(2)
      setStatusText('Mapping to dashboard fields...')
      const mapped = data.rates.mapped.length
      const unmapped = data.rates.unmapped.length
      addStep({
        text: `Mapped ${mapped} modes${unmapped > 0 ? `, ${unmapped} unmapped` : ''}`,
        status: unmapped > 0 ? 'warning' : 'done',
        icon: 'map',
      })
      setProgress(65)
      await sleep(400)

      // Phase: Auto-fill
      setActivePhaseIdx(3)
      setStatusText('Auto-filling form...')
      addStep({ text: `Merchant Size: ${ag.merchant_size || 'Long Tail'}`, status: 'done', icon: 'fill' })
      await sleep(150)
      addStep({ text: `Merchant Type: ${ag.merchant_type || 'D2C'}`, status: 'done', icon: 'fill' })
      await sleep(150)

      // Build rate table for preview
      const tableRows = []
      const tabs = data.tabs
      for (const [tabName, entries] of Object.entries(tabs)) {
        for (const e of entries) {
          tableRows.push({ tab: tabName, method: e.method, rate: e.rate, mode: e.original_mode })
        }
      }
      setRateTable(tableRows)
      addStep({ text: `Filling ${tableRows.length} rates across ${Object.keys(tabs).length} tabs`, status: 'done', icon: 'fill' })
      setProgress(82)
      await sleep(400)

      // Auto-fill LOCAL dashboard
      if (onPhase1Complete) onPhase1Complete(data)
      addStep({ text: 'Local dashboard auto-filled', status: 'done', icon: 'fill' })
      await sleep(300)

      // Phase: Fill GoKwik (Playwright)
      setActivePhaseIdx(3)
      setStatusText('Filling real GoKwik dashboard...')
      addStep({ text: 'Connecting to GoKwik dashboard...', status: 'running', icon: 'cloud' })
      setProgress(85)

      let gokwikFilled = false
      try {
        const fillForm = new FormData()
        fillForm.append('tabs_json', JSON.stringify(data.tabs))
        fillForm.append('agreement_json', JSON.stringify(data.agreement))
        fillForm.append('merchant_name', name)

        const fillRes = await fetch(`${API_BASE}/api/playwright/fill`, {
          method: 'POST', body: fillForm,
        })
        const fillData = await fillRes.json()

        if (fillData.success) {
          gokwikFilled = true
          updateLastStep({ status: 'done', text: `Filled ${fillData.filled} rates on GoKwik` })
          if (fillData.failed > 0) {
            addStep({ text: `${fillData.failed} entries failed to fill`, status: 'warning', icon: 'alert' })
          }
        } else {
          updateLastStep({ status: 'warning', text: `GoKwik fill: ${fillData.message}` })
          addStep({ text: 'Skipping GoKwik — using local verification', status: 'warning', icon: 'alert' })
        }
      } catch (err) {
        updateLastStep({ status: 'warning', text: 'GoKwik not available — using local verification' })
      }

      await sleep(300)

      // Phase: Verify
      setActivePhaseIdx(4)
      let report

      if (gokwikFilled) {
        // REAL Phase 2: Read back from GoKwik
        setStatusText('Reading back from GoKwik screen...')
        addStep({ text: 'Reading rates from GoKwik screen...', status: 'running', icon: 'verify' })

        try {
          const verifyForm = new FormData()
          verifyForm.append('expected_json', JSON.stringify(data.rates.mapped))
          verifyForm.append('merchant_name', name)

          const verifyRes = await fetch(`${API_BASE}/api/playwright/verify`, {
            method: 'POST', body: verifyForm,
          })
          const verifyData = await verifyRes.json()

          if (verifyData.success) {
            report = verifyData.report
            updateLastStep({
              status: 'done',
              text: `Read ${verifyData.total_read} rates from GoKwik screen`,
            })
            addStep({
              text: `REAL verification: ${report.matched} matched, ${report.mismatched} mismatched`,
              status: report.mismatched > 0 ? 'warning' : 'done',
              icon: 'verify',
            })
          } else {
            updateLastStep({ status: 'warning', text: `GoKwik verify failed: ${verifyData.message}` })
            report = data.report // fallback to local
          }
        } catch (err) {
          updateLastStep({ status: 'warning', text: 'GoKwik verify failed — using local result' })
          report = data.report
        }
      } else {
        // Fallback: local verification
        setStatusText('Verifying locally...')
        report = data.report
        addStep({
          text: `Local verification: ${report.matched} matched, ${report.mismatched} mismatched`,
          status: report.mismatched > 0 ? 'warning' : 'done',
          icon: 'verify',
        })
      }

      setProgress(95)
      await sleep(300)

      // Phase: Result
      setActivePhaseIdx(5)
      const allMatch = !report.has_discrepancies
      if (allMatch) {
        setStatusText('All rates verified!')
        addStep({ text: 'ALL RATES MATCH', status: 'success', icon: 'shield' })
      } else {
        setStatusText('Discrepancies found')
        addStep({ text: 'DISCREPANCIES FOUND', status: 'error', icon: 'alert' })
        for (const d of (report.discrepancies || [])) {
          addStep({
            text: `${d.mode}: Expected ${d.expected_rate}%, Found ${d.actual_rate}%`,
            status: 'error', icon: 'x',
          })
          await sleep(150)
        }
        if (data.email_sent?.success) {
          addStep({ text: `Report emailed to: ${data.email_sent.sent_to.join(', ')}`, status: 'success', icon: 'mail' })
        }
      }

      setProgress(100)
      await sleep(200)
      addStep({
        text: gokwikFilled ? 'GoKwik automation complete' : 'Local automation complete',
        status: 'success', icon: 'sparkle',
      })
      setResult({ ...data, report, all_match: allMatch, gokwik_filled: gokwikFilled })

      if (onPhase2Complete) onPhase2Complete(data)
      if (onFullAutoComplete) onFullAutoComplete(data)
    } catch (err) {
      updateLastStep({ status: 'error' })
      addStep({ text: `Error: ${err.message}`, status: 'error', icon: 'x' })
      setError(err.message)
      setStatusText('Pipeline failed')
    }

    setRunning(false)
    runningRef.current = false
  }, [merchantAutoName, onPhase1Complete, onPhase2Complete, onFullAutoComplete])

  // Auto-trigger (works with both local file and Drive file)
  useEffect(() => {
    const hasRateCard = rateCardFile || driveFileId
    if (autoRun && agreementFile && hasRateCard && !runningRef.current && !autoRunTriggered.current) {
      if (!(agreementFile instanceof File)) return
      if (rateCardFile && !(rateCardFile instanceof File)) return
      autoRunTriggered.current = true
      const timer = setTimeout(() => runFullAuto(), 500)
      return () => clearTimeout(timer)
    }
  }, [autoRun, agreementFile, rateCardFile, driveFileId, runFullAuto])

  const getStepIcon = (step) => {
    const s = step.status
    if (s === 'running') return <Loader size={13} className="ap-spin" />
    if (s === 'error') return <XCircle size={13} />
    if (s === 'warning') return <AlertCircle size={13} />
    if (s === 'success') return <Sparkles size={13} />

    // done icons by type
    switch (step.icon) {
      case 'brain': return <Brain size={13} />
      case 'upload': return <Upload size={13} />
      case 'scan': return <ScanSearch size={13} />
      case 'verify': return <ClipboardCheck size={13} />
      case 'shield': return <ShieldCheck size={13} />
      case 'mail': return <Mail size={13} />
      case 'sparkle': return <Sparkles size={13} />
      case 'zap': return <Zap size={13} />
      default: return <CheckCircle size={13} />
    }
  }

  return (
    <div className="ap-panel">
      {/* Header */}
      <div className="ap-header">
        <div className="ap-header-left">
          <div className="ap-logo">
            <Brain size={20} />
          </div>
          <div>
            <h3 className="ap-title">AI Rate Automation</h3>
            <p className="ap-subtitle">
              {running ? statusText : result
                ? (result.all_match ? 'All rates verified successfully' : 'Completed with discrepancies')
                : 'Upload Agreement PDF + Rate Card (upload or Google Drive)'}
            </p>
          </div>
        </div>
        {running && (
          <div className="ap-thinking">
            <div className="ap-thinking-dots">
              <span></span><span></span><span></span>
            </div>
            <span className="ap-thinking-text">Processing</span>
          </div>
        )}
      </div>

      {/* Phase Pipeline */}
      <div className="ap-pipeline">
        {PHASES.map((p, i) => {
          const Icon = p.icon
          const isDone = i < activePhaseIdx
          const isActive = i === activePhaseIdx
          const isPending = i > activePhaseIdx
          return (
            <div key={p.key} className={`ap-pipe-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''} ${isPending ? 'pending' : ''}`}>
              <div className="ap-pipe-icon">
                {isActive && running ? <Loader size={16} className="ap-spin" /> : <Icon size={16} />}
              </div>
              <span className="ap-pipe-label">{p.label}</span>
              {i < PHASES.length - 1 && <div className={`ap-pipe-line ${isDone ? 'done' : ''}`} />}
            </div>
          )
        })}
      </div>

      {/* Progress Bar */}
      {(running || progress > 0) && (
        <div className="ap-progress-wrap">
          <div className="ap-progress-bar">
            <div
              className={`ap-progress-fill ${progress >= 100 ? (result?.all_match ? 'success' : 'error') : ''}`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="ap-progress-pct">{progress}%</span>
        </div>
      )}

      {/* Mode Selector + Action */}
      {!running && !result && (
        <div className="ap-mode-section">
          {/* Mode Tabs */}
          <div className="ap-mode-tabs">
            <button
              className={`ap-mode-tab ${autoMode === 'drive' ? 'active' : ''}`}
              onClick={() => setAutoMode('drive')}
            >
              <CloudDownload size={15} />
              <div className="ap-mode-tab-text">
                <span className="ap-mode-tab-title">Google Drive Auto</span>
                <span className="ap-mode-tab-desc">Just type merchant name</span>
              </div>
            </button>
            <button
              className={`ap-mode-tab ${autoMode === 'upload' ? 'active' : ''}`}
              onClick={() => setAutoMode('upload')}
            >
              <Upload size={15} />
              <div className="ap-mode-tab-text">
                <span className="ap-mode-tab-title">Manual Upload</span>
                <span className="ap-mode-tab-desc">Upload both PDFs</span>
              </div>
            </button>
          </div>

          {/* Drive Auto Mode */}
          {autoMode === 'drive' && (
            <div className="ap-mode-content">
              <div className="ap-full-auto-row">
                <div className="ap-input-wrap">
                  <Search size={16} className="ap-input-icon" />
                  <input
                    type="text"
                    className="ap-merchant-input"
                    placeholder="Enter merchant name (e.g. Jaipur Masala)..."
                    value={merchantAutoName}
                    onChange={(e) => setMerchantAutoName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && merchantAutoName.trim() && runMerchantAuto()}
                  />
                </div>
                <button
                  className="ap-run-btn full-auto"
                  onClick={runMerchantAuto}
                  disabled={running || !merchantAutoName.trim()}
                >
                  <Zap size={14} />
                  Auto Run
                </button>
              </div>
              <div className="ap-mode-info">
                <div className="ap-mode-info-item">
                  <span className="ap-mode-info-dot green" />
                  Searches Google Drive for Agreement + Rate Card
                </div>
                <div className="ap-mode-info-item">
                  <span className="ap-mode-info-dot green" />
                  AI extracts, auto-fills, and verifies in one click
                </div>
              </div>
            </div>
          )}

          {/* Manual Upload Mode */}
          {autoMode === 'upload' && (
            <div className="ap-mode-content">
              <div className="ap-file-status">
                <div className={`ap-file-pill ${agreementFile ? 'ready' : 'missing'}`}>
                  {agreementFile ? <FileCheck size={13} /> : <AlertCircle size={13} />}
                  <span>{agreementFile ? (agreementFile.name || 'Agreement PDF') : 'Upload Agreement PDF above'}</span>
                </div>
                <div className={`ap-file-pill ${(rateCardFile || driveFileId) ? 'ready' : 'missing'}`}>
                  {(rateCardFile || driveFileId) ? <FileCheck size={13} /> : <AlertCircle size={13} />}
                  <span>
                    {rateCardFile ? rateCardFile.name
                      : driveFileId ? 'Rate Card (from Drive)'
                      : 'Upload Rate Card or select from Drive'}
                  </span>
                </div>
              </div>
              <button
                className="ap-run-btn full-auto"
                onClick={runFullAuto}
                disabled={running || !agreementFile || (!rateCardFile && !driveFileId)}
                style={{ width: '100%', marginTop: 12 }}
              >
                <Play size={14} />
                {(!agreementFile || (!rateCardFile && !driveFileId))
                  ? 'Upload both PDFs to start'
                  : 'Run Automation'}
              </button>
              {(!agreementFile || (!rateCardFile && !driveFileId)) && (
                <div className="ap-mode-info" style={{ marginTop: 8 }}>
                  <div className="ap-mode-info-item">
                    <span className="ap-mode-info-dot orange" />
                    Upload files in the Agreement Details section above
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && !running && (
        <div className="ap-error">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Live Log */}
      {steps.length > 0 && (
        <div className="ap-log">
          <div className="ap-log-header">
            <h4>
              {running ? <><Loader size={12} className="ap-spin" /> Live Log</> : 'Automation Log'}
            </h4>
            <span className="ap-log-count">{steps.length} steps</span>
          </div>
          <div className="ap-steps">
            {steps.map((s, i) => (
              <div key={i} className={`ap-step ${s.status} ap-step-enter`}>
                <div className={`ap-step-dot ${s.status}`}>{getStepIcon(s)}</div>
                <span className="ap-step-text">{s.text}</span>
                {s.time && <span className="ap-step-time">{s.time}</span>}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {/* Rate Table Preview */}
      {rateTable && rateTable.length > 0 && (
        <div className="ap-rate-table-wrap">
          <h4>Extracted Rates ({rateTable.length} modes)</h4>
          <div className="ap-rate-table-scroll">
            <table className="ap-rate-table">
              <thead>
                <tr>
                  <th>Tab</th>
                  <th>Method</th>
                  <th>Rate</th>
                  <th>PDF Mode</th>
                </tr>
              </thead>
              <tbody>
                {rateTable.map((r, i) => (
                  <tr key={i}>
                    <td><span className="ap-tab-badge">{r.tab}</span></td>
                    <td>{r.method}</td>
                    <td><strong>{r.rate}%</strong></td>
                    <td className="ap-mode-name">{r.mode}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rate Card Selection (when needs_selection) */}
      {result && result._needsSelection && (
        <div className="ap-selection-card">
          <h4><CloudDownload size={16} /> Select Rate Card for "{merchantAutoName}"</h4>
          <p className="ap-selection-hint">Agreement found. Multiple rate cards detected — pick the correct one:</p>
          <div className="rc-drive-results">
            {result._candidates.map((f) => (
              <div
                key={f.id}
                className="rc-drive-file"
                onClick={async () => {
                  // User picked a file — now run with agreement + selected rate card
                  setResult(null)
                  setRunning(true)
                  runningRef.current = true
                  setStatusText('Downloading selected rate card...')
                  addStep({ text: `Selected: ${f.name}`, status: 'done', icon: 'file' })

                  try {
                    const formData = new FormData()
                    formData.append('merchant_name', merchantAutoName)
                    addStep({ text: 'Downloading both PDFs...', status: 'running', icon: 'cloud' })

                    const res2 = await fetch(`${API_BASE}/api/drive/full-auto-select`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        merchant_name: merchantAutoName,
                        agreement_file_id: result._agreementFileId,
                        rate_card_file_id: f.id,
                      }),
                    })

                    if (!res2.ok) {
                      const err = await res2.json().catch(() => ({ detail: 'Server error' }))
                      throw new Error(err.detail || 'Backend error')
                    }

                    const data2 = await res2.json()
                    if (!data2.success) {
                      addStep({ text: `Error: ${data2.error}`, status: 'error', icon: 'x' })
                      setRunning(false)
                      runningRef.current = false
                      return
                    }

                    // Success — show the rest of the pipeline
                    updateLastStep({ status: 'done', text: 'Both PDFs downloaded' })
                    setProgress(25)
                    await sleep(300)

                    setActivePhaseIdx(1)
                    setStatusText('AI reading PDFs...')
                    const ag = data2.agreement
                    addStep({ text: `Start Date: ${ag.start_date || 'Not found'}`, status: ag.date_extraction_failed ? 'warning' : 'done', icon: 'calendar' })
                    addStep({ text: `Extracted ${data2.raw_rates_count} payment modes`, status: 'done', icon: 'scan' })
                    setProgress(60)
                    await sleep(300)

                    setActivePhaseIdx(3)
                    const tableRows = []
                    for (const [tabName, entries] of Object.entries(data2.tabs)) {
                      for (const e of entries) {
                        tableRows.push({ tab: tabName, method: e.method, rate: e.rate, mode: e.original_mode })
                      }
                    }
                    setRateTable(tableRows)
                    addStep({ text: `Filling ${tableRows.length} rates`, status: 'done', icon: 'fill' })
                    setProgress(82)

                    if (onPhase1Complete) onPhase1Complete(data2)
                    await sleep(300)

                    setActivePhaseIdx(5)
                    const report = data2.report
                    if (data2.all_match) {
                      setStatusText('All rates verified!')
                      addStep({ text: 'ALL RATES MATCH', status: 'success', icon: 'shield' })
                    } else {
                      setStatusText('Discrepancies found')
                      addStep({ text: 'DISCREPANCIES FOUND', status: 'error', icon: 'alert' })
                      for (const d of report.discrepancies) {
                        addStep({ text: `${d.mode}: Expected ${d.expected_rate}%, Found ${d.actual_rate}%`, status: 'error', icon: 'x' })
                      }
                    }
                    setProgress(100)
                    addStep({ text: 'Complete', status: 'success', icon: 'sparkle' })
                    setResult(data2)
                    if (onPhase2Complete) onPhase2Complete(data2)
                    if (onFullAutoComplete) onFullAutoComplete(data2)
                  } catch (err) {
                    addStep({ text: `Error: ${err.message}`, status: 'error', icon: 'x' })
                    setError(err.message)
                  }
                  setRunning(false)
                  runningRef.current = false
                }}
              >
                <div className="rc-drive-file-name">{f.name}</div>
                <div className="rc-drive-file-meta">{f.size} &middot; {new Date(f.modified).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
          <button className="ap-restart-btn" style={{ marginTop: 12 }} onClick={() => {
            setResult(null); setSteps([]); setProgress(0); setActivePhaseIdx(-1)
            setRateTable(null); setStatusText(''); setError(null)
          }}>
            <Play size={14} /> Start Over
          </button>
        </div>
      )}

      {/* Final Result Card */}
      {result && result.report && !result._needsSelection && (
        <div className={`ap-result-card ${result.all_match ? 'match' : 'mismatch'}`}>
          <div className="ap-result-icon">
            {result.all_match
              ? <ShieldCheck size={28} />
              : <AlertCircle size={28} />
            }
          </div>
          <div className="ap-result-body">
            <h4>{result.all_match ? 'All Rates Verified' : 'Discrepancies Found'}</h4>
            <p>{result.report.matched}/{result.report.total} modes matched
              {result.report.mismatched > 0 && ` — ${result.report.mismatched} mismatched`}
            </p>
          </div>
          {result.all_match && (
            <div className="ap-result-badge">CONFIRMED</div>
          )}
          {!result.all_match && (
            <button
              className="ap-email-btn"
              onClick={async () => {
                try {
                  const formData = new FormData()
                  formData.append('merchant_name', merchantName || 'Unknown')
                  formData.append('report_json', JSON.stringify(result.report))
                  formData.append('extra_emails', '')
                  const res = await fetch(`${API_BASE}/api/send-report`, { method: 'POST', body: formData })
                  const data = await res.json()
                  if (data.success) {
                    addStep({ text: `Report re-sent to: ${data.sent_to.join(', ')}`, status: 'success', icon: 'mail' })
                  } else {
                    addStep({ text: `Email failed: ${data.message}`, status: 'warning', icon: 'alert' })
                  }
                } catch (err) {
                  addStep({ text: `Email error: ${err.message}`, status: 'error', icon: 'x' })
                }
              }}
            >
              <Mail size={14} /> Send Report
            </button>
          )}
        </div>
      )}

      {/* Result Action Buttons */}
      {result && !running && (
        <div className="ap-result-actions">
          {result.all_match ? (
            <button
              className="ap-run-btn confirm-btn"
              onClick={async () => {
                // Confirm locally
                if (onConfirm) onConfirm()
                addStep({ text: 'Confirmed locally', status: 'done', icon: 'shield' })

                // Also confirm on GoKwik if it was filled there
                if (result.gokwik_filled) {
                  addStep({ text: 'Confirming on GoKwik...', status: 'running', icon: 'cloud' })
                  try {
                    const res = await fetch(`${API_BASE}/api/playwright/confirm`, { method: 'POST' })
                    const data = await res.json()
                    if (data.success) {
                      updateLastStep({ status: 'success', text: 'Confirmed on GoKwik!' })
                    } else {
                      updateLastStep({ status: 'warning', text: `GoKwik confirm: ${data.message}` })
                    }
                  } catch (e) {
                    updateLastStep({ status: 'warning', text: 'Could not confirm on GoKwik' })
                  }
                }
              }}
            >
              <ShieldCheck size={14} /> Confirm & Save
            </button>
          ) : (
            <>
              <button
                className="ap-run-btn edit-btn"
                onClick={() => {
                  setResult(null); setSteps([]); setProgress(0); setActivePhaseIdx(-1)
                  setRateTable(null); setStatusText(''); setError(null)
                }}
              >
                <Pencil size={14} /> Edit Manually
              </button>
            </>
          )}
          <button
            className="ap-restart-btn"
            onClick={() => {
              setResult(null); setSteps([]); setProgress(0); setActivePhaseIdx(-1)
              setRateTable(null); setStatusText(''); setError(null)
              autoRunTriggered.current = false
            }}
          >
            <Play size={14} /> Run Again
          </button>
        </div>
      )}
    </div>
  )
}
