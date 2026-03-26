import { useState } from 'react'
import { ChevronDown, ChevronUp, Upload, Pencil, X, Search, CloudDownload, Loader } from 'lucide-react'
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
  onDriveSelect,
}) {
  const [driveSearchQuery, setDriveSearchQuery] = useState('')
  const [driveResults, setDriveResults] = useState(null)
  const [driveSearching, setDriveSearching] = useState(false)
  const [driveMode, setDriveMode] = useState(false) // false=upload, true=drive

  const handleDriveSearch = async () => {
    if (!driveSearchQuery.trim()) return
    setDriveSearching(true)
    setDriveResults(null)
    try {
      const res = await fetch(`http://localhost:8000/api/drive/search?merchant=${encodeURIComponent(driveSearchQuery)}`)
      const data = await res.json()
      setDriveResults(data)
    } catch (err) {
      setDriveResults({ success: false, files: [], message: err.message })
    }
    setDriveSearching(false)
  }

  const handleDriveSelect = (file) => {
    setDriveResults(null)
    setDriveSearchQuery('')
    if (onDriveSelect) onDriveSelect(file)
  }
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
            <div className="rc-field rc-rate-card-field">
              <div className="rc-rate-label-row">
                <label>Rate Card PDF</label>
                <div className="rc-rate-toggle">
                  <button
                    className={`rc-toggle-btn ${!driveMode ? 'active' : ''}`}
                    onClick={() => setDriveMode(false)}
                  >
                    <Upload size={12} /> Upload
                  </button>
                  <button
                    className={`rc-toggle-btn ${driveMode ? 'active' : ''}`}
                    onClick={() => setDriveMode(true)}
                  >
                    <CloudDownload size={12} /> Google Drive
                  </button>
                </div>
              </div>

              {!driveMode ? (
                /* Upload mode */
                <>
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
                    <div className="rc-file-display rc-file-rate">
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
                </>
              ) : (
                /* Google Drive mode */
                <>
                  {rateCardName ? (
                    <div className="rc-file-display rc-file-rate rc-file-drive">
                      <CloudDownload size={14} style={{ color: '#4285f4' }} />
                      <span className="rc-file-name" title={rateCardName}>
                        {rateCardName}
                      </span>
                      <button className="rc-file-remove" onClick={onRemoveRateCard}>
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    <div className="rc-drive-search">
                      <div className="rc-drive-input-row">
                        <input
                          type="text"
                          placeholder="Search merchant name in Drive..."
                          value={driveSearchQuery}
                          onChange={(e) => setDriveSearchQuery(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleDriveSearch()}
                        />
                        <button
                          className="rc-drive-search-btn"
                          onClick={handleDriveSearch}
                          disabled={driveSearching || !driveSearchQuery.trim()}
                        >
                          {driveSearching ? <Loader size={14} className="ap-spin" /> : <Search size={14} />}
                        </button>
                      </div>

                      {driveResults && (
                        <div className="rc-drive-results">
                          {driveResults.files.length === 0 ? (
                            <div className="rc-drive-empty">{driveResults.message}</div>
                          ) : (
                            driveResults.files.map((f) => (
                              <div
                                key={f.id}
                                className="rc-drive-file"
                                onClick={() => handleDriveSelect(f)}
                              >
                                <div className="rc-drive-file-name">{f.name}</div>
                                <div className="rc-drive-file-meta">{f.size} &middot; {new Date(f.modified).toLocaleDateString()}</div>
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
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
