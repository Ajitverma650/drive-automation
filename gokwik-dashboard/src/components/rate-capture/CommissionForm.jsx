import TagSelect from '../common/TagSelect'
import { commissionTypes, tabMethodLabel, getMethodsForTab } from '../../constants/rateCapture'

export default function CommissionForm({
  activePaymentTab,
  activeTabData,
  updateCommRow,
  onAddCommission,
  commValueRef,
}) {
  return (
    <div className="rc-commission-add">
      <div className="rc-field rc-field-sm">
        <label>{tabMethodLabel[activePaymentTab] || 'Methods'}</label>
        <TagSelect
          options={getMethodsForTab(activePaymentTab)}
          value={activeTabData.commRow.method}
          onChange={(val) => updateCommRow('method', val)}
        />
      </div>
      <div className="rc-field rc-field-sm">
        <label>Commission Type</label>
        <TagSelect
          options={commissionTypes}
          value={activeTabData.commRow.commissionType}
          onChange={(val) => updateCommRow('commissionType', val)}
        />
      </div>
      <div className="rc-field rc-field-sm">
        <label>Value</label>
        <input
          ref={commValueRef}
          type="text"
          placeholder="Enter value"
          value={activeTabData.commRow.value}
          onChange={(e) => updateCommRow('value', e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') onAddCommission() }}
        />
      </div>
      <button className="rc-add-btn" onClick={onAddCommission}>Add</button>
    </div>
  )
}
