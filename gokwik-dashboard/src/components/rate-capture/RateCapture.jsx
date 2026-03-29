import { useState, useRef, useCallback } from 'react'
import Toast from '../common/Toast'
import MerchantSelector from './MerchantSelector'
import AgreementSection from './AgreementSection'
import CheckoutSection from './CheckoutSection'
import AutomationPanel from './AutomationPanel'
import {
  dummyMerchants,
  buildEmptyCheckout,
  buildInitialTabData,
  getMethodsForTab,
} from '../../constants/rateCapture'

export default function RateCapture({ onBack }) {
  const [activeMerchant, setActiveMerchant] = useState(dummyMerchants[0].id)
  const [agreementOpen, setAgreementOpen] = useState(true)
  const [checkoutOpen, setCheckoutOpen] = useState(true)
  const [activePaymentTab, setActivePaymentTab] = useState('EMI')
  const fileInputRef = useRef(null)
  const commValueRef = useRef(null)

  // Toast notifications
  const [toasts, setToasts] = useState([])
  const showToast = useCallback((message, type = 'success') => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3000)
  }, [])

  // Per-merchant state store
  const [merchantStore, setMerchantStore] = useState(() => {
    const store = {}
    dummyMerchants.forEach((m) => {
      store[m.id] = {
        agreement: { ...m.agreement },
        agreementSaved: m.agreementSaved,
        agreementEditMode: !m.agreementSaved,
        checkout: m.agreementSaved
          ? { ...buildEmptyCheckout(), pricingStartDate: m.agreement.startDate, pricingEndDate: m.agreement.endDate }
          : buildEmptyCheckout(),
        checkoutSaved: false,
        checkoutEditMode: true,
        confirmed: false,
        tabData: buildInitialTabData(),
      }
    })
    return store
  })

  const current = merchantStore[activeMerchant]
  const agreement = current.agreement
  const agreementSaved = current.agreementSaved
  const agreementEditMode = current.agreementEditMode
  const checkout = current.checkout
  const checkoutSaved = current.checkoutSaved
  const checkoutEditMode = current.checkoutEditMode
  const confirmed = current.confirmed
  const tabData = current.tabData

  const updateStore = (field, value) => {
    setMerchantStore((prev) => ({
      ...prev,
      [activeMerchant]: { ...prev[activeMerchant], [field]: value },
    }))
  }

  const setAgreement = (valOrFn) => {
    setMerchantStore((prev) => {
      const old = prev[activeMerchant].agreement
      const next = typeof valOrFn === 'function' ? valOrFn(old) : valOrFn
      return { ...prev, [activeMerchant]: { ...prev[activeMerchant], agreement: next } }
    })
  }

  const setCheckout = (valOrFn) => {
    setMerchantStore((prev) => {
      const old = prev[activeMerchant].checkout
      const next = typeof valOrFn === 'function' ? valOrFn(old) : valOrFn
      return { ...prev, [activeMerchant]: { ...prev[activeMerchant], checkout: next } }
    })
  }

  const setTabData = (valOrFn) => {
    setMerchantStore((prev) => {
      const old = prev[activeMerchant].tabData
      const next = typeof valOrFn === 'function' ? valOrFn(old) : valOrFn
      return { ...prev, [activeMerchant]: { ...prev[activeMerchant], tabData: next } }
    })
  }

  const [showAutomation, setShowAutomation] = useState(false)
  const [autoRunTriggered, setAutoRunTriggered] = useState(false)
  const rateCardInputRef = useRef(null)
  const [rateCardFile, setRateCardFile] = useState(null)
  const [rateCardName, setRateCardName] = useState('')
  const [driveFileId, setDriveFileId] = useState(null) // Google Drive file ID

  // Inline editing state
  const [editingCommId, setEditingCommId] = useState(null)
  const [editingValues, setEditingValues] = useState({})

  const checkAutoTrigger = (agFile, rcFile) => {
    if (agFile && rcFile && !autoRunTriggered) {
      setShowAutomation(true)
      setAutoRunTriggered(true)
    }
  }

  // Handle Drive file selection
  const handleDriveSelect = (driveFile) => {
    setDriveFileId(driveFile.id)
    setRateCardName(driveFile.name)
    setRateCardFile(null) // clear local file — using Drive instead
    // Auto-trigger if agreement is also uploaded
    if (agreement.merchantAgreementFile && !autoRunTriggered) {
      setShowAutomation(true)
      setAutoRunTriggered(true)
    }
  }

  // Phase 1 auto-fill
  const handlePhase1Complete = (data) => {
    const ag = data.agreement
    const tabs = data.tabs

    // Build new tab data
    const newTabData = buildInitialTabData()
    for (const [tabName, entries] of Object.entries(tabs)) {
      if (newTabData[tabName]) {
        newTabData[tabName].commissions = entries.map((e, i) => ({
          id: Date.now() + i + Math.random(),
          method: e.method,
          commissionType: 'Percentage',
          value: String(e.rate),
          originalMode: e.original_mode || '',
        }))
      }
    }

    // Update everything in a SINGLE state update to avoid stale state
    setMerchantStore((prev) => {
      const oldMerchant = prev[activeMerchant]
      return {
        ...prev,
        [activeMerchant]: {
          ...oldMerchant,
          agreement: {
            ...oldMerchant.agreement,
            merchantAgreementFile: oldMerchant.agreement.merchantAgreementFile || { name: ag.file_name },
            merchantAgreementName: ag.file_name,
            startDate: ag.start_date || '',
            endDate: ag.end_date || '',
            merchantSize: ag.merchant_size || 'Long Tail',
            merchantType: ag.merchant_type || 'D2C',
            agency: ag.agency || '',
            agencyCommission: ag.agency_commission || '',
            purchasedProducts: ag.purchased_products || ['Checkout'],
          },
          agreementSaved: true,
          agreementEditMode: false,
          checkout: {
            ...oldMerchant.checkout,
            pricingStartDate: ag.start_date || oldMerchant.checkout.pricingStartDate,
            pricingEndDate: ag.end_date || oldMerchant.checkout.pricingEndDate,
          },
          tabData: newTabData,
        },
      }
    })
  }

  const getDashboardRates = () => {
    const rates = {}
    for (const [tabName, data] of Object.entries(tabData)) {
      if (data.commissions.length > 0) {
        rates[tabName] = data.commissions.map((c) => ({
          method: c.method,
          rate: parseFloat(c.value) || 0,
          originalMode: c.originalMode || '',
        }))
      }
    }
    return rates
  }

  const handlePhase2Complete = (data) => {
    if (data.all_match) {
      showToast('All rates match! Verification successful.', 'success')
    }
  }

  const handleMerchantSwitch = (merchantId) => {
    setActiveMerchant(merchantId)
    setActivePaymentTab('EMI')
    setAgreementOpen(true)
    setCheckoutOpen(true)
    setAutoRunTriggered(false)
    setEditingCommId(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const activeTabData = tabData[activePaymentTab]

  const updateTabField = (field, value) => {
    setTabData((prev) => ({
      ...prev,
      [activePaymentTab]: { ...prev[activePaymentTab], [field]: value },
    }))
  }

  const updateCommRow = (field, value) => {
    setTabData((prev) => ({
      ...prev,
      [activePaymentTab]: {
        ...prev[activePaymentTab],
        commRow: { ...prev[activePaymentTab].commRow, [field]: value },
      },
    }))
  }

  const handleFileUpload = (e, type) => {
    const file = e.target.files[0]
    if (!file) return
    if (type === 'rateCard') {
      setRateCardFile(file)
      setRateCardName(file.name)
      checkAutoTrigger(agreement.merchantAgreementFile, file)
    } else {
      setAgreement((prev) => ({
        ...prev,
        merchantAgreementFile: file,
        merchantAgreementName: file.name,
      }))
      checkAutoTrigger(file, rateCardFile)
    }
  }

  const handleRemoveFile = () => {
    setAgreement((prev) => ({
      ...prev,
      merchantAgreementFile: null,
      merchantAgreementName: '',
    }))
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleRemoveRateCard = () => {
    setRateCardFile(null)
    setRateCardName('')
    if (rateCardInputRef.current) rateCardInputRef.current.value = ''
  }

  // Save Agreement
  const handleSaveAgreement = () => {
    if (!agreement.merchantAgreementFile) {
      showToast('Please upload a Merchant Agreement file.', 'error')
      return
    }
    if (!agreement.startDate) {
      showToast('Please enter Agreement Start Date.', 'error')
      return
    }
    if (!agreement.endDate) {
      showToast('Please enter Agreement End Date.', 'error')
      return
    }
    if (agreement.endDate <= agreement.startDate) {
      showToast('End Date must be after Start Date.', 'error')
      return
    }
    if (!agreement.merchantSize) {
      showToast('Please select Merchant Size.', 'error')
      return
    }
    if (!agreement.merchantType) {
      showToast('Please select Merchant Type.', 'error')
      return
    }
    if (agreement.purchasedProducts.length === 0) {
      showToast('Please select at least one Purchased Product.', 'error')
      return
    }

    updateStore('agreementSaved', true)
    updateStore('agreementEditMode', false)

    setCheckout((prev) => ({
      ...prev,
      pricingStartDate: prev.pricingStartDate || agreement.startDate,
      pricingEndDate: prev.pricingEndDate || agreement.endDate,
    }))

    showToast('Agreement details saved successfully!', 'success')
  }

  // Save Checkout
  const handleSaveCheckout = () => {
    if (!checkout.pricingStartDate) {
      showToast('Please enter Pricing Start Date.', 'error')
      return
    }
    if (!checkout.pricingEndDate) {
      showToast('Please enter Pricing End Date.', 'error')
      return
    }
    const hasCommissions = Object.values(tabData).some((t) => t.commissions.length > 0)
    if (!hasCommissions) {
      showToast('Please add at least one commission entry.', 'error')
      return
    }

    updateStore('checkoutSaved', true)
    updateStore('checkoutEditMode', false)
    showToast('Checkout pricing saved successfully!', 'success')
  }

  // Confirm
  const handleConfirm = () => {
    if (!agreementSaved) {
      showToast('Please save Agreement Details first.', 'error')
      return
    }
    const hasCommissions = Object.values(tabData).some((t) => t.commissions.length > 0)
    if (!hasCommissions) {
      showToast('Please add rate entries before confirming.', 'error')
      return
    }
    if (!checkoutSaved) {
      updateStore('checkoutSaved', true)
      updateStore('checkoutEditMode', false)
    }
    updateStore('confirmed', true)
    updateStore('agreementEditMode', false)
    updateStore('checkoutEditMode', false)
    showToast('Agreement confirmed successfully!', 'success')
  }

  // Edit mode toggles
  const handleEditAgreement = (e) => {
    e.stopPropagation()
    updateStore('agreementEditMode', true)
    if (confirmed) {
      updateStore('confirmed', false)
      showToast('Confirmation reset. Please re-confirm after editing.', 'warning')
    }
  }

  const handleEditCheckout = (e) => {
    e.stopPropagation()
    updateStore('checkoutEditMode', true)
    updateStore('checkoutSaved', false)
    if (confirmed) {
      updateStore('confirmed', false)
      showToast('Confirmation reset. Please re-confirm after editing.', 'warning')
    }
  }

  const handleAddMore = () => {
    if (commValueRef.current) commValueRef.current.focus()
  }

  const handleAddCommission = () => {
    if (!activeTabData.commRow.method) {
      showToast('Please select a method.', 'error')
      return
    }
    if (!activeTabData.commRow.value) {
      showToast('Please enter a commission value.', 'error')
      return
    }
    setTabData((prev) => ({
      ...prev,
      [activePaymentTab]: {
        ...prev[activePaymentTab],
        commissions: [
          ...prev[activePaymentTab].commissions,
          { ...prev[activePaymentTab].commRow, id: Date.now() },
        ],
        commRow: { method: getMethodsForTab(activePaymentTab)[0], commissionType: 'Percentage', value: '' },
      },
    }))
    showToast(`Commission added to ${activePaymentTab}.`, 'success')
  }

  const handleDeleteCommission = (id) => {
    setTabData((prev) => ({
      ...prev,
      [activePaymentTab]: {
        ...prev[activePaymentTab],
        commissions: prev[activePaymentTab].commissions.filter((c) => c.id !== id),
      },
    }))
    if (editingCommId === id) setEditingCommId(null)
  }

  // Inline editing
  const handleStartEdit = (comm) => {
    setEditingCommId(comm.id)
    setEditingValues({ method: comm.method, commissionType: comm.commissionType, value: comm.value })
  }

  const handleSaveEdit = (id) => {
    if (!editingValues.value) {
      showToast('Value cannot be empty.', 'error')
      return
    }
    setTabData((prev) => ({
      ...prev,
      [activePaymentTab]: {
        ...prev[activePaymentTab],
        commissions: prev[activePaymentTab].commissions.map((c) =>
          c.id === id ? { ...c, ...editingValues } : c
        ),
      },
    }))
    setEditingCommId(null)
    setEditingValues({})
  }

  const handleCancelEdit = () => {
    setEditingCommId(null)
    setEditingValues({})
  }

  // Status helpers
  const getAgreementStatus = () => {
    if (confirmed) return { label: 'Confirmed', className: 'confirmed' }
    if (agreementSaved) return { label: 'Saved', className: 'saved' }
    return { label: 'Draft', className: 'draft' }
  }

  const getCheckoutStatus = () => {
    if (confirmed) return { label: 'Confirmed', className: 'confirmed' }
    if (checkoutSaved) return { label: 'Saved', className: 'saved' }
    return { label: 'Draft', className: 'draft' }
  }

  const isFieldDisabled = !agreementEditMode
  const isCheckoutDisabled = !checkoutEditMode

  return (
    <div className="rate-capture">
      <Toast toasts={toasts} setToasts={setToasts} />

      <MerchantSelector
        activeMerchant={activeMerchant}
        onMerchantSwitch={handleMerchantSwitch}
        onBack={onBack}
        confirmed={confirmed}
        showAutomation={showAutomation}
        onToggleAutomation={() => setShowAutomation(!showAutomation)}
        onConfirm={handleConfirm}
      />

      {/* Automation Panel */}
      {showAutomation && (
        <AutomationPanel
          onPhase1Complete={handlePhase1Complete}
          onPhase2Complete={handlePhase2Complete}
          onFullAutoComplete={(data) => { if (data.all_match) { /* verified */ } }}
          onConfirm={handleConfirm}
          dashboardRates={getDashboardRates()}
          merchantName={dummyMerchants.find((m) => m.id === activeMerchant)?.name || ''}
          agreementFile={agreement.merchantAgreementFile}
          rateCardFile={rateCardFile}
          driveFileId={driveFileId}
          autoRun={autoRunTriggered}
        />
      )}

      {/* ─── Verification Report (replaces form — shows what was extracted vs filled) ─── */}
      {agreementSaved && (
        <div className="rc-verify-report" style={{ background: '#fff', borderRadius: 12, padding: 24, marginTop: 16, border: '1px solid #e5e7eb' }}>
          {/* Agreement Summary */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <span style={{ fontSize: 20 }}>&#128196;</span>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Extraction & Fill Report</h3>
            <span style={{ marginLeft: 'auto', padding: '2px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
              background: confirmed ? '#dcfce7' : '#fef3c7', color: confirmed ? '#166534' : '#92400e' }}>
              {confirmed ? 'CONFIRMED' : 'DRAFT'}
            </span>
          </div>

          {/* Agreement Details Card */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 20, padding: 16, background: '#f9fafb', borderRadius: 8 }}>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Merchant</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{agreement.merchantAgreementName || 'N/A'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Start Date</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{agreement.startDate || 'N/A'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>End Date</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{agreement.endDate || 'N/A'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Size</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{agreement.merchantSize || 'N/A'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Type</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{agreement.merchantType || 'N/A'}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Products</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{(agreement.purchasedProducts || []).join(', ') || 'N/A'}</div>
            </div>
          </div>

          {/* Rate Summary by Tab */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 18 }}>&#128202;</span>
            <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Extracted Rates by Payment Tab</h4>
            <span style={{ marginLeft: 'auto', fontSize: 13, color: '#6b7280' }}>
              {Object.values(tabData).reduce((sum, t) => sum + t.commissions.length, 0)} total rates across {Object.values(tabData).filter(t => t.commissions.length > 0).length} tabs
            </span>
          </div>

          {/* Tab Pills */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
            {Object.entries(tabData).filter(([, t]) => t.commissions.length > 0).map(([tabName, t]) => (
              <button key={tabName} onClick={() => setActivePaymentTab(tabName)}
                style={{ padding: '4px 12px', borderRadius: 16, border: activePaymentTab === tabName ? '2px solid #7c3aed' : '1px solid #d1d5db',
                  background: activePaymentTab === tabName ? '#ede9fe' : '#fff', color: activePaymentTab === tabName ? '#7c3aed' : '#374151',
                  fontSize: 13, fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                {tabName}
                <span style={{ background: activePaymentTab === tabName ? '#7c3aed' : '#9ca3af', color: '#fff', borderRadius: 10, padding: '0 6px', fontSize: 11, fontWeight: 700 }}>
                  {t.commissions.length}
                </span>
              </button>
            ))}
          </div>

          {/* Active Tab Rate Table */}
          {tabData[activePaymentTab]?.commissions.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f3f4f6' }}>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>Method</th>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>PDF Mode (Original)</th>
                  <th style={{ textAlign: 'right', padding: '8px 12px', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>Rate (%)</th>
                  <th style={{ textAlign: 'center', padding: '8px 12px', fontWeight: 600, color: '#374151', borderBottom: '2px solid #e5e7eb' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {tabData[activePaymentTab].commissions.map((c, i) => (
                  <tr key={c.id || i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 12px', fontWeight: 500 }}>{c.method}</td>
                    <td style={{ padding: '8px 12px', color: '#6b7280', fontStyle: 'italic' }}>{c.originalMode || c.method}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, fontFamily: 'monospace', fontSize: 14 }}>{c.value}%</td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#22c55e' }}></span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ padding: 20, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
              No rates in {activePaymentTab} tab. Run automation to extract rates.
            </div>
          )}

          {/* All Tabs Overview Table */}
          {Object.values(tabData).some(t => t.commissions.length > 0) && (
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span style={{ fontSize: 18 }}>&#128209;</span>
                <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Complete Rate Summary</h4>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: '#f3f4f6' }}>
                    <th style={{ textAlign: 'left', padding: '6px 10px', fontWeight: 600, borderBottom: '2px solid #e5e7eb' }}>Tab</th>
                    <th style={{ textAlign: 'left', padding: '6px 10px', fontWeight: 600, borderBottom: '2px solid #e5e7eb' }}>Method</th>
                    <th style={{ textAlign: 'right', padding: '6px 10px', fontWeight: 600, borderBottom: '2px solid #e5e7eb' }}>Rate</th>
                    <th style={{ textAlign: 'left', padding: '6px 10px', fontWeight: 600, borderBottom: '2px solid #e5e7eb' }}>PDF Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(tabData).flatMap(([tabName, t]) =>
                    t.commissions.map((c, i) => (
                      <tr key={`${tabName}-${i}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '5px 10px' }}>
                          <span style={{ background: '#ede9fe', color: '#7c3aed', padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 }}>{tabName}</span>
                        </td>
                        <td style={{ padding: '5px 10px', fontWeight: 500 }}>{c.method}</td>
                        <td style={{ padding: '5px 10px', textAlign: 'right', fontWeight: 700, fontFamily: 'monospace' }}>{c.value}%</td>
                        <td style={{ padding: '5px 10px', color: '#6b7280', fontStyle: 'italic', fontSize: 11 }}>{c.originalMode || '-'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
