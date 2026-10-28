import { useEffect, useRef } from 'react'
import { AlertCircle, X } from 'lucide-react'

/**
 * Clean, accessible confirmation dialog for destructive actions (like deleting a meeting)
 * or inline text input (like renaming a meeting).
 */
export default function ConfirmationModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDanger = false,
  inputValue = null,
  onInputChange = null,
  inputPlaceholder = '',
  onConfirm,
  onClose,
}) {
  const inputRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose()
      }
      window.addEventListener('keydown', handleKeyDown)
      if (inputValue !== null && inputRef.current) {
        inputRef.current.focus()
        inputRef.current.select()
      }
      return () => window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, inputValue, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-xs transition-opacity"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md bg-white rounded-xl border border-gray-200 shadow-xl p-6 transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 rounded-md p-1 hover:bg-gray-100 transition-colors"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-start gap-3 mb-3">
          {isDanger && (
            <div className="shrink-0 w-8 h-8 rounded-full bg-red-50 border border-red-100 flex items-center justify-center text-red-600">
              <AlertCircle className="w-4 h-4" />
            </div>
          )}
          <div>
            <h3 className="text-base font-semibold text-gray-900 leading-snug">
              {title}
            </h3>
            {message && (
              <p className="mt-1 text-sm text-gray-500 leading-relaxed">
                {message}
              </p>
            )}
          </div>
        </div>

        {/* Optional Input (for Renaming) */}
        {inputValue !== null && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              if (inputValue.trim()) onConfirm()
            }}
            className="mt-4 mb-2"
          >
            <label htmlFor="modal-input" className="sr-only">
              {inputPlaceholder || title}
            </label>
            <input
              id="modal-input"
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => onInputChange && onInputChange(e.target.value)}
              placeholder={inputPlaceholder}
              className="w-full px-3.5 py-2 text-sm bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 transition-colors"
            />
          </form>
        )}

        {/* Modal Actions */}
        <div className="mt-6 flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 active:bg-gray-100 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={inputValue !== null && !inputValue.trim()}
            className={`px-4 py-2 text-sm font-medium rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              isDanger
                ? 'bg-red-600 hover:bg-red-700 active:bg-red-800'
                : 'bg-gray-900 hover:bg-black active:bg-gray-800'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
