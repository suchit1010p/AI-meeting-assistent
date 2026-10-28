import { FolderSearch, Plus } from 'lucide-react'
import MeetingFolder from './MeetingFolder'

/**
 * Renders the list of meeting folders in the sidebar.
 * Handles empty search results and empty meeting list states.
 */
export default function MeetingHistory({
  meetings,
  searchQuery,
  expandedFolderIds,
  onToggleExpand,
  activeSelection,
  onSelectMeeting,
  onSelectChildItem,
  onOpenRename,
  onOpenDelete,
  onNewMeeting,
}) {
  // Filter meetings based on search query
  const filteredMeetings = meetings.filter((meeting) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase().trim()
    const matchesTitle = meeting.title.toLowerCase().includes(q)
    const matchesDate = (meeting.date || meeting.created_at || '').toLowerCase().includes(q)
    const matchesTranscript = meeting.transcript?.toLowerCase().includes(q)
    return matchesTitle || matchesDate || matchesTranscript
  })

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex items-center justify-between px-3 py-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
        <span>Meeting History</span>
        <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
          {meetings.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-1.5 py-1">
        {filteredMeetings.length > 0 ? (
          filteredMeetings.map((meeting) => (
            <MeetingFolder
              key={meeting.id}
              meeting={meeting}
              isExpanded={expandedFolderIds.has(meeting.id)}
              onToggleExpand={onToggleExpand}
              activeSelection={activeSelection}
              onSelectMeeting={onSelectMeeting}
              onSelectChildItem={onSelectChildItem}
              onOpenRename={onOpenRename}
              onOpenDelete={onOpenDelete}
            />
          ))
        ) : searchQuery ? (
          // Empty Search State
          <div className="px-3 py-8 text-center">
            <FolderSearch className="w-6 h-6 text-gray-300 mx-auto mb-2" />
            <p className="text-xs font-medium text-gray-700">No matching meetings</p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              No results for "{searchQuery}"
            </p>
          </div>
        ) : (
          // Empty Meeting List State
          <div className="px-3 py-8 text-center">
            <div className="w-8 h-8 rounded-full bg-gray-50 border border-gray-100 flex items-center justify-center mx-auto mb-2.5 text-gray-400">
              <FolderSearch className="w-4 h-4" />
            </div>
            <p className="text-xs font-medium text-gray-700">No meetings yet</p>
            <p className="text-[11px] text-gray-400 mt-0.5 mb-3">
              Capture your first meeting to get started
            </p>
            <button
              type="button"
              onClick={onNewMeeting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              New Meeting
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
