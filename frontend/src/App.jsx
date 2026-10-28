import { useState, useEffect, useRef, useCallback } from 'react'
import meetingsApi from './api/meetingsApi'
import Sidebar from './components/Sidebar'
import WorkspaceHeader from './components/WorkspaceHeader'
import MeetingAudioCard from './components/MeetingAudioCard'
import MeetingTranscriptCard from './components/MeetingTranscriptCard'
import GenerateNotesAction from './components/GenerateNotesAction'
import MeetingNotesCard from './components/MeetingNotesCard'
import ConfirmationModal from './components/ConfirmationModal'
import { AlertCircle, RefreshCw } from 'lucide-react'

/**
 * MeetNote AI - Primary Application Container
 * Integrated with Django REST Framework backend and private AWS S3 storage.
 */
export default function App() {
  // Meetings list state loaded from Django
  const [meetings, setMeetings] = useState([])
  const [isLoadingMeetings, setIsLoadingMeetings] = useState(true)
  const [apiError, setApiError] = useState(null)

  // Active selection: null (New Meeting) OR { meetingId: number|string, childType?: 'overview'|'audio'|'transcript'|'summary' }
  const [activeSelection, setActiveSelection] = useState(null)

  // Detailed meeting state containing files array from GET /api/meetings/<id>/
  const [activeMeetingDetails, setActiveMeetingDetails] = useState(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)

  // Cache for text content of transcripts and summaries fetched from S3 presigned URLs: { [fileId]: string }
  const [fileContents, setFileContents] = useState({})

  // Draft session state for "New Meeting" before persisting
  const [draftSession, setDraftSession] = useState({
    recordings: [],
    transcripts: [],
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
  const [expandedFolderIds, setExpandedFolderIds] = useState(() => new Set())

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

  // Active object URLs cleanup for local preview blobs
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
  // Load meetings from Django backend on mount
  // -------------------------------------------------------------
  const fetchMeetingsList = useCallback(async (selectMeetingId = null) => {
    try {
      setIsLoadingMeetings(true)
      setApiError(null)
      const data = await meetingsApi.listMeetings()
      setMeetings(data)

      if (selectMeetingId) {
        setActiveSelection({ meetingId: selectMeetingId, childType: 'overview' })
        setExpandedFolderIds((prev) => new Set([...prev, selectMeetingId]))
      } else if (data.length > 0 && activeSelection === null) {
        setActiveSelection({ meetingId: data[0].id, childType: 'overview' })
        setExpandedFolderIds((prev) => new Set([...prev, data[0].id]))
      }
    } catch (err) {
      console.error('[MeetNote AI] Failed to fetch meetings:', err)
      setApiError(err.message || 'Failed to connect to backend server.')
    } finally {
      setIsLoadingMeetings(false)
    }
  }, [activeSelection])

  useEffect(() => {
    fetchMeetingsList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // -------------------------------------------------------------
  // Load meeting details and files whenever active selection changes
  // -------------------------------------------------------------
  const loadMeetingDetails = useCallback(async (meetingId) => {
    if (!meetingId) {
      setActiveMeetingDetails(null)
      return
    }

    try {
      setIsLoadingDetails(true)
      const details = await meetingsApi.getMeeting(meetingId)
      setActiveMeetingDetails(details)

      // Fetch text content for any transcript and summary files
      if (details.files && details.files.length > 0) {
        details.files.forEach(async (file) => {
          if (
            (file.file_type === 'transcript' || file.file_type === 'summary') &&
            file.download_url
          ) {
            try {
              const text = await meetingsApi.fetchTextFromS3(file.download_url)
              setFileContents((prev) => ({ ...prev, [file.id]: text }))
            } catch (err) {
              console.warn(`[MeetNote AI] Could not fetch text for file ${file.id}:`, err)
            }
          }
        })
      }
    } catch (err) {
      console.error(`[MeetNote AI] Failed to load details for meeting ${meetingId}:`, err)
      setApiError(err.message)
    } finally {
      setIsLoadingDetails(false)
    }
  }, [])

  useEffect(() => {
    if (activeSelection?.meetingId) {
      loadMeetingDetails(activeSelection.meetingId)
    } else {
      setActiveMeetingDetails(null)
    }
  }, [activeSelection?.meetingId, loadMeetingDetails])

  // -------------------------------------------------------------
  // Active Session Resolution
  // -------------------------------------------------------------
  const isHistorySession = activeSelection !== null
  const activeMeeting = isHistorySession
    ? activeMeetingDetails || meetings.find((m) => m.id === activeSelection.meetingId)
    : null

  // Format file timestamp
  const formatFileTimestamp = (dateStr) => {
    if (!dateStr) return 'Just now'
    try {
      const d = new Date(dateStr)
      if (isNaN(d.getTime())) return String(dateStr)
      const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
      const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      return `${time} • ${date}`
    } catch {
      return String(dateStr)
    }
  }

  // Current session recordings (mapped from backend files or draft)
  const currentRecordings = isHistorySession
    ? (activeMeetingDetails?.files || [])
        .filter((f) => f.file_type === 'audio')
        .map((f) => ({
          id: f.id,
          fileId: f.id,
          name: f.original_filename || `Recording ${f.id}`,
          duration: 'Audio',
          timestamp: formatFileTimestamp(f.created_at),
          audioUrl: f.download_url,
          s3Key: f.s3_key,
        }))
    : draftSession.recordings

  // Current session transcripts (mapped from backend files or draft)
  const currentTranscripts = isHistorySession
    ? (activeMeetingDetails?.files || [])
        .filter((f) => f.file_type === 'transcript')
        .map((f) => {
          const text = fileContents[f.id] || ''
          return {
            id: f.id,
            fileId: f.id,
            name: f.original_filename || `Transcript ${f.id}`,
            text: text || 'Loading transcript from S3...',
            preview: text ? text.slice(0, 140) + '...' : 'Loading transcript from S3...',
            wordCount: text ? text.trim().split(/\s+/).filter(Boolean).length : 0,
            charCount: text ? text.length : 0,
            timestamp: formatFileTimestamp(f.created_at),
            downloadUrl: f.download_url,
            s3Key: f.s3_key,
          }
        })
    : draftSession.transcripts

  // Current session notes (mapped from backend summary files or draft)
  const currentNotes = isHistorySession
    ? (activeMeetingDetails?.files || [])
        .filter((f) => f.file_type === 'summary')
        .map((f) => {
          const content = fileContents[f.id] || ''
          return {
            id: f.id,
            fileId: f.id,
            title: f.original_filename || `Meeting Notes ${f.id}`,
            content: content || 'Loading notes from S3...',
            preview: content ? content.slice(0, 140) + '...' : 'Loading notes from S3...',
            timestamp: formatFileTimestamp(f.created_at),
          }
        })
    : draftSession.notes

  // -------------------------------------------------------------
  // Navigation & Tree Interactions
  // -------------------------------------------------------------
  const handleNewMeeting = () => {
    setActiveSelection(null)
    setActiveMeetingDetails(null)
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
  // Audio Recording & Direct AWS S3 Upload Workflow
  // -------------------------------------------------------------
  const handleSaveRecording = async (pendingAudioData) => {
    let targetMeetingId = activeSelection?.meetingId

    // 1. If in "New Meeting" mode, create meeting in Django first
    if (!targetMeetingId) {
      const dateStr = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
      const newMeeting = await meetingsApi.createMeeting(`Meeting — ${dateStr}`)
      targetMeetingId = newMeeting.id
      setMeetings((prev) => [newMeeting, ...prev])
      setActiveSelection({ meetingId: targetMeetingId, childType: 'audio' })
      setExpandedFolderIds((prev) => new Set([...prev, targetMeetingId]))
    }

    // 2. Format filename and determine MIME type
    const rawMime = pendingAudioData.blob?.type || 'audio/webm'
    const cleanMime = rawMime.split(';')[0] || 'audio/webm'
    const ext = cleanMime.includes('wav')
      ? '.wav'
      : cleanMime.includes('mp4')
      ? '.mp4'
      : cleanMime.includes('mpeg')
      ? '.mp3'
      : '.webm'
    const filename = `recording_${Date.now()}${ext}`

    // 3. Request presigned upload URL from Django backend
    const uploadData = await meetingsApi.getUploadUrl(targetMeetingId, {
      file_type: 'audio',
      content_type: cleanMime,
      filename,
    })

    // 4. Upload raw audio Blob directly to AWS S3 using presigned PUT URL
    await meetingsApi.uploadToS3(uploadData.upload_url, pendingAudioData.blob, uploadData.content_type)

    // 5. Confirm upload with Django and persist metadata in SQLite
    await meetingsApi.confirmFile(targetMeetingId, {
      s3_key: uploadData.s3_key,
      file_type: 'audio',
      original_filename: filename,
    })

    // 6. Refresh active meeting details from Django
    await loadMeetingDetails(targetMeetingId)
    const updatedMeetings = await meetingsApi.listMeetings()
    setMeetings(updatedMeetings)
  }

  const handleDeleteRecording = async (fileId) => {
    if (activeSelection?.meetingId) {
      try {
        await meetingsApi.deleteFile(activeSelection.meetingId, fileId)
        await loadMeetingDetails(activeSelection.meetingId)
        const updatedMeetings = await meetingsApi.listMeetings()
        setMeetings(updatedMeetings)
      } catch (err) {
        console.error('Failed to delete recording:', err)
        alert(`Failed to delete recording: ${err.message}`)
      }
    }
  }

  // -------------------------------------------------------------
  // Transcript Upload Workflow (S3 + SQLite)
  // -------------------------------------------------------------
  const handleSubmitTranscript = async (text) => {
    let targetMeetingId = activeSelection?.meetingId

    // 1. If in "New Meeting" mode, create meeting in Django first
    if (!targetMeetingId) {
      const dateStr = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
      const newMeeting = await meetingsApi.createMeeting(`Meeting — ${dateStr}`)
      targetMeetingId = newMeeting.id
      setMeetings((prev) => [newMeeting, ...prev])
      setActiveSelection({ meetingId: targetMeetingId, childType: 'transcript' })
      setExpandedFolderIds((prev) => new Set([...prev, targetMeetingId]))
    }

    const filename = `transcript_${Date.now()}.txt`
    const textBlob = new Blob([text], { type: 'text/plain;charset=utf-8' })

    // 2. Request presigned upload URL
    const uploadData = await meetingsApi.getUploadUrl(targetMeetingId, {
      file_type: 'transcript',
      content_type: 'text/plain',
      filename,
    })

    // 3. Direct PUT to S3
    await meetingsApi.uploadToS3(uploadData.upload_url, textBlob, 'text/plain')

    // 4. Confirm with Django
    const confirmed = await meetingsApi.confirmFile(targetMeetingId, {
      s3_key: uploadData.s3_key,
      file_type: 'transcript',
      original_filename: filename,
    })

    // Cache text in state
    if (confirmed?.id) {
      setFileContents((prev) => ({ ...prev, [confirmed.id]: text }))
    }

    // 5. Refresh details
    await loadMeetingDetails(targetMeetingId)
    const updatedMeetings = await meetingsApi.listMeetings()
    setMeetings(updatedMeetings)
  }

  const handleDeleteTranscript = async (fileId) => {
    if (activeSelection?.meetingId) {
      try {
        await meetingsApi.deleteFile(activeSelection.meetingId, fileId)
        await loadMeetingDetails(activeSelection.meetingId)
        const updatedMeetings = await meetingsApi.listMeetings()
        setMeetings(updatedMeetings)
      } catch (err) {
        console.error('Failed to delete transcript:', err)
        alert(`Failed to delete transcript: ${err.message}`)
      }
    }
  }

  const handleDeleteNote = (noteId) => {
    if (isHistorySession && activeMeeting) {
      // If note is local or backend file
      if (typeof noteId === 'number') {
        meetingsApi.deleteFile(activeSelection.meetingId, noteId).then(() => {
          loadMeetingDetails(activeSelection.meetingId)
        })
      }
    } else {
      setDraftSession((prev) => ({
        ...prev,
        notes: prev.notes.filter((n) => n.id !== noteId),
      }))
    }
  }

  // -------------------------------------------------------------
  // Generate Notes Action (Frontend action preserving existing UI)
  // -------------------------------------------------------------
  const canGenerate = currentTranscripts.length > 0 || currentRecordings.length > 0

  const handleGenerateNotes = () => {
    if (!canGenerate || isGenerating) return

    setIsGenerating(true)
    setDemoNotice(false)

    setTimeout(() => {
      setIsGenerating(false)
      setDemoNotice(true)
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

  const handleConfirmRename = async () => {
    const { meeting, newTitle } = renameModalState
    if (!meeting || !newTitle.trim()) return

    try {
      await meetingsApi.updateMeeting(meeting.id, { title: newTitle.trim() })
      setMeetings((prev) =>
        prev.map((m) => (m.id === meeting.id ? { ...m, title: newTitle.trim() } : m))
      )
      if (activeMeetingDetails?.id === meeting.id) {
        setActiveMeetingDetails((prev) => ({ ...prev, title: newTitle.trim() }))
      }
    } catch (err) {
      console.error('Failed to rename meeting:', err)
      alert(`Failed to rename meeting: ${err.message}`)
    } finally {
      setRenameModalState({ isOpen: false, meeting: null, newTitle: '' })
    }
  }

  const handleOpenDelete = (meeting) => {
    setDeleteModalState({
      isOpen: true,
      meeting,
    })
  }

  const handleConfirmDelete = async () => {
    const { meeting } = deleteModalState
    if (!meeting) return

    try {
      await meetingsApi.deleteMeeting(meeting.id)
      const nextMeetings = meetings.filter((m) => m.id !== meeting.id)
      setMeetings(nextMeetings)

      if (activeSelection?.meetingId === meeting.id) {
        if (nextMeetings.length > 0) {
          setActiveSelection({ meetingId: nextMeetings[0].id, childType: 'overview' })
        } else {
          setActiveSelection(null)
          setActiveMeetingDetails(null)
        }
      }
    } catch (err) {
      console.error('Failed to delete meeting:', err)
      alert(`Failed to delete meeting: ${err.message}`)
    } finally {
      setDeleteModalState({ isOpen: false, meeting: null })
    }
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

        {/* Global API Connection Error Banner */}
        {apiError && (
          <div className="bg-red-50 border-b border-red-200 px-6 py-2.5 flex items-center justify-between text-xs text-red-800">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{apiError}</span>
            </div>
            <button
              type="button"
              onClick={() => fetchMeetingsList()}
              className="inline-flex items-center gap-1 font-semibold underline hover:text-red-950"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry Connection</span>
            </button>
          </div>
        )}

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

            {/* 2. Meeting Transcript Card */}
            <div id="section-transcript">
              <MeetingTranscriptCard
                transcripts={currentTranscripts}
                onSubmitTranscript={handleSubmitTranscript}
                onDeleteTranscript={handleDeleteTranscript}
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
        message={`Are you sure you want to delete "${deleteModalState.meeting?.title}"? This will delete all associated audio recordings, transcripts, and S3 files.`}
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
