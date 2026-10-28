import { useState, useEffect, useRef } from 'react'
import initialMeetings from './data/mockMeetings'
import Sidebar from './components/Sidebar'
import WorkspaceHeader from './components/WorkspaceHeader'
import MeetingInput from './components/MeetingInput'
import HistoryViewer from './components/HistoryViewer'
import ProcessingState from './components/ProcessingState'
import ConfirmationModal from './components/ConfirmationModal'

/**
 * MeetNote AI - Primary Application Container
 * Manages meeting history, active folder navigation, audio recording state,
 * and workspace presentation.
 */
export default function App() {
  // Meetings data state (initialized with realistic mock data)
  const [meetings, setMeetings] = useState(initialMeetings)

  // Active selection: null (New Meeting workspace) OR { meetingId: string, childType: 'overview'|'audio'|'transcript'|'summary' }
  const [activeSelection, setActiveSelection] = useState(null)

  // Expanded folders in sidebar (default: first meeting expanded)
  const [expandedFolderIds, setExpandedFolderIds] = useState(
    () => new Set(['meeting-1'])
  )

  // Sidebar responsiveness
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false)

  // New Meeting Input State
  const [transcript, setTranscript] = useState('')
  const [audioData, setAudioData] = useState(null) // { blob, url, duration, durationSeconds }
  const [isRecordingAudio, setIsRecordingAudio] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [hasProcessedDemo, setHasProcessedDemo] = useState(false)

  // Dialog / Modal states
  const [deleteModalState, setDeleteModalState] = useState({
    isOpen: false,
    meeting: null,
  })
  const [renameModalState, setRenameModalState] = useState({
    isOpen: false,
    meeting: null,
    newTitle: '',
  })

  // Track created audio object URLs for memory leak cleanup
  const activeObjectUrlsRef = useRef([])

  useEffect(() => {
    return () => {
      // Clean up all generated object URLs on unmount
      activeObjectUrlsRef.current.forEach((url) => {
        try {
          URL.revokeObjectURL(url)
        } catch {
          // Ignore revocation error
        }
      })
    }
  }, [])

  // -------------------------------------------------------------
  // Navigation & Tree Interactions
  // -------------------------------------------------------------

  const handleNewMeeting = () => {
    setActiveSelection(null)
    setHasProcessedDemo(false)
  }

  const handleSelectMeeting = (meetingId) => {
    setActiveSelection({ meetingId, childType: 'overview' })
    setExpandedFolderIds((prev) => {
      const next = new Set(prev)
      next.add(meetingId)
      return next
    })
  }

  const handleSelectChildItem = (meetingId, childType) => {
    setActiveSelection({ meetingId, childType })
  }

  const handleToggleExpand = (meetingId) => {
    setExpandedFolderIds((prev) => {
      const next = new Set(prev)
      if (next.has(meetingId)) {
        next.delete(meetingId)
      } else {
        next.add(meetingId)
      }
      return next
    })
  }

  // -------------------------------------------------------------
  // Audio Lifecycle & Cleanup
  // -------------------------------------------------------------

  const handleAudioRecorded = (recordedData) => {
    // If a previous recording URL existed, revoke it
    if (audioData?.url) {
      try {
        URL.revokeObjectURL(audioData.url)
      } catch {
        // Ignore revocation error
      }
    }
    if (recordedData.url) {
      activeObjectUrlsRef.current.push(recordedData.url)
    }
    setAudioData(recordedData)
  }

  const handleAudioDiscard = () => {
    if (audioData?.url) {
      try {
        URL.revokeObjectURL(audioData.url)
      } catch {
        // Ignore revocation error
      }
    }
    setAudioData(null)
  }

  // -------------------------------------------------------------
  // Processing Simulation
  // -------------------------------------------------------------

  const handleGenerateNotes = () => {
    setIsProcessing(true)
    // Simulate short network & packaging delay (1.4s)
    setTimeout(() => {
      setIsProcessing(false)
      setHasProcessedDemo(true)
    }, 1400)
  }

  const handleResetWorkspace = () => {
    handleAudioDiscard()
    setTranscript('')
    setIsProcessing(false)
    setHasProcessedDemo(false)
  }

  // Convenience action: allows saving current test capture to mock list
  const handleSaveToMockHistory = () => {
    const newId = `meeting-${Date.now()}`
    const today = new Date().toISOString().split('T')[0]
    const title = transcript.trim()
      ? transcript.trim().split('\n')[0].slice(0, 40) + '...'
      : 'Recorded Audio Meeting'

    const newMeeting = {
      id: newId,
      title: title || 'Custom Meeting',
      date: today,
      audioDuration: audioData?.duration || null,
      audioUrl: audioData?.url || null,
      transcript: transcript || 'Audio recorded during this session.',
      summary: `### Summary\nNotes captured from client session.\n\n### Key Highlights\n- Processed input in client session.\n\n### Action Items\n- [ ] Review captured transcript.`,
    }

    setMeetings((prev) => [newMeeting, ...prev])
    setExpandedFolderIds((prev) => new Set([...prev, newId]))
    setActiveSelection({ meetingId: newId, childType: 'overview' })
    handleResetWorkspace()
  }

  // -------------------------------------------------------------
  // Rename & Delete Actions
  // -------------------------------------------------------------

  const handleOpenRename = (meeting) => {
    setRenameModalState({
      isOpen: true,
      meeting,
      newTitle: meeting.title,
    })
  }

  const handleConfirmRename = () => {
    const { meeting, newTitle } = renameModalState
    if (!meeting || !newTitle.trim()) return

    setMeetings((prev) =>
      prev.map((m) => (m.id === meeting.id ? { ...m, title: newTitle.trim() } : m))
    )
    setRenameModalState({ isOpen: false, meeting: null, newTitle: '' })
  }

  const handleOpenDelete = (meeting) => {
    setDeleteModalState({
      isOpen: true,
      meeting,
    })
  }

  const handleConfirmDelete = () => {
    const { meeting } = deleteModalState
    if (!meeting) return

    setMeetings((prev) => prev.filter((m) => m.id !== meeting.id))

    // If currently active meeting was deleted, switch back to New Meeting
    if (activeSelection?.meetingId === meeting.id) {
      setActiveSelection(null)
    }

    setDeleteModalState({ isOpen: false, meeting: null })
  }

  // -------------------------------------------------------------
  // Determine View State
  // -------------------------------------------------------------

  const isHistoryView = activeSelection !== null
  const currentMeeting = isHistoryView
    ? meetings.find((m) => m.id === activeSelection.meetingId)
    : null

  // Resolve Header Title & Subtitle
  let headerTitle = 'New Meeting'
  let headerSubTitle = null
  let headerStatus = 'ready'

  if (isRecordingAudio) {
    headerStatus = 'recording'
  } else if (isProcessing) {
    headerStatus = 'processing'
  } else if (isHistoryView && currentMeeting) {
    headerTitle = currentMeeting.title
    headerStatus = 'archived'
    if (activeSelection.childType === 'audio') headerSubTitle = 'Audio'
    if (activeSelection.childType === 'transcript') headerSubTitle = 'Transcript'
    if (activeSelection.childType === 'summary') headerSubTitle = 'Summary'
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-gray-900 font-sans antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        meetings={meetings}
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebarCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        isMobileDrawerOpen={isMobileDrawerOpen}
        onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
        activeSelection={activeSelection}
        onNewMeeting={handleNewMeeting}
        onSelectMeeting={handleSelectMeeting}
        onSelectChildItem={handleSelectChildItem}
        expandedFolderIds={expandedFolderIds}
        onToggleExpand={handleToggleExpand}
        onOpenRename={handleOpenRename}
        onOpenDelete={handleOpenDelete}
      />

      {/* Main Workspace Column */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-white">
        {/* Top Header */}
        <WorkspaceHeader
          title={headerTitle}
          subTitle={headerSubTitle}
          status={headerStatus}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggleSidebarCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
          onOpenMobileDrawer={() => setIsMobileDrawerOpen(true)}
          onNewMeeting={handleNewMeeting}
          isHistoryView={isHistoryView}
        />

        {/* Workspace Body Area */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {isHistoryView && currentMeeting ? (
            /* Selected History Item View */
            <HistoryViewer
              meeting={currentMeeting}
              selectedTab={activeSelection.childType}
              onTabChange={(tab) =>
                setActiveSelection((prev) => ({ ...prev, childType: tab }))
              }
              onNewMeeting={handleNewMeeting}
            />
          ) : isProcessing || hasProcessedDemo ? (
            /* Processing State / Honest Demo Placeholder */
            <ProcessingState
              isProcessing={isProcessing}
              transcript={transcript}
              audioData={audioData}
              onResetWorkspace={handleResetWorkspace}
              onSaveToMockHistory={handleSaveToMockHistory}
            />
          ) : (
            /* New Meeting Capture Workspace */
            <MeetingInput
              transcript={transcript}
              onTranscriptChange={setTranscript}
              audioData={audioData}
              onAudioRecorded={handleAudioRecorded}
              onAudioDiscard={handleAudioDiscard}
              onGenerateNotes={handleGenerateNotes}
              isRecordingAudio={isRecordingAudio}
              setIsRecordingAudio={setIsRecordingAudio}
            />
          )}
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteModalState.isOpen}
        title="Delete Meeting"
        message={`Are you sure you want to delete "${deleteModalState.meeting?.title}"? This action cannot be undone.`}
        confirmLabel="Delete"
        isDanger={true}
        onConfirm={handleConfirmDelete}
        onClose={() => setDeleteModalState({ isOpen: false, meeting: null })}
      />

      {/* Rename Dialog Modal */}
      <ConfirmationModal
        isOpen={renameModalState.isOpen}
        title="Rename Meeting"
        inputPlaceholder="Enter meeting title..."
        inputValue={renameModalState.newTitle}
        onInputChange={(val) =>
          setRenameModalState((prev) => ({ ...prev, newTitle: val }))
        }
        confirmLabel="Save"
        isDanger={false}
        onConfirm={handleConfirmRename}
        onClose={() =>
          setRenameModalState({ isOpen: false, meeting: null, newTitle: '' })
        }
      />
    </div>
  )
}
