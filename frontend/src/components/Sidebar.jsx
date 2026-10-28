import { useState } from 'react'
import {
  Sparkles,
  Plus,
  Search,
  X,
  PanelLeftClose,
  PanelLeft,
  AudioLines,
} from 'lucide-react'
import MeetingHistory from './MeetingHistory'

/**
 * Left Sidebar navigation component:
 * - Brand logo & title: MeetNote AI
 * - "+ New Meeting" action
 * - Meeting search filter
 * - Collapsible meeting history folder tree
 * - Collapse sidebar toggle
 * - Responsive mobile drawer support
 */
export default function Sidebar({
  meetings,
  isSidebarCollapsed,
  onToggleSidebarCollapse,
  isMobileDrawerOpen,
  onCloseMobileDrawer,
  activeSelection,
  onNewMeeting,
  onSelectMeeting,
  onSelectChildItem,
  expandedFolderIds,
  onToggleExpand,
  onOpenRename,
  onOpenDelete,
}) {
  const [searchQuery, setSearchQuery] = useState('')

  const handleNewMeetingClick = () => {
    onNewMeeting()
    if (isMobileDrawerOpen) onCloseMobileDrawer()
  }

  const handleSelectMeeting = (id) => {
    onSelectMeeting(id)
    if (isMobileDrawerOpen) onCloseMobileDrawer()
  }

  const handleSelectChildItem = (id, type) => {
    onSelectChildItem(id, type)
    if (isMobileDrawerOpen) onCloseMobileDrawer()
  }

  const sidebarContent = (
    <aside
      className={`h-full flex flex-col bg-white border-r border-gray-200 select-none ${
        isSidebarCollapsed ? 'w-0 overflow-hidden border-r-0' : 'w-[270px]'
      } transition-[width] duration-200 ease-in-out`}
    >
      {/* Top Header: Logo + Collapse Button */}
      <div className="p-4 pb-3 flex items-center justify-between border-b border-gray-100">
        <div
          onClick={handleNewMeetingClick}
          className="flex items-center gap-2.5 cursor-pointer group"
          title="MeetNote AI - Go to New Meeting"
        >
          <div className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center text-white shadow-2xs group-hover:bg-black transition-colors">
            <AudioLines className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-gray-900 tracking-tight leading-tight">
              MeetNote AI
            </span>
            <span className="text-[10px] text-gray-400 font-normal leading-tight">
              Meeting Assistant
            </span>
          </div>
        </div>

        {/* Collapse toggle button on desktop */}
        <button
          type="button"
          onClick={onToggleSidebarCollapse}
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
          className="hidden md:flex p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={onCloseMobileDrawer}
          title="Close menu"
          aria-label="Close menu"
          className="md:hidden p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Action: + New Meeting Button */}
      <div className="p-3 pb-2">
        <button
          type="button"
          onClick={handleNewMeetingClick}
          className={`w-full flex items-center justify-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all shadow-2xs ${
            activeSelection === null
              ? 'bg-gray-900 text-white hover:bg-black'
              : 'bg-white text-gray-800 border border-gray-200 hover:bg-gray-50 hover:border-gray-300'
          }`}
        >
          <Plus className="w-4 h-4" />
          <span>New Meeting</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="px-3 py-1">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search history..."
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-gray-50 border border-transparent rounded-md text-gray-800 placeholder-gray-400 focus:bg-white focus:outline-none focus:border-gray-300 focus:ring-1 focus:ring-gray-300 transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-0.5"
              aria-label="Clear search"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Meeting History Section */}
      <div className="flex-1 min-h-0 mt-1 flex flex-col">
        <MeetingHistory
          meetings={meetings}
          searchQuery={searchQuery}
          expandedFolderIds={expandedFolderIds}
          onToggleExpand={onToggleExpand}
          activeSelection={activeSelection}
          onSelectMeeting={handleSelectMeeting}
          onSelectChildItem={handleSelectChildItem}
          onOpenRename={onOpenRename}
          onOpenDelete={onOpenDelete}
          onNewMeeting={handleNewMeetingClick}
        />
      </div>

      {/* Bottom Footer Info */}
      <div className="p-3 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-400">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          Frontend Only Demo
        </span>
        <span className="text-[10px] text-gray-400">v1.0</span>
      </div>
    </aside>
  )

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:block shrink-0 h-full">{sidebarContent}</div>

      {/* Mobile Drawer (Overlay) */}
      {isMobileDrawerOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden bg-black/25 backdrop-blur-2xs transition-opacity"
          onClick={onCloseMobileDrawer}
          aria-hidden="true"
        >
          <div
            className="h-full w-[280px] max-w-[85vw] bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  )
}
