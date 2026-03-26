import { useState, useRef, useEffect } from 'react'
import { ChevronDown, X } from 'lucide-react'

export default function TagSelect({ options, value, onChange, disabled }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className={`rc-tagselect ${disabled ? 'disabled' : ''}`} ref={ref}>
      <div className="rc-tagselect-control" onClick={() => !disabled && setOpen(!open)}>
        {value ? (
          <span className="rc-tagselect-tag">
            {value}
            {!disabled && (
              <button className="rc-tagselect-tag-x" onClick={(e) => { e.stopPropagation(); onChange('') }}>
                <X size={11} />
              </button>
            )}
          </span>
        ) : (
          <span className="rc-tagselect-placeholder">Select</span>
        )}
        <ChevronDown size={14} className={`rc-chipselect-arrow ${open ? 'open' : ''}`} />
      </div>
      {open && (
        <div className="rc-chipselect-dropdown">
          {options.map((opt) => (
            <div
              key={opt}
              className={`rc-chipselect-option ${value === opt ? 'selected' : ''}`}
              onClick={() => { onChange(opt); setOpen(false) }}
            >
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
