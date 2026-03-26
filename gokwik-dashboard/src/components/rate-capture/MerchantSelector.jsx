import { dummyMerchants } from '../../constants/rateCapture'

export default function MerchantSelector({
  activeMerchant,
  onMerchantSwitch,
  onBack,
  confirmed,
  showAutomation,
  onToggleAutomation,
  onConfirm,
}) {
  return (
    <>
      {/* ─── Top Header (matches original: RATE CAPTURE | Switch merchant [green dot] dropdown) ─── */}
      <div className="rc-topbar">
        <div className="rc-topbar-left">
          <span className="rc-badge">RATE CAPTURE</span>
        </div>
        <div className="rc-topbar-right">
          <span className="rc-switch-label">Switch merchant</span>
          <div className="rc-merchant-select-wrapper">
            <span className="rc-merchant-dot"></span>
            <select
              className="rc-merchant-select"
              value={activeMerchant}
              onChange={(e) => onMerchantSwitch(e.target.value)}
            >
              {dummyMerchants.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ─── Actions Bar (matches original: ← Agreements | [Automation] [Confirm]) ─── */}
      <div className="rc-actions-bar">
        <button className="rc-back-link" onClick={onBack}>
          &larr; Agreements
        </button>
        <div className="rc-actions-right">
          {confirmed && (
            <span className="rc-status-badge confirmed">Confirmed</span>
          )}
          <button
            className={`rc-automation-toggle ${showAutomation ? 'active' : ''}`}
            onClick={onToggleAutomation}
          >
            {showAutomation ? 'Hide Automation' : 'Run Automation'}
          </button>
          <button
            className={`rc-confirm-btn ${confirmed ? 'confirmed' : ''}`}
            onClick={onConfirm}
            disabled={confirmed}
          >
            {confirmed ? 'Confirmed' : 'Confirm'}
          </button>
        </div>
      </div>
    </>
  )
}
