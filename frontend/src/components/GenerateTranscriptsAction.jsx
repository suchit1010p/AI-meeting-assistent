import { Sparkles, Loader2, FileAudio, CheckCircle2, AlertCircle } from 'lucide-react'

/**
 * Generate Transcripts Action — placed directly below the Meeting Audio Card.
 * Allows transcribing all audio files for the selected meeting using Deepgram Nova-3.
 */
export default function GenerateTranscriptsAction({
  canGenerate,
  isGenerating,
  onGenerateTranscripts,
  audioCount = 0,
  transcriptCount = 0,
  statusMessage = null,
  errorMessage = null,
}) {
  return (
    <div className="space-y-2.5">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-white border border-gray-200 rounded-xl shadow-2xs">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-700 shrink-0">
            <FileAudio className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-gray-900 leading-tight">
              Audio Transcription
            </p>
            <p className="text-[11px] text-gray-500 mt-0.5">
              {audioCount === 0
                ? 'Record or upload audio above to enable transcription.'
                : transcriptCount > 0
                ? `${audioCount} audio file(s) available • ${transcriptCount} transcript(s) generated`
                : `${audioCount} audio file(s) ready to transcribe (supports English, Hindi, Gujarati)`}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onGenerateTranscripts}
          disabled={!canGenerate || isGenerating}
          className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all shadow-2xs shrink-0 ${
            canGenerate && !isGenerating
              ? 'bg-gray-900 text-white hover:bg-black active:bg-gray-800 cursor-pointer'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
          }`}
          title={!canGenerate ? 'Record audio first' : 'Transcribe all audio files with Deepgram'}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />
              <span>Transcribing with Deepgram...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-white" />
              <span>{transcriptCount > 0 ? 'Regenerate Transcripts' : 'Generate Transcripts'}</span>
            </>
          )}
        </button>
      </div>

      {/* Success Status Message */}
      {statusMessage && !isGenerating && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-xs text-emerald-800">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && !isGenerating && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between gap-2 text-xs text-red-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={onGenerateTranscripts}
            className="text-xs font-medium underline hover:text-red-950 shrink-0"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  )
}
