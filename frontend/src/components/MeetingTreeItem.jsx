import { Volume2, FileText, Sparkles } from 'lucide-react'

/**
 * Renders a single child leaf inside a meeting folder:
 * - Audio
 * - Transcript
 * - Summary
 */
export default function MeetingTreeItem({
  type,
  label,
  isActive,
  badgeText,
  onClick,
}) {
  const getIcon = () => {
    switch (type) {
      case 'audio':
        return <Volume2 className="w-3.5 h-3.5 shrink-0" />
      case 'transcript':
        return <FileText className="w-3.5 h-3.5 shrink-0" />
      case 'summary':
        return <Sparkles className="w-3.5 h-3.5 shrink-0" />
      default:
        return <FileText className="w-3.5 h-3.5 shrink-0" />
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group w-full flex items-center justify-between pl-7 pr-2.5 py-1.5 text-xs rounded-md transition-colors text-left ${
        isActive
          ? 'bg-gray-100 text-gray-900 font-medium'
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span
          className={`transition-colors ${
            isActive ? 'text-gray-900' : 'text-gray-400 group-hover:text-gray-600'
          }`}
        >
          {getIcon()}
        </span>
        <span className="truncate">{label}</span>
      </div>

      {badgeText && (
        <span className="text-[10px] text-gray-400 font-normal px-1 py-0.5 rounded">
          {badgeText}
        </span>
      )}
    </button>
  )
}
