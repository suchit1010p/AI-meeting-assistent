import { useState } from 'react'
import {
  FileText,
  Trash2,
  ExternalLink,
  Plus,
  Send,
  X,
  Copy,
  Check,
  AlignLeft,
} from 'lucide-react'

/**
 * Meeting Transcript Card — Second Section of the Main Workspace.
 * Redesigned to match MeetingAudioCard:
 * - Card Header: Document icon, "Meeting Transcript", supporting text
 * - Input Area: 1 input text box with Submit button
 * - Submitting generates a transcript item and displays it below as a list, matching the audio file list
 */
export default function MeetingTranscriptCard({
  transcripts = [],
  onSubmitTranscript,
  onDeleteTranscript,
}) {
  const [inputText, setInputText] = useState('')
  const [viewingTranscript, setViewingTranscript] = useState(null)
  const [copied, setCopied] = useState(false)

  const characterCount = inputText.length
  const wordCount = inputText.trim() ? inputText.trim().split(/\s+/).length : 0
  const canSubmit = inputText.trim().length > 0

  const handleInsertSample = () => {
    setInputText(
      `Sarah: Let's review the Q4 roadmap priorities. The main focus is completing the audio recording pipeline and latency reduction for real-time transcription.
David: On the frontend, we have implemented the pure white minimal interface. The MediaRecorder API is capturing local blobs without issues.
Sarah: Excellent. How are we handling long recordings? Is there memory pressure?
David: We release Object URLs when recordings are discarded or replaced to avoid memory leaks.`
    )
  }

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!canSubmit) return

    const trimmed = inputText.trim()
    const now = new Date()
    const timeFormatted =
      now.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      }) + ' • Today'

    const newTranscript = {
      id: `trans-${Date.now()}`,
      name: `Transcript ${transcripts.length + 1}`,
      text: trimmed,
      preview: trimmed.slice(0, 140) + (trimmed.length > 140 ? '...' : ''),
      wordCount: trimmed.split(/\s+/).length,
      charCount: trimmed.length,
      timestamp: timeFormatted,
    }

    onSubmitTranscript(newTranscript)
    setInputText('')
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
              Meeting Transcript
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Enter or paste transcript text for this meeting.
            </p>
          </div>
        </div>

        {/* Right Header action */}
        {characterCount === 0 && (
          <button
            type="button"
            onClick={handleInsertSample}
            className="text-[11px] text-gray-400 hover:text-gray-700 underline transition-colors self-start sm:self-auto"
          >
            Insert sample
          </button>
        )}
      </div>

      {/* Input Text Box & Submit Controls */}
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <div className="relative">
          <label htmlFor="transcript-input-box" className="sr-only">
            Meeting Transcript Input
          </label>
          <textarea
            id="transcript-input-box"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Paste or type your meeting transcript here..."
            className="w-full h-[120px] p-3.5 text-xs md:text-sm bg-white border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 transition-all resize-y leading-relaxed"
          />
        </div>

        {/* Action Row below Text Box */}
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-gray-400 flex items-center gap-2">
            <span>
              {characterCount.toLocaleString()}{' '}
              {characterCount === 1 ? 'char' : 'chars'}
            </span>
            {wordCount > 0 && (
              <span>
                • {wordCount.toLocaleString()}{' '}
                {wordCount === 1 ? 'word' : 'words'}
              </span>
            )}
            {characterCount > 0 && (
              <button
                type="button"
                onClick={() => setInputText('')}
                className="ml-2 text-gray-400 hover:text-gray-700 underline text-xs"
              >
                Clear
              </button>
            )}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all shadow-2xs ${
              canSubmit
                ? 'bg-gray-900 text-white hover:bg-black active:bg-gray-800 cursor-pointer'
                : 'bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed'
            }`}
          >
            <Send className="w-3.5 h-3.5" />
            <span>Submit Transcript</span>
          </button>
        </div>
      </form>

      {/* Previously Submitted Transcripts List Subsection (same as audio list) */}
      <div className="mt-5">
        <div className="flex items-center justify-between mb-2.5">
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Transcripts
          </h4>
          <span className="text-[11px] text-gray-400 font-medium">
            {transcripts.length}{' '}
            {transcripts.length === 1 ? 'transcript' : 'transcripts'}
          </span>
        </div>

        {transcripts.length > 0 ? (
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden bg-white">
            {transcripts.map((t) => (
              <div
                key={t.id}
                className="p-3 flex items-center justify-between gap-3 hover:bg-gray-50/60 transition-colors"
              >
                {/* Left: Icon & Details */}
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="w-7 h-7 rounded-md bg-gray-100 text-gray-700 flex items-center justify-center shrink-0">
                    <FileText className="w-3.5 h-3.5" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium text-gray-900 truncate">
                        {t.name}
                      </p>
                      <span className="text-[10px] text-gray-400 font-mono">
                        {t.wordCount || (t.text ? t.text.split(/\s+/).length : 0)} words
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-500 truncate mt-0.5 max-w-lg">
                      {t.preview || t.text}
                    </p>
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-400 mt-0.5">
                      <span>{t.timestamp || 'Today'}</span>
                    </div>
                  </div>
                </div>

                {/* Right: View & Delete Actions */}
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => setViewingTranscript(t)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 rounded-md transition-colors"
                    title="View full transcript"
                  >
                    <span>View</span>
                    <ExternalLink className="w-3 h-3 text-gray-400" />
                  </button>

                  {onDeleteTranscript && (
                    <button
                      type="button"
                      onClick={() => onDeleteTranscript(t.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors shrink-0"
                      title="Delete transcript"
                      aria-label={`Delete ${t.name}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 border border-dashed border-gray-200 rounded-lg text-center bg-gray-50/50">
            <FileText className="w-4 h-4 text-gray-400 mx-auto mb-1.5" />
            <p className="text-xs text-gray-500">
              No transcripts yet. Enter text and submit to add a transcript to this meeting.
            </p>
          </div>
        )}
      </div>

      {/* Full Transcript Viewer Modal */}
      {viewingTranscript && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-2xs"
          role="dialog"
          aria-modal="true"
          onClick={() => setViewingTranscript(null)}
        >
          <div
            className="w-full max-w-xl bg-white border border-gray-200 rounded-xl shadow-xl p-6 max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-3 border-b border-gray-100">
              <div>
                <h3 className="text-sm md:text-base font-semibold text-gray-900">
                  {viewingTranscript.name}
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  {viewingTranscript.timestamp} •{' '}
                  {viewingTranscript.wordCount ||
                    (viewingTranscript.text
                      ? viewingTranscript.text.split(/\s+/).length
                      : 0)}{' '}
                  words
                </p>
              </div>
              <button
                type="button"
                onClick={() => setViewingTranscript(null)}
                className="p-1 text-gray-400 hover:text-gray-700 rounded-md hover:bg-gray-100"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto py-4 text-xs md:text-sm text-gray-800 leading-relaxed font-sans whitespace-pre-line">
              {viewingTranscript.text}
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
              <button
                type="button"
                onClick={() => handleCopy(viewingTranscript.text)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
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
                onClick={() => setViewingTranscript(null)}
                className="px-4 py-1.5 text-xs font-medium text-white bg-gray-900 hover:bg-black rounded-md transition-colors"
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
