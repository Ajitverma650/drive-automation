import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Play, CheckCircle, AlertCircle, Loader, FileText, XCircle,
  Zap, Brain, ScanSearch, FileCheck, Upload, ArrowRight, Download,
  ShieldCheck, ClipboardCheck, Sparkles, Mail,
} from 'lucide-react'

const API_BASE = 'http://localhost:8000'
const STEP_DELAY = 350

// Phase pipeline config
const PHASES = [
  { key: 'upload', label: 'Upload', icon: Upload },
  { key: 'extract', label: 'AI Extracting', icon: Brain },
  { key: 'mapping', label: 'Mapping', icon: ArrowRight },
  { key: 'filling', label: 'Auto-Fill', icon: Download },
  { key: 'verify', label: 'Verifying', icon: ScanSearch },
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
  autoRun = false,
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
    if (!agreementFile || !rateCardFile) {
      setError('Please upload both Agreement PDF and Rate Card PDF.')
      return
    }
    if (!(agreementFile instanceof File) || !(rateCardFile instanceof File)) {
      setError('Files are not valid. Please re-upload.')
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
      addStep({ text: `Uploading ${rateCardFile.name}`, status: 'running', icon: 'upload' })
      setProgress(8)
      await sleep(300)
      updateLastStep({ status: 'done' })
      setProgress(12)

      // Phase: AI Extract
      setActivePhaseIdx(1)
      setStatusText('AI is reading and understanding your PDFs...')
      addStep({ text: 'AI analyzing Agreement PDF...', status: 'running', icon: 'brain' })
      setProgress(18)

      const formData = new FormData()
      formData.append('agreement_pdf', agreementFile)
      formData.append('rate_pdf', rateCardFile)
      formData.append('merchant_name', merchantName || 'Unknown Merchant')

      const res = await fetch(`${API_BASE}/api/auto-process`, {
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
  }, [agreementFile, rateCardFile, merchantName, onPhase1Complete, onPhase2Complete, onFullAutoComplete])

  // Auto-trigger
  useEffect(() => {
    if (autoRun && agreementFile && rateCardFile && !runningRef.current && !autoRunTriggered.current) {
      if (!(agreementFile instanceof File) || !(rateCardFile instanceof File)) return
      autoRunTriggered.current = true
      const timer = setTimeout(() => runFullAuto(), 500)
      return () => clearTimeout(timer)
    }
  }, [autoRun, agreementFile, rateCardFile, runFullAuto])

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
                : 'Upload both PDFs to start'}
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

      {/* File Status Pills */}
      <div className="ap-file-status">
        <div className={`ap-file-pill ${agreementFile ? 'ready' : 'missing'}`}>
          <FileCheck size={13} />
          <span>{agreementFile ? (agreementFile.name || 'Agreement') : 'Agreement PDF'}</span>
        </div>
        <div className={`ap-file-pill ${rateCardFile ? 'ready' : 'missing'}`}>
          <FileText size={13} />
          <span>{rateCardFile ? rateCardFile.name : 'Rate Card PDF'}</span>
        </div>
      </div>

      {/* Action Buttons */}
      {!running && !result && (
        <div className="ap-actions">
          <button className="ap-run-btn full-auto" onClick={runFullAuto} disabled={running || !agreementFile || !rateCardFile}>
            <Zap size={15} />
            Run Full Automation
          </button>
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

      {/* Final Result Card */}
      {result && result.report && (
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

      {/* Restart */}
      {result && !running && (
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
      )}
    </div>
  )
}
