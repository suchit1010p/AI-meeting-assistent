import { Sparkles, Loader2, AlertCircle } from 'lucide-react'

/**
 * Generate Notes Action — Third Section of the Main Workspace.
 * - Placed directly below the transcript card and before the Meeting Notes card
 * - Enabled when at least one transcript exists for the meeting
 * - Calls the Groq LLM API via Django backend to generate structured meeting notes
 */
export default function GenerateNotesAction({
  canGenerate,
  isGenerating,
  onGenerateNotes,
  hasNotes = false,
  errorMessage = null,
}) {
  return (
    <div className="space-y-2.5">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-white border border-gray-200 rounded-xl shadow-2xs">
        <p className="text-xs text-gray-500 text-center sm:text-left">
          {canGenerate
            ? hasNotes
              ? 'Transcripts ready. Click Regenerate Notes to re-analyze this meeting with Groq LLM.'
              : 'Transcripts ready. Click Generate Notes to produce structured meeting notes with Groq LLM.'
            : 'Generate transcripts first before generating AI meeting notes.'}
        </p>

        <button
          type="button"
          onClick={onGenerateNotes}
          disabled={!canGenerate || isGenerating}
          className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs md:text-sm font-medium transition-all shadow-2xs shrink-0 ${
            canGenerate && !isGenerating
              ? 'bg-gray-900 text-white hover:bg-black active:bg-gray-800 cursor-pointer'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
          }`}
          title={!canGenerate ? 'Transcribe audio recordings first' : 'Analyze transcripts with Groq LLM'}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
              <span>Analyzing with Groq LLM...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-white" />
              <span>{hasNotes ? 'Regenerate Notes' : 'Generate Notes'}</span>
            </>
          )}
        </button>
      </div>

      {/* Error Message */}
      {errorMessage && !isGenerating && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between gap-2 text-xs text-red-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={onGenerateNotes}
            className="text-xs font-medium underline hover:text-red-950 shrink-0"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  )
}
