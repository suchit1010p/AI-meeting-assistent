import { X, FileText } from 'lucide-react'

/**
 * Transcript Text Input — Second Section of the Main Workspace.
 * - Compact height (140-180px initial height on desktop)
 * - White background, subtle border, rounded corners
 * - Character count and clear-text action
 * - No introductory headings or subtitles
 */
export default function MeetingTranscriptInput({
  transcript = '',
  onChange,
}) {
  const characterCount = transcript.length
  const wordCount = transcript.trim() ? transcript.trim().split(/\s+/).length : 0

  const handleClear = () => {
    onChange('')
  }

  const handleInsertSample = () => {
    onChange(
      `Sarah: Let's review the Q4 roadmap priorities. The main focus is completing the audio recording pipeline and latency reduction for real-time transcription.
David: On the frontend, we have implemented the pure white minimal interface. The MediaRecorder API is capturing local blobs without issues.
Sarah: Excellent. How are we handling long recordings? Is there memory pressure?
David: We release Object URLs when recordings are discarded or replaced to avoid memory leaks. We also enforce chunking before backend uploads.`
    )
  }

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-4 md:p-5 shadow-2xs">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-2.5 mb-2 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-500" />
          <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
            Meeting Transcript
          </h3>
        </div>

        {characterCount === 0 && (
          <button
            type="button"
            onClick={handleInsertSample}
            className="text-[11px] text-gray-400 hover:text-gray-700 underline transition-colors"
          >
            Insert sample
          </button>
        )}
      </div>

      {/* Compact Textarea */}
      <div className="relative">
        <label htmlFor="transcript-editor" className="sr-only">
          Meeting Transcript
        </label>
        <textarea
          id="transcript-editor"
          value={transcript}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Paste or type your meeting transcript here..."
          className="w-full h-[150px] p-3.5 text-xs md:text-sm bg-white border border-gray-200 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 transition-all resize-y leading-relaxed"
        />
      </div>

      {/* Footer bar with character count and clear-text */}
      <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-2">
          <span>
            {characterCount.toLocaleString()}{' '}
            {characterCount === 1 ? 'character' : 'characters'}
          </span>
          {wordCount > 0 && (
            <span>
              • {wordCount.toLocaleString()} {wordCount === 1 ? 'word' : 'words'}
            </span>
          )}
        </div>

        {characterCount > 0 && (
          <button
            type="button"
            onClick={handleClear}
            className="flex items-center gap-1 text-gray-400 hover:text-gray-700 transition-colors py-0.5 px-1.5 rounded hover:bg-gray-100"
            aria-label="Clear transcript text"
          >
            <X className="w-3.5 h-3.5" />
            <span>Clear text</span>
          </button>
        )}
      </div>
    </section>
  )
}
