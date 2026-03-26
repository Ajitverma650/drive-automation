import { useState, useRef, useEffect } from 'react'
import { ChevronDown, X } from 'lucide-react'

export default function ChipSelect({ options, selected, onChange, disabled, placeholder = 'Select value' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const toggle = (val) => {
    if (disabled) return
    if (selected.includes(val)) {
      onChange(selected.filter((v) => v !== val))
    } else {
      onChange([...selected, val])
    }
  }

  const remove = (val, e) => {
    e.stopPropagation()
    if (disabled) return
    onChange(selected.filter((v) => v !== val))
  }

  return (
    <div className={`rc-chipselect ${disabled ? 'disabled' : ''}`} ref={ref}>
      <div className="rc-chipselect-control" onClick={() => !disabled && setOpen(!open)}>
        {selected.length === 0 ? (
          <span className="rc-chipselect-placeholder">{placeholder}</span>
        ) : (
          <div className="rc-chipselect-chips">
            {selected.map((v) => (
              <span key={v} className="rc-chipselect-chip">
                {v}
                {!disabled && (
                  <button className="rc-chipselect-chip-x" onClick={(e) => remove(v, e)}>
                    <X size={12} />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
        <ChevronDown size={16} className={`rc-chipselect-arrow ${open ? 'open' : ''}`} />
      </div>
      {open && (
        <div className="rc-chipselect-dropdown">
          {options.map((opt) => (
            <div
              key={opt}
              className={`rc-chipselect-option ${selected.includes(opt) ? 'selected' : ''}`}
              onClick={() => toggle(opt)}
            >
              <span className="rc-chipselect-check">{selected.includes(opt) ? '✓' : ''}</span>
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
