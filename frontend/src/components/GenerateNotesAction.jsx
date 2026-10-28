import { Sparkles, Loader2, Info, X } from 'lucide-react'

/**
 * Generate Notes Action — Third Section of the Main Workspace.
 * - Placed directly below the transcript input and before the Meeting Notes card
 * - Enabled when transcript text exists OR at least one saved audio recording exists
 * - Shows loading state on click and brief frontend demo notification
 */
export default function GenerateNotesAction({
  canGenerate,
  isGenerating,
  onGenerateNotes,
  demoNotice,
  onDismissNotice,
}) {
  return (
    <div className="space-y-3">
      {/* Primary Action Button Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-white border border-gray-200 rounded-xl shadow-2xs">
        <p className="text-xs text-gray-400 text-center sm:text-left">
          {canGenerate
            ? 'Input ready. Click Generate Notes to process this meeting.'
            : 'Add a transcript or save an audio recording to generate notes.'}
        </p>

        <button
          type="button"
          onClick={onGenerateNotes}
          disabled={!canGenerate || isGenerating}
          className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs md:text-sm font-medium transition-all shadow-2xs ${
            canGenerate && !isGenerating
              ? 'bg-gray-900 text-white hover:bg-black active:bg-gray-800 cursor-pointer'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
          }`}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
              <span>Processing Meeting...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-white" />
              <span>Generate Notes</span>
            </>
          )}
        </button>
      </div>

      {/* Brief Frontend Demo Notice */}
      {demoNotice && (
        <div className="p-3.5 bg-gray-50 border border-gray-200 rounded-xl flex items-start justify-between gap-3 text-xs text-gray-600 animate-fadeIn">
          <div className="flex items-start gap-2.5">
            <Info className="w-4 h-4 shrink-0 text-gray-500 mt-0.5" />
            <div>
              <p className="font-semibold text-gray-900">
                Frontend Demonstration Only
              </p>
              <p className="mt-0.5 text-gray-500 leading-relaxed">
                Backend integration is not implemented. In a production deployment, this action sends your audio recordings and transcript to the backend for Whisper speech transcription and AI note generation.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onDismissNotice}
            className="p-1 text-gray-400 hover:text-gray-700 rounded transition-colors shrink-0"
            aria-label="Dismiss notice"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
