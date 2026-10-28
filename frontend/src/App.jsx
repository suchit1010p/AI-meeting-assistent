import { useState, useEffect, useRef } from 'react'
import initialMeetings from './data/mockMeetings'
import Sidebar from './components/Sidebar'
import WorkspaceHeader from './components/WorkspaceHeader'
import MeetingAudioCard from './components/MeetingAudioCard'
import MeetingTranscriptInput from './components/MeetingTranscriptInput'
import GenerateNotesAction from './components/GenerateNotesAction'
import MeetingNotesCard from './components/MeetingNotesCard'
import ConfirmationModal from './components/ConfirmationModal'

/**
 * MeetNote AI - Primary Application Container
 * Main workspace content order:
 * 1. Audio Recording Card (MeetingAudioCard)
 * 2. Transcript Text Input (MeetingTranscriptInput)
 * 3. Generate Notes Action (GenerateNotesAction)
 * 4. Meeting Notes Card (MeetingNotesCard)
 */
export default function App() {
  // Saved meetings state
  const [meetings, setMeetings] = useState(initialMeetings)

  // Active selection: null (New Meeting) OR { meetingId: string, childType?: 'overview'|'audio'|'transcript'|'summary' }
  const [activeSelection, setActiveSelection] = useState(null)

  // Draft session state for "New Meeting"
  const [draftSession, setDraftSession] = useState({
    recordings: [],
    transcript: '',
    notes: [],
  })

  // Global recording state indicator
  const [isRecordingAudio, setIsRecordingAudio] = useState(false)

  // Generate notes processing states
  const [isGenerating, setIsGenerating] = useState(false)
  const [demoNotice, setDemoNotice] = useState(false)

  // Sidebar state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false)
  const [expandedFolderIds, setExpandedFolderIds] = useState(
    () => new Set(['meeting-1'])
  )

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
      activeObjectUrlsRef.current.forEach((url) => {
        try {
          URL.revokeObjectURL(url)
        } catch {
          // ignore
        }
      })
    }
  }, [])

  // -------------------------------------------------------------
  // Active Session Resolution
  // -------------------------------------------------------------
  const isHistorySession = activeSelection !== null
  const activeMeeting = isHistorySession
    ? meetings.find((m) => m.id === activeSelection.meetingId)
    : null

  // Current session data: either the selected meeting or the draft session
  const currentRecordings = isHistorySession
    ? activeMeeting?.recordings || []
    : draftSession.recordings
  const currentTranscript = isHistorySession
    ? activeMeeting?.transcript || ''
    : draftSession.transcript
  const currentNotes = isHistorySession
    ? activeMeeting?.notes || []
    : draftSession.notes

  // -------------------------------------------------------------
  // Navigation & Tree Interactions
  // -------------------------------------------------------------
  const handleNewMeeting = () => {
    setActiveSelection(null)
    setDemoNotice(false)
  }

  const handleSelectMeeting = (meetingId) => {
    setActiveSelection({ meetingId, childType: 'overview' })
    setDemoNotice(false)
    setExpandedFolderIds((prev) => {
      const next = new Set(prev)
      next.add(meetingId)
      return next
    })
  }

  const handleSelectChildItem = (meetingId, childType) => {
    setActiveSelection({ meetingId, childType })
    setDemoNotice(false)

    // Smooth-scroll to target section
    setTimeout(() => {
      const targetId =
        childType === 'audio'
          ? 'section-audio'
          : childType === 'transcript'
          ? 'section-transcript'
          : 'section-notes'
      const el = document.getElementById(targetId)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 50)
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
  // Session State Modifiers
  // -------------------------------------------------------------
  const handleSaveRecording = (newRecording) => {
    if (newRecording.audioUrl) {
      activeObjectUrlsRef.current.push(newRecording.audioUrl)
    }

    if (isHistorySession && activeMeeting) {
      setMeetings((prev) =>
        prev.map((m) =>
          m.id === activeMeeting.id
            ? {
                ...m,
                recordings: [newRecording, ...(m.recordings || [])],
                audioDuration: newRecording.duration,
              }
            : m
        )
      )
    } else {
      setDraftSession((prev) => ({
        ...prev,
        recordings: [newRecording, ...prev.recordings],
      }))
    }
  }

  const handleDeleteRecording = (recordingId) => {
    if (isHistorySession && activeMeeting) {
      setMeetings((prev) =>
        prev.map((m) =>
          m.id === activeMeeting.id
            ? {
                ...m,
                recordings: (m.recordings || []).filter(
                  (r) => r.id !== recordingId
                ),
              }
            : m
        )
      )
    } else {
      setDraftSession((prev) => ({
        ...prev,
        recordings: prev.recordings.filter((r) => r.id !== recordingId),
      }))
    }
  }

  const handleTranscriptChange = (newText) => {
    if (isHistorySession && activeMeeting) {
      setMeetings((prev) =>
        prev.map((m) =>
          m.id === activeMeeting.id ? { ...m, transcript: newText } : m
        )
      )
    } else {
      setDraftSession((prev) => ({
        ...prev,
        transcript: newText,
      }))
    }
  }

  const handleDeleteNote = (noteId) => {
    if (isHistorySession && activeMeeting) {
      setMeetings((prev) =>
        prev.map((m) =>
          m.id === activeMeeting.id
            ? {
                ...m,
                notes: (m.notes || []).filter((n) => n.id !== noteId),
              }
            : m
        )
      )
    } else {
      setDraftSession((prev) => ({
        ...prev,
        notes: prev.notes.filter((n) => n.id !== noteId),
      }))
    }
  }

  // -------------------------------------------------------------
  // Generate Notes Action
  // -------------------------------------------------------------
  const canGenerate =
    currentTranscript.trim().length > 0 || currentRecordings.length > 0

  const handleGenerateNotes = () => {
    if (!canGenerate || isGenerating) return

    setIsGenerating(true)
    setDemoNotice(false)

    // Simulate short frontend processing state
    setTimeout(() => {
      setIsGenerating(false)
      setDemoNotice(true)

      // Add a clean demo note to the session so the notes card updates
      const timestampStr = new Date().toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      }) + ' • Today'

      const generatedNote = {
        id: `note-${Date.now()}`,
        title: `Meeting Notes — ${new Date().toLocaleTimeString('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true,
        })}`,
        preview: currentTranscript.trim()
          ? `Notes captured from transcript (${currentTranscript.trim().split(/\s+/).length} words)...`
          : `Notes captured from ${currentRecordings.length} audio recording(s)...`,
        timestamp: timestampStr,
        content: `### Meeting Notes (Frontend Demo)
This note illustrates the frontend layout for generated meeting documentation. In a complete production deployment, this content is returned by the AI processing service using Whisper speech transcription and LLM summarization.

### Session Inputs Processed
- Transcript: ${
          currentTranscript.trim()
            ? `${currentTranscript.length} characters`
            : 'None provided'
        }
- Audio recordings: ${currentRecordings.length} recording(s)

### Action Items
- [ ] Connect backend transcription pipeline.
- [ ] Connect LLM summarization service.`,
      }

      if (isHistorySession && activeMeeting) {
        setMeetings((prev) =>
          prev.map((m) =>
            m.id === activeMeeting.id
              ? {
                  ...m,
                  notes: [generatedNote, ...(m.notes || [])],
                }
              : m
          )
        )
      } else {
        setDraftSession((prev) => ({
          ...prev,
          notes: [generatedNote, ...prev.notes],
        }))
      }
    }, 1200)
  }

  // -------------------------------------------------------------
  // Rename & Delete Meeting Dialogs
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
      prev.map((m) =>
        m.id === meeting.id ? { ...m, title: newTitle.trim() } : m
      )
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

    if (activeSelection?.meetingId === meeting.id) {
      setActiveSelection(null)
    }

    setDeleteModalState({ isOpen: false, meeting: null })
  }

  // -------------------------------------------------------------
  // Header Title & Status
  // -------------------------------------------------------------
  let headerTitle = 'New Meeting'
  let headerSubTitle = null
  let headerStatus = 'ready'

  if (isRecordingAudio) {
    headerStatus = 'recording'
  } else if (isGenerating) {
    headerStatus = 'processing'
  } else if (isHistorySession && activeMeeting) {
    headerTitle = activeMeeting.title
    headerStatus = 'archived'
    if (activeSelection.childType === 'audio') headerSubTitle = 'Audio'
    if (activeSelection.childType === 'transcript') headerSubTitle = 'Transcript'
    if (activeSelection.childType === 'summary') headerSubTitle = 'Notes'
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-gray-900 font-sans antialiased">
      {/* Left Sidebar */}
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
          isHistoryView={isHistorySession}
        />

        {/* Workspace Body: Centered Container with max-w-[900px] */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          <div className="w-full max-w-[900px] mx-auto px-4 sm:px-6 py-6 md:py-8 space-y-5">
            {/* 1. Audio Recording Card */}
            <div id="section-audio">
              <MeetingAudioCard
                recordings={currentRecordings}
                onSaveRecording={handleSaveRecording}
                onDeleteRecording={handleDeleteRecording}
                isRecording={isRecordingAudio}
                setIsRecording={setIsRecordingAudio}
              />
            </div>

            {/* 2. Transcript Text Input */}
            <div id="section-transcript">
              <MeetingTranscriptInput
                transcript={currentTranscript}
                onChange={handleTranscriptChange}
              />
            </div>

            {/* 3. Generate Notes Action */}
            <div id="section-generate">
              <GenerateNotesAction
                canGenerate={canGenerate}
                isGenerating={isGenerating}
                onGenerateNotes={handleGenerateNotes}
                demoNotice={demoNotice}
                onDismissNotice={() => setDemoNotice(false)}
              />
            </div>

            {/* 4. Meeting Notes Card */}
            <div id="section-notes">
              <MeetingNotesCard
                notes={currentNotes}
                onDeleteNote={handleDeleteNote}
              />
            </div>
          </div>
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
