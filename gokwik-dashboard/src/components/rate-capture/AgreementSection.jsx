import { ChevronDown, ChevronUp, Upload, Pencil, X } from 'lucide-react'
import ChipSelect from '../common/ChipSelect'
import {
  merchantSizeOptions,
  merchantTypeOptions,
  agencyOptions,
  productOptions,
} from '../../constants/rateCapture'

export default function AgreementSection({
  agreement,
  setAgreement,
  agreementSaved,
  agreementEditMode,
  agreementOpen,
  setAgreementOpen,
  fileInputRef,
  rateCardInputRef,
  rateCardName,
  onFileUpload,
  onRemoveFile,
  onRemoveRateCard,
  onSaveAgreement,
  onEditAgreement,
  getAgreementStatus,
  isFieldDisabled,
}) {
  const driveMode = false // rate card loaded from Drive shows different style
  return (
    <div className="rc-section">
      <div className="rc-section-header" onClick={() => setAgreementOpen(!agreementOpen)}>
        {agreementOpen ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        <h3>Agreement Details</h3>
        <span className={`rc-status-badge ${getAgreementStatus().className}`}>
          {getAgreementStatus().label}
        </span>
        <div className="rc-section-header-right">
          {agreementSaved && !agreementEditMode && (
            <button className="rc-edit-btn" onClick={onEditAgreement}>
              <Pencil size={14} /> Edit
            </button>
          )}
        </div>
      </div>
      {agreementOpen && (
        <div className="rc-section-body">
          {/* Row 1: Two file uploads side by side */}
          <div className="rc-form-grid-2">
            <div className="rc-field">
              <label>Merchant Agreement</label>
              <input
                type="file"
                ref={fileInputRef}
                onChange={onFileUpload}
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
                style={{ display: 'none' }}
              />
              {agreement.merchantAgreementName ? (
                <div className="rc-file-display">
                  <span className="rc-file-name" title={agreement.merchantAgreementName}>
                    {agreement.merchantAgreementName}
                  </span>
                  {agreementEditMode && (
                    <button className="rc-file-remove" onClick={onRemoveFile}>
                      <X size={14} />
                    </button>
                  )}
                </div>
              ) : (
                <div
                  className={`rc-upload-box ${isFieldDisabled ? 'disabled' : ''}`}
                  onClick={() => agreementEditMode && fileInputRef.current?.click()}
                >
                  <Upload size={14} />
                  <span>Click here to upload</span>
                </div>
              )}
            </div>
            <div className="rc-field">
              <label>Rate Card PDF</label>
              <input
                type="file"
                ref={rateCardInputRef}
                onChange={(e) => {
                  const file = e.target.files[0]
                  if (file) onFileUpload(e, 'rateCard')
                }}
                accept=".pdf"
                style={{ display: 'none' }}
              />
              {rateCardName ? (
                <div className={`rc-file-display rc-file-rate ${driveMode ? 'rc-file-drive' : ''}`}>
                  <span className="rc-file-name" title={rateCardName}>
                    {rateCardName}
                  </span>
                  <button className="rc-file-remove" onClick={onRemoveRateCard}>
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <div className="rc-upload-box" onClick={() => rateCardInputRef.current?.click()}>
                  <Upload size={14} />
                  <span>Click here to upload</span>
                </div>
              )}
              <p className="rc-field-hint">Or use Google Drive Auto in the automation panel above</p>
            </div>
          </div>

          {/* Row 2: Agreement fields - 6 columns */}
          <div className="rc-form-grid-6">
            <div className="rc-field">
              <label>Agreement Start Date</label>
              <input
                type="date"
                value={agreement.startDate}
                onChange={(e) => setAgreement({ ...agreement, startDate: e.target.value })}
                disabled={isFieldDisabled}
                placeholder="Select date"
              />
            </div>
            <div className="rc-field">
              <label>Agreement End Date</label>
              <input
                type="date"
                value={agreement.endDate}
                onChange={(e) => setAgreement({ ...agreement, endDate: e.target.value })}
                disabled={isFieldDisabled}
                placeholder="Select date"
              />
            </div>
            <div className="rc-field">
              <label>Merchant Size</label>
              <select
                value={agreement.merchantSize}
                onChange={(e) => setAgreement({ ...agreement, merchantSize: e.target.value })}
                disabled={isFieldDisabled}
              >
                <option value="">Select value</option>
                {merchantSizeOptions.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>
            <div className="rc-field">
              <label>Merchant Type</label>
              <select
                value={agreement.merchantType}
                onChange={(e) => setAgreement({ ...agreement, merchantType: e.target.value })}
                disabled={isFieldDisabled}
              >
                <option value="">Select value</option>
                {merchantTypeOptions.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>
            <div className="rc-field">
              <label>Agency</label>
              <select
                value={agreement.agency}
                onChange={(e) => setAgreement({ ...agreement, agency: e.target.value })}
                disabled={isFieldDisabled}
              >
                <option value="">Select value</option>
                {agencyOptions.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 3: Agency Commission + Purchased Products (chip dropdown) */}
          <div className="rc-form-row-2">
            <div className="rc-field">
              <label>Agency Commission %</label>
              <input
                type="text"
                placeholder="Enter value"
                value={agreement.agencyCommission}
                onChange={(e) => setAgreement({ ...agreement, agencyCommission: e.target.value })}
                disabled={isFieldDisabled}
              />
            </div>
            <div className="rc-field">
              <label>Purchased Products</label>
              <ChipSelect
                options={productOptions}
                selected={agreement.purchasedProducts}
                onChange={(val) => setAgreement({ ...agreement, purchasedProducts: val })}
                disabled={isFieldDisabled}
                placeholder="Select value"
              />
            </div>
          </div>

          {agreementEditMode && (
            <div className="rc-save-row">
              <button className="rc-save-btn" onClick={onSaveAgreement}>Save</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
