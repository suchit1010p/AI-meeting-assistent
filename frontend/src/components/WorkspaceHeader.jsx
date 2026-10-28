import {
  Menu,
  PanelLeftOpen,
  Sparkles,
  Radio,
  Loader2,
  CheckCircle2,
  Plus,
} from 'lucide-react'

/**
 * Top navigation bar of the main workspace:
 * - Page Title: "New Meeting" or selected meeting title
 * - Subtle status indicator: "Ready", "Recording", "Processing", or "Archived"
 * - Responsive drawer toggle & desktop sidebar un-collapse toggle
 */
export default function WorkspaceHeader({
  title = 'New Meeting',
  subTitle = null,
  status = 'ready', // 'ready' | 'recording' | 'processing' | 'archived'
  isSidebarCollapsed,
  onToggleSidebarCollapse,
  onOpenMobileDrawer,
  onNewMeeting,
  isHistoryView = false,
}) {
  const renderStatus = () => {
    switch (status) {
      case 'recording':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 border border-red-200 text-red-600 text-xs font-medium animate-pulse">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            <span>Recording</span>
          </div>
        )
      case 'processing':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Processing...</span>
          </div>
        )
      case 'archived':
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 text-gray-600 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-gray-400"></span>
            <span>Archived Meeting</span>
          </div>
        )
      case 'ready':
      default:
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-50 border border-gray-200 text-gray-600 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>Ready</span>
          </div>
        )
    }
  }

  return (
    <header className="h-14 border-b border-gray-200 px-4 md:px-6 flex items-center justify-between bg-white shrink-0">
      {/* Left: Sidebar Toggle + Title */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile Hamburger */}
        <button
          type="button"
          onClick={onOpenMobileDrawer}
          className="md:hidden p-1.5 -ml-1 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
          aria-label="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Desktop Expand Button (when collapsed) */}
        {isSidebarCollapsed && (
          <button
            type="button"
            onClick={onToggleSidebarCollapse}
            className="hidden md:flex p-1.5 -ml-1 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
            title="Expand sidebar"
            aria-label="Expand sidebar"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        )}

        {/* Title & Subtitle Breadcrumb */}
        <div className="flex items-baseline gap-2 min-w-0 truncate">
          <h1 className="text-sm md:text-base font-semibold text-gray-900 truncate">
            {title}
          </h1>
          {subTitle && (
            <span className="text-xs text-gray-400 font-normal truncate hidden sm:inline">
              / {subTitle}
            </span>
          )}
        </div>
      </div>

      {/* Right: Status Indicator & Quick Actions */}
      <div className="flex items-center gap-3 shrink-0">
        {isHistoryView && (
          <button
            type="button"
            onClick={onNewMeeting}
            className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Capture</span>
          </button>
        )}
        {renderStatus()}
      </div>
    </header>
  )
}
