import { Loader2, Info, ArrowLeft, Plus, Check } from 'lucide-react'

/**
 * Renders the processing simulation and the honest demo result placeholder.
 * Does not produce fake AI summaries or simulate non-existent AI output.
 */
export default function ProcessingState({
  isProcessing,
  transcript,
  audioData,
  onResetWorkspace,
  onSaveToMockHistory,
}) {
  if (isProcessing) {
    return (
      <div className="w-full max-w-[760px] mx-auto px-4 md:px-6 py-20 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-full bg-gray-50 border border-gray-200 flex items-center justify-center mb-4">
          <Loader2 className="w-6 h-6 text-gray-900 animate-spin" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900">
          Preparing your meeting...
        </h3>
        <p className="mt-1 text-sm text-gray-500 max-w-sm">
          Bundling your meeting input and validating media payload for the processing pipeline.
        </p>
      </div>
    )
  }

  return (
    <div className="w-full max-w-[760px] mx-auto px-4 md:px-6 py-10 md:py-16">
      {/* Notice Card */}
      <div className="p-6 md:p-8 bg-white border border-gray-200 rounded-xl shadow-2xs">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-gray-100 border border-gray-200 flex items-center justify-center shrink-0 text-gray-700">
            <Info className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-gray-100 text-[11px] font-medium text-gray-700 mb-2">
              Frontend Milestone Demo
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              Backend Integration Not Implemented
            </h3>
            <p className="mt-2 text-sm text-gray-600 leading-relaxed">
              This milestone is strictly frontend only. In a complete deployment, this step sends your meeting payload to the backend service for secure AWS S3 storage, Whisper speech transcription, and LLM meeting note generation.
            </p>

            {/* Input Payload Summary */}
            <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2.5">
                Captured Meeting Payload
              </h4>
              <ul className="space-y-1.5 text-xs text-gray-600">
                <li className="flex items-center justify-between">
                  <span>Transcript text:</span>
                  <span className="font-mono text-gray-900">
                    {transcript.trim()
                      ? `${transcript.length} characters (${transcript.trim().split(/\s+/).length} words)`
                      : 'None provided'}
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Audio recording:</span>
                  <span className="font-mono text-gray-900">
                    {audioData
                      ? `Ready (${audioData.duration})`
                      : 'None recorded'}
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Status:</span>
                  <span className="font-medium text-emerald-600 flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" /> Client input validated
                  </span>
                </li>
              </ul>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex flex-wrap items-center gap-3">
              {onSaveToMockHistory && (
                <button
                  type="button"
                  onClick={onSaveToMockHistory}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-900 hover:bg-black text-white text-xs font-medium rounded-lg transition-colors shadow-2xs"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Save as Demo Meeting in Sidebar</span>
                </button>
              )}
              <button
                type="button"
                onClick={onResetWorkspace}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-medium rounded-lg transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Return to New Meeting</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
