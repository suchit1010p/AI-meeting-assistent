import { useState } from 'react'
import {
  ChevronRight,
  Folder,
  FolderOpen,
  Pencil,
  Trash2,
} from 'lucide-react'
import MeetingTreeItem from './MeetingTreeItem'

/**
 * Collapsible folder node in the meeting history tree.
 * Displays folder name, date, expand/collapse chevron, actions, and child items.
 */
export default function MeetingFolder({
  meeting,
  isExpanded,
  onToggleExpand,
  activeSelection,
  onSelectMeeting,
  onSelectChildItem,
  onOpenRename,
  onOpenDelete,
}) {
  const [isHovered, setIsHovered] = useState(false)

  // Determine if this meeting or any child is currently active
  const isMeetingActive =
    activeSelection?.meetingId === meeting.id && !activeSelection?.childType
  const isAudioActive =
    activeSelection?.meetingId === meeting.id &&
    activeSelection?.childType === 'audio'
  const isTranscriptActive =
    activeSelection?.meetingId === meeting.id &&
    activeSelection?.childType === 'transcript'
  const isSummaryActive =
    activeSelection?.meetingId === meeting.id &&
    activeSelection?.childType === 'summary'

  // Format date nicely (e.g., Oct 27, 2026 or fallback)
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    try {
      const parts = dateStr.split('-')
      if (parts.length === 3) {
        const date = new Date(parts[0], parts[1] - 1, parts[2])
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
        })
      }
      return dateStr
    } catch {
      return dateStr
    }
  }

  return (
    <div
      className="mb-0.5 select-none"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Folder Row Header */}
      <div
        className={`group relative flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
          isMeetingActive
            ? 'bg-gray-100 text-gray-900 font-medium'
            : 'text-gray-700 hover:bg-gray-50'
        }`}
        onClick={() => {
          onSelectMeeting(meeting.id)
          if (!isExpanded) onToggleExpand(meeting.id)
        }}
      >
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          {/* Chevron */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onToggleExpand(meeting.id)
            }}
            aria-label={isExpanded ? 'Collapse folder' : 'Expand folder'}
            className="p-0.5 -ml-1 text-gray-400 hover:text-gray-700 rounded transition-transform"
          >
            <ChevronRight
              className={`w-3.5 h-3.5 transition-transform duration-150 ${
                isExpanded ? 'rotate-90 text-gray-600' : ''
              }`}
            />
          </button>

          {/* Folder Icon */}
          <span className="text-gray-400 group-hover:text-gray-600 shrink-0">
            {isExpanded ? (
              <FolderOpen className="w-3.5 h-3.5 text-gray-600" />
            ) : (
              <Folder className="w-3.5 h-3.5" />
            )}
          </span>

          {/* Title & Date */}
          <div className="flex flex-col min-w-0 pr-1">
            <span className="truncate text-xs text-gray-800 font-medium leading-tight">
              {meeting.title}
            </span>
            <span className="text-[10px] text-gray-400 leading-tight">
              {formatDate(meeting.date)}
            </span>
          </div>
        </div>

        {/* Hover / Context Actions */}
        <div
          className={`flex items-center gap-1 shrink-0 ${
            isHovered ? 'opacity-100' : 'opacity-0 md:opacity-0 group-hover:opacity-100'
          } transition-opacity`}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={() => onOpenRename(meeting)}
            title="Rename meeting"
            aria-label={`Rename ${meeting.title}`}
            className="p-1 text-gray-400 hover:text-gray-700 hover:bg-gray-200/60 rounded transition-colors"
          >
            <Pencil className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={() => onOpenDelete(meeting)}
            title="Delete meeting"
            aria-label={`Delete ${meeting.title}`}
            className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Children Tree: Audio, Transcript, Summary */}
      {isExpanded && (
        <div className="mt-0.5 space-y-0.5 relative before:absolute before:left-3.5 before:top-1 before:bottom-2 before:w-px before:bg-gray-200">
          <MeetingTreeItem
            type="audio"
            label="Audio"
            badgeText={meeting.audioDuration || null}
            isActive={isAudioActive}
            onClick={() => onSelectChildItem(meeting.id, 'audio')}
          />
          <MeetingTreeItem
            type="transcript"
            label="Transcript"
            badgeText={
              meeting.transcript
                ? `${Math.round(meeting.transcript.split(/\s+/).filter(Boolean).length)} words`
                : null
            }
            isActive={isTranscriptActive}
            onClick={() => onSelectChildItem(meeting.id, 'transcript')}
          />
          <MeetingTreeItem
            type="summary"
            label="Summary"
            badgeText={meeting.summary ? 'Ready' : 'Pending'}
            isActive={isSummaryActive}
            onClick={() => onSelectChildItem(meeting.id, 'summary')}
          />
        </div>
      )}
    </div>
  )
}
