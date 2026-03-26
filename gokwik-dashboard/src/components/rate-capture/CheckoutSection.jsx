import { ChevronDown, ChevronUp, Pencil } from 'lucide-react'
import TagSelect from '../common/TagSelect'
import CommissionForm from './CommissionForm'
import CommissionTable from './CommissionTable'
import { paymentTabs, pricingTypes } from '../../constants/rateCapture'

export default function CheckoutSection({
  checkout,
  setCheckout,
  tabData,
  activePaymentTab,
  setActivePaymentTab,
  activeTabData,
  checkoutOpen,
  setCheckoutOpen,
  checkoutSaved,
  checkoutEditMode,
  isCheckoutDisabled,
  getCheckoutStatus,
  onEditCheckout,
  onSaveCheckout,
  updateTabField,
  updateCommRow,
  onAddCommission,
  onDeleteCommission,
  onAddMore,
  commValueRef,
  editingCommId,
  editingValues,
  setEditingValues,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  setEditingCommId,
}) {
  return (
    <div className="rc-section">
      <div className="rc-section-header" onClick={() => setCheckoutOpen(!checkoutOpen)}>
        {checkoutOpen ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        <h3>Checkout</h3>
        <span className={`rc-status-badge ${getCheckoutStatus().className}`}>
          {getCheckoutStatus().label}
        </span>
        <div className="rc-section-header-right">
          {checkoutSaved && !checkoutEditMode && (
            <button className="rc-edit-btn" onClick={onEditCheckout}>
              <Pencil size={14} /> Edit
            </button>
          )}
        </div>
      </div>
      {checkoutOpen && (
        <div className="rc-section-body">
          {/* Pricing row 1 (matches original exactly) */}
          <div className="rc-pricing-row">
            <div className="rc-field rc-field-sm">
              <label>Pricing Start Date:</label>
              <input
                type="date"
                value={checkout.pricingStartDate}
                onChange={(e) => setCheckout({ ...checkout, pricingStartDate: e.target.value })}
                disabled={isCheckoutDisabled}
              />
            </div>
            <div className="rc-field rc-field-sm">
              <label>Pricing End Date:</label>
              <input
                type="date"
                value={checkout.pricingEndDate}
                onChange={(e) => setCheckout({ ...checkout, pricingEndDate: e.target.value })}
                disabled={isCheckoutDisabled}
              />
            </div>
            <div className="rc-field rc-field-sm">
              <label>Minimum Guarantee (&#8377;):</label>
              <select
                value={checkout.frequency}
                onChange={(e) => setCheckout({ ...checkout, frequency: e.target.value })}
                disabled={isCheckoutDisabled}
              >
                <option>Monthly</option>
                <option>Quarterly</option>
                <option>Yearly</option>
              </select>
            </div>
            <div className="rc-field rc-field-sm">
              <label>&nbsp;</label>
              <input
                type="number"
                value={checkout.minimumGuarantee}
                onChange={(e) => setCheckout({ ...checkout, minimumGuarantee: e.target.value })}
                disabled={isCheckoutDisabled}
              />
            </div>
          </div>

          {/* Pricing row 2 */}
          <div className="rc-pricing-row">
            <div className="rc-field rc-field-sm">
              <label>Platform Fee (&#8377;):</label>
              <select
                value={checkout.platformFeeFreq}
                onChange={(e) => setCheckout({ ...checkout, platformFeeFreq: e.target.value })}
                disabled={isCheckoutDisabled}
              >
                <option>Quarterly</option>
                <option>Monthly</option>
                <option>Yearly</option>
              </select>
            </div>
            <div className="rc-field rc-field-sm">
              <label>&nbsp;</label>
              <input
                type="number"
                value={checkout.platformFee}
                onChange={(e) => setCheckout({ ...checkout, platformFee: e.target.value })}
                disabled={isCheckoutDisabled}
              />
            </div>
          </div>

          {/* Payment method tabs */}
          <div className="rc-tabs">
            {paymentTabs.map((tab) => (
              <button
                key={tab}
                className={`rc-tab ${activePaymentTab === tab ? 'active' : ''}`}
                onClick={() => { setActivePaymentTab(tab); setEditingCommId(null) }}
              >
                {tab}
                {tabData[tab].commissions.length > 0 && (
                  <span className="rc-tab-badge">{tabData[tab].commissions.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Pricing Type */}
          <div className="rc-pricing-type-row">
            <label>Pricing Type:</label>
            <TagSelect
              options={pricingTypes}
              value={activeTabData.pricingType}
              onChange={(val) => updateTabField('pricingType', val)}
              disabled={isCheckoutDisabled}
            />
          </div>

          {/* Commission add row */}
          {checkoutEditMode && (
            <CommissionForm
              activePaymentTab={activePaymentTab}
              activeTabData={activeTabData}
              updateCommRow={updateCommRow}
              onAddCommission={onAddCommission}
              commValueRef={commValueRef}
            />
          )}

          {/* Commission table */}
          <CommissionTable
            activePaymentTab={activePaymentTab}
            commissions={activeTabData.commissions}
            checkoutEditMode={checkoutEditMode}
            editingCommId={editingCommId}
            editingValues={editingValues}
            setEditingValues={setEditingValues}
            onStartEdit={onStartEdit}
            onSaveEdit={onSaveEdit}
            onCancelEdit={onCancelEdit}
            onDeleteCommission={onDeleteCommission}
          />

          {/* Bottom actions */}
          <div className="rc-bottom-actions">
            {checkoutEditMode ? (
              <>
                <button className="rc-add-more-btn" onClick={onAddMore}>+ Add more</button>
                <button className="rc-save-btn" onClick={onSaveCheckout}>Save</button>
              </>
            ) : (
              <div />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
