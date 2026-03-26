import { X } from 'lucide-react'

export default function Toast({ toasts, setToasts }) {
  if (toasts.length === 0) return null

  return (
    <div className="rc-toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`rc-toast ${t.type}`}>
          <span>{t.message}</span>
          <button className="rc-toast-close" onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}>
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
