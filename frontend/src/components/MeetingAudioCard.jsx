import { useState, useRef, useEffect } from 'react'
import {
  Mic,
  Square,
  Volume2,
  Trash2,
  Play,
  Pause,
  Save,
  RotateCcw,
  AlertCircle,
  RefreshCw,
  Clock,
  AudioLines,
} from 'lucide-react'

/**
 * Audio Recording Card — First Section of the Main Workspace.
 * - Card Header: Mic icon, "Meeting Audio", supporting text, recording action button
 * - Recording Controls: Start / Stop, elapsed timer, audio preview with discard and save actions
 * - Recorded Audio List: Displays recordings for current meeting session with inline playback & delete
 */
export default function MeetingAudioCard({
  recordings = [],
  onSaveRecording,
  onDeleteRecording,
  isRecording,
  setIsRecording,
}) {
  // Pending unsaved recording state
  const [pendingAudio, setPendingAudio] = useState(null) // { blob, url, duration, durationSeconds }
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [errorMessage, setErrorMessage] = useState(null)
  const [activePlayingId, setActivePlayingId] = useState(null)

  // MediaRecorder refs
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const timerIntervalRef = useRef(null)
  const audioChunksRef = useRef([])
  const previewAudioRef = useRef(null)
  const inlineAudioRefs = useRef({})

  // Format seconds to mm:ss
  const formatTime = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Format current timestamp
  const getFormattedTimestamp = () => {
    const now = new Date()
    return now.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }) + ' • Today'
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupMedia()
      if (pendingAudio?.url) {
        try {
          URL.revokeObjectURL(pendingAudio.url)
        } catch {
          // ignore
        }
      }
    }
  }, [pendingAudio])

  const cleanupMedia = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current)
      timerIntervalRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }

  // Start MediaRecorder
  const startRecording = async () => {
    setErrorMessage(null)
    setElapsedSeconds(0)
    audioChunksRef.current = []

    if (
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia ||
      typeof window.MediaRecorder === 'undefined'
    ) {
      setErrorMessage(
        'Audio recording is not supported in this browser. Please use Chrome, Edge, Safari, or Firefox.'
      )
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        '',
      ].find((type) => (type ? MediaRecorder.isTypeSupported(type) : true))

      const options = mimeType ? { mimeType } : undefined
      const recorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const recordedBlob = new Blob(audioChunksRef.current, {
          type: mimeType || 'audio/webm',
        })
        const audioUrl = URL.createObjectURL(recordedBlob)
        const durationFormatted = formatTime(elapsedSeconds)

        cleanupMedia()
        setIsRecording(false)

        setPendingAudio({
          blob: recordedBlob,
          url: audioUrl,
          duration: durationFormatted,
          durationSeconds: elapsedSeconds,
        })
      }

      recorder.start(250)
      setIsRecording(true)

      timerIntervalRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1)
      }, 1000)
    } catch (err) {
      console.error('Error starting audio recording:', err)
      cleanupMedia()
      setIsRecording(false)

      if (
        err.name === 'NotAllowedError' ||
        err.name === 'PermissionDeniedError'
      ) {
        setErrorMessage(
          'Microphone permission was denied. Please allow microphone access in browser settings.'
        )
      } else {
        setErrorMessage(`Microphone error: ${err.message || 'Unable to access device'}`)
      }
    }
  }

  // Stop MediaRecorder
  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== 'inactive'
    ) {
      mediaRecorderRef.current.stop()
    } else {
      cleanupMedia()
      setIsRecording(false)
    }
  }

  // Discard pending recording
  const handleDiscardPending = () => {
    if (pendingAudio?.url) {
      try {
        URL.revokeObjectURL(pendingAudio.url)
      } catch {
        // ignore
      }
    }
    setPendingAudio(null)
  }

  // Save pending recording to session
  const handleSavePending = () => {
    if (!pendingAudio) return
    const newRecording = {
      id: `rec-${Date.now()}`,
      name: `Recording ${recordings.length + 1}`,
      duration: pendingAudio.duration || '00:00',
      timestamp: getFormattedTimestamp(),
      audioUrl: pendingAudio.url,
      blob: pendingAudio.blob,
    }
    onSaveRecording(newRecording)
    setPendingAudio(null) // saved to session
  }

  // Handle inline playback of a saved recording
  const togglePlayRecording = (recordingId) => {
    const audioEl = inlineAudioRefs.current[recordingId]
    if (!audioEl) return

    if (activePlayingId === recordingId) {
      audioEl.pause()
      setActivePlayingId(null)
    } else {
      // Pause any currently playing audio first
      if (activePlayingId && inlineAudioRefs.current[activePlayingId]) {
        inlineAudioRefs.current[activePlayingId].pause()
      }
      audioEl.play().catch((e) => console.warn('Audio play prevented:', e))
      setActivePlayingId(recordingId)
    }
  }

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-2xs">
      {/* Card Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-700 shrink-0">
            <Mic className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 leading-tight">
              Meeting Audio
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Record audio for this meeting.
            </p>
          </div>
        </div>

        {/* Right side recording button */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {!isRecording ? (
            <button
              type="button"
              onClick={startRecording}
              disabled={!!pendingAudio}
              className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all shadow-2xs ${
                pendingAudio
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-900 text-white hover:bg-black active:bg-gray-800'
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record Audio</span>
            </button>
          ) : (
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-red-50 border border-red-200 text-red-600 text-xs font-mono font-medium">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
                <span>{formatTime(elapsedSeconds)}</span>
              </div>
              <button
                type="button"
                onClick={stopRecording}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-900 hover:bg-black text-white text-xs font-medium transition-colors"
              >
                <Square className="w-3 h-3 fill-current" />
                <span>Stop Recording</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Error Notice */}
      {errorMessage && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start justify-between gap-2 text-xs text-red-700">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
            <p>{errorMessage}</p>
          </div>
          <button
            type="button"
            onClick={startRecording}
            className="shrink-0 text-red-700 hover:text-red-900 underline font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Pending Recording Review (When recording just stopped) */}
      {pendingAudio && !isRecording && (
        <div className="mt-4 p-3.5 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center justify-between text-xs text-gray-700 font-medium mb-2">
            <span className="flex items-center gap-1.5">
              <AudioLines className="w-3.5 h-3.5 text-gray-500" />
              New Recording Ready
            </span>
            <span className="text-gray-500 font-mono">
              Duration: {pendingAudio.duration}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <audio
              ref={previewAudioRef}
              src={pendingAudio.url}
              controls
              className="w-full max-w-md h-8 text-xs accent-gray-900"
            />

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={handleDiscardPending}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs text-gray-600 hover:text-red-600 bg-white border border-gray-200 hover:border-red-200 rounded-md transition-colors"
                title="Discard recording"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Discard</span>
              </button>
              <button
                type="button"
                onClick={handleSavePending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-gray-900 hover:bg-black rounded-md transition-colors shadow-2xs"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save Recording</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Previously Recorded Audio List Subsection */}
      <div className="mt-5">
        <div className="flex items-center justify-between mb-2.5">
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Recorded Audio
          </h4>
          <span className="text-[11px] text-gray-400 font-medium">
            {recordings.length} {recordings.length === 1 ? 'recording' : 'recordings'}
          </span>
        </div>

        {recordings.length > 0 ? (
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden bg-white">
            {recordings.map((rec) => {
              const isThisPlaying = activePlayingId === rec.id
              return (
                <div
                  key={rec.id}
                  className="p-3 flex items-center justify-between gap-3 hover:bg-gray-50/60 transition-colors"
                >
                  {/* Left: Audio icon & Title */}
                  <div className="flex items-center gap-3 min-w-0">
                    <button
                      type="button"
                      onClick={() => togglePlayRecording(rec.id)}
                      className="w-7 h-7 rounded-md bg-gray-100 hover:bg-gray-900 hover:text-white text-gray-700 flex items-center justify-center shrink-0 transition-colors"
                      title={isThisPlaying ? 'Pause recording' : 'Play recording'}
                      aria-label={isThisPlaying ? 'Pause' : 'Play'}
                    >
                      {isThisPlaying ? (
                        <Pause className="w-3.5 h-3.5 fill-current" />
                      ) : (
                        <Play className="w-3.5 h-3.5 fill-current translate-x-0.5" />
                      )}
                    </button>

                    <div className="min-w-0">
                      <p className="text-xs font-medium text-gray-900 truncate">
                        {rec.name}
                      </p>
                      <div className="flex items-center gap-2 text-[11px] text-gray-400">
                        <span className="font-mono">{rec.duration}</span>
                        <span>•</span>
                        <span>{rec.timestamp}</span>
                      </div>
                    </div>
                  </div>

                  {/* Hidden or inline audio element for playback */}
                  {rec.audioUrl && (
                    <audio
                      ref={(el) => {
                        inlineAudioRefs.current[rec.id] = el
                      }}
                      src={rec.audioUrl}
                      onEnded={() => setActivePlayingId(null)}
                      className="hidden"
                    />
                  )}

                  {/* Delete action */}
                  <button
                    type="button"
                    onClick={() => onDeleteRecording(rec.id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors shrink-0"
                    title="Delete recording"
                    aria-label={`Delete ${rec.name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="p-4 border border-dashed border-gray-200 rounded-lg text-center bg-gray-50/50">
            <Volume2 className="w-4 h-4 text-gray-400 mx-auto mb-1.5" />
            <p className="text-xs text-gray-500">
              No recordings yet. Start recording to add audio to this meeting.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
