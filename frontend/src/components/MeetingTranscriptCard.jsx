import { useState } from 'react'
import {
  FileText,
  Trash2,
  ExternalLink,
  X,
  Copy,
  Check,
  Music,
  CheckCircle2,
  Clock,
  Loader2,
} from 'lucide-react'

/**
 * Meeting Transcript Card — Second Section of the Main Workspace.
 * Displays all generated transcripts for the current meeting session.
 * Removed manual textarea, sample link, and submit button.
 * Lists:
 * - Original audio filename
 * - Transcript filename
 * - Generation status
 * - An "Open Transcript" button to retrieve content from S3 and view in a clean modal.
 */
export default function MeetingTranscriptCard({
  transcripts = [],
  onOpenTranscript,
  onDeleteTranscript,
}) {
  const [selectedTranscript, setSelectedTranscript] = useState(null)
  const [copied, setCopied] = useState(false)
  const [isLoadingContent, setIsLoadingContent] = useState(false)

  const handleOpen = async (t) => {
    // If the transcript content is already provided, open directly; otherwise fetch
    if (t.text && t.text !== 'Loading transcript from S3...') {
      setSelectedTranscript(t)
      return
    }

    if (onOpenTranscript) {
      setIsLoadingContent(true)
      try {
        const fullTranscript = await onOpenTranscript(t.id)
        setSelectedTranscript(fullTranscript || t)
      } catch (err) {
        console.error('Failed to open transcript:', err)
        setSelectedTranscript(t)
      } finally {
        setIsLoadingContent(false)
      }
    } else {
      setSelectedTranscript(t)
    }
  }

  const handleCopy = async (text) => {
    if (text) {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-2xs">
      {/* Card Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-700 shrink-0">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 leading-tight">
              Meeting Transcripts
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Transcripts automatically generated from your meeting audio recordings.
            </p>
          </div>
        </div>

        <span className="text-[11px] text-gray-400 font-medium">
          {transcripts.length} {transcripts.length === 1 ? 'transcript' : 'transcripts'}
        </span>
      </div>

      {/* Transcripts List */}
      <div className="mt-4">
        {transcripts.length > 0 ? (
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden bg-white">
            {transcripts.map((t) => {
              const audioName =
                t.originalAudioFilename ||
                t.original_audio_filename ||
                t.audioFilename ||
                'Audio Recording'
              const transcriptName = t.name || t.original_filename || `transcript_${t.id}.txt`
              const wordCount =
                t.wordCount ||
                (t.text && t.text !== 'Loading transcript from S3...'
                  ? t.text.trim().split(/\s+/).filter(Boolean).length
                  : 0)

              return (
                <div
                  key={t.id}
                  className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-gray-50/60 transition-colors"
                >
                  {/* Left: Icon & Details */}
                  <div className="flex items-start sm:items-center gap-3 min-w-0 flex-1">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 text-gray-700 flex items-center justify-center shrink-0 mt-0.5 sm:mt-0">
                      <FileText className="w-4 h-4" />
                    </div>

                    <div className="min-w-0 flex-1 space-y-1">
                      {/* Transcript filename & status */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-xs font-semibold text-gray-900 truncate">
                          {transcriptName}
                        </p>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          <span>Generated</span>
                        </span>
                      </div>

                      {/* Original audio reference */}
                      <div className="flex items-center gap-1.5 text-[11px] text-gray-500">
                        <Music className="w-3 h-3 text-gray-400 shrink-0" />
                        <span className="truncate">Source Audio: {audioName}</span>
                      </div>

                      {/* Metadata row */}
                      <div className="flex items-center gap-2 text-[10px] text-gray-400">
                        {wordCount > 0 && (
                          <>
                            <span className="font-mono">{wordCount.toLocaleString()} words</span>
                            <span>•</span>
                          </>
                        )}
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {t.timestamp || 'Today'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                    <button
                      type="button"
                      onClick={() => handleOpen(t)}
                      disabled={isLoadingContent}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 active:bg-gray-100 rounded-md transition-colors shadow-2xs cursor-pointer"
                      title="Open and view full transcript from S3"
                    >
                      <span>Open Transcript</span>
                      <ExternalLink className="w-3 h-3 text-gray-400" />
                    </button>

                    {onDeleteTranscript && (
                      <button
                        type="button"
                        onClick={() => onDeleteTranscript(t.id)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                        title="Delete transcript"
                        aria-label={`Delete ${transcriptName}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="p-8 border border-dashed border-gray-200 rounded-lg text-center bg-gray-50/50">
            <FileText className="w-6 h-6 text-gray-400 mx-auto mb-2" />
            <p className="text-xs font-semibold text-gray-700">
              No transcripts yet
            </p>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto leading-relaxed">
              Click <span className="font-medium text-gray-900">Generate Transcripts</span> above to transcribe the audio recordings for this meeting.
            </p>
          </div>
        )}
      </div>

      {/* Full Transcript Viewer Modal */}
      {selectedTranscript && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-2xs"
          role="dialog"
          aria-modal="true"
          onClick={() => setSelectedTranscript(null)}
        >
          <div
            className="w-full max-w-2xl bg-white border border-gray-200 rounded-xl shadow-2xl p-6 max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-3 border-b border-gray-100">
              <div>
                <h3 className="text-sm md:text-base font-semibold text-gray-900">
                  {selectedTranscript.name || selectedTranscript.original_filename || 'Meeting Transcript'}
                </h3>
                <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                  <span>Source: {selectedTranscript.originalAudioFilename || selectedTranscript.original_audio_filename || 'Audio Recording'}</span>
                  <span>•</span>
                  <span>{selectedTranscript.timestamp || 'Today'}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedTranscript(null)}
                className="p-1 text-gray-400 hover:text-gray-700 rounded-md hover:bg-gray-100 transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto py-4 text-xs md:text-sm text-gray-800 leading-relaxed font-sans whitespace-pre-wrap select-text">
              {isLoadingContent ? (
                <div className="flex items-center justify-center py-12 gap-2 text-gray-500 text-xs">
                  <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                  <span>Loading transcript from S3...</span>
                </div>
              ) : selectedTranscript.text ? (
                selectedTranscript.text
              ) : (
                <p className="text-gray-400 italic">Empty transcript content.</p>
              )}
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
              <button
                type="button"
                onClick={() => handleCopy(selectedTranscript.text)}
                disabled={!selectedTranscript.text}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 active:bg-gray-100 transition-colors cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Text</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => setSelectedTranscript(null)}
                className="px-4 py-1.5 text-xs font-medium text-white bg-gray-900 hover:bg-black rounded-md transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
