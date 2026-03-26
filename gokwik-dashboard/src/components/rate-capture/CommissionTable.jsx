import { Trash2, Mail, Pencil, Check, X } from 'lucide-react'
import TagSelect from '../common/TagSelect'
import { commissionTypes, getMethodsForTab } from '../../constants/rateCapture'

export default function CommissionTable({
  activePaymentTab,
  commissions,
  checkoutEditMode,
  editingCommId,
  editingValues,
  setEditingValues,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onDeleteCommission,
}) {
  return (
    <div className="rc-commission-table">
      <table>
        <thead>
          <tr>
            <th>Methods</th>
            <th>Commission type</th>
            <th>Value</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {commissions.length === 0 ? (
            <tr>
              <td colSpan={4}>
                <div className="rc-no-data">
                  <Mail size={40} color="#b2bec3" />
                  <p>No data</p>
                </div>
              </td>
            </tr>
          ) : (
            commissions.map((c) => (
              <tr key={c.id}>
                {editingCommId === c.id ? (
                  <>
                    <td>
                      <TagSelect
                        options={getMethodsForTab(activePaymentTab)}
                        value={editingValues.method}
                        onChange={(val) => setEditingValues({ ...editingValues, method: val })}
                      />
                    </td>
                    <td>
                      <TagSelect
                        options={commissionTypes}
                        value={editingValues.commissionType}
                        onChange={(val) => setEditingValues({ ...editingValues, commissionType: val })}
                      />
                    </td>
                    <td>
                      <input
                        className="rc-inline-edit"
                        type="text"
                        value={editingValues.value}
                        onChange={(e) => setEditingValues({ ...editingValues, value: e.target.value })}
                        onKeyDown={(e) => { if (e.key === 'Enter') onSaveEdit(c.id); if (e.key === 'Escape') onCancelEdit() }}
                        autoFocus
                      />
                    </td>
                    <td>
                      <div className="rc-action-btns">
                        <button className="rc-save-inline-btn" onClick={() => onSaveEdit(c.id)}>
                          <Check size={16} />
                        </button>
                        <button className="rc-cancel-inline-btn" onClick={onCancelEdit}>
                          <X size={16} />
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{c.method}</td>
                    <td>{c.commissionType}</td>
                    <td>{c.value}</td>
                    <td>
                      <div className="rc-action-btns">
                        {checkoutEditMode && (
                          <button className="rc-edit-inline-btn" onClick={() => onStartEdit(c)}>
                            <Pencil size={14} />
                          </button>
                        )}
                        {checkoutEditMode && (
                          <button className="rc-delete-btn" onClick={() => onDeleteCommission(c.id)}>
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
