import { useState } from 'react'
import { Sparkles, X, FileText, ArrowRight, CornerDownLeft } from 'lucide-react'
import AudioRecorder from './AudioRecorder'
import AudioPreview from './AudioPreview'

/**
 * Main input workspace for capturing a new meeting:
 * - Transcript multiline text area with character & word counts
 * - Functional audio recording and preview
 * - "Generate Notes" primary action
 */
export default function MeetingInput({
  transcript,
  onTranscriptChange,
  audioData, // { blob, url, duration, durationSeconds } | null
  onAudioRecorded,
  onAudioDiscard,
  onGenerateNotes,
  isRecordingAudio,
  setIsRecordingAudio,
}) {
  const characterCount = transcript.length
  const wordCount = transcript.trim() ? transcript.trim().split(/\s+/).length : 0

  const hasText = transcript.trim().length > 0
  const hasAudio = audioData !== null
  const canGenerate = (hasText || hasAudio) && !isRecordingAudio

  // Quick sample transcript helper for testing ease
  const insertSampleText = () => {
    onTranscriptChange(
      `Alex: Good morning team, let's review the launch checklist for MeetNote AI.
Elena: The frontend interface is fully styled with pure white backgrounds, subtle gray borders, and Lucide icons.
Alex: Has the browser audio recording API been validated?
David: Yes, MediaRecorder captures voice input locally as audio blobs, with live duration timers and clean cleanup on discard.
Alex: Perfect. Let's package this frontend milestone for user review.`
    )
  }

  return (
    <div className="w-full max-w-[760px] mx-auto px-4 md:px-6 py-8 md:py-12">
      {/* Workspace Header Title & Description */}
      <div className="mb-8">
        <h2 className="text-2xl md:text-3xl font-semibold text-gray-900 tracking-tight">
          What would you like to capture?
        </h2>
        <p className="mt-2 text-sm md:text-base text-gray-500 leading-relaxed">
          Paste a meeting transcript or record a conversation to generate meeting notes.
        </p>
      </div>

      {/* Main Input Card */}
      <div className="space-y-5">
        {/* Multiline Transcript Text Area */}
        <div className="relative group">
          <label htmlFor="transcript-input" className="sr-only">
            Meeting Transcript
          </label>
          <textarea
            id="transcript-input"
            rows={8}
            value={transcript}
            onChange={(e) => onTranscriptChange(e.target.value)}
            placeholder="Paste your meeting transcript here..."
            className="w-full p-4 md:p-5 text-sm md:text-base bg-white border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 transition-all resize-y min-h-[180px] shadow-2xs leading-relaxed"
          />

          {/* Action Row inside / below Textarea: Character counter & Clear */}
          <div className="flex items-center justify-between text-xs text-gray-400 px-1 pt-1.5">
            <div className="flex items-center gap-3">
              <span>
                {characterCount.toLocaleString()} {characterCount === 1 ? 'character' : 'characters'}
              </span>
              {wordCount > 0 && (
                <span>
                  • {wordCount.toLocaleString()} {wordCount === 1 ? 'word' : 'words'}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {characterCount === 0 && (
                <button
                  type="button"
                  onClick={insertSampleText}
                  className="text-gray-400 hover:text-gray-700 underline text-xs font-normal transition-colors"
                >
                  Insert sample transcript
                </button>
              )}
              {characterCount > 0 && (
                <button
                  type="button"
                  onClick={() => onTranscriptChange('')}
                  className="flex items-center gap-1 text-gray-400 hover:text-gray-700 transition-colors py-0.5 px-1.5 rounded hover:bg-gray-100"
                  aria-label="Clear transcript text"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Clear text</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Audio Recording / Preview Area */}
        <div className="pt-2">
          {!audioData ? (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white border border-gray-200 rounded-xl shadow-2xs">
              <div>
                <p className="text-xs md:text-sm font-medium text-gray-900">
                  Record Meeting Audio
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Capture your microphone directly in the browser
                </p>
              </div>
              <AudioRecorder
                onRecordingComplete={onAudioRecorded}
                onRecordingStateChange={setIsRecordingAudio}
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-gray-500 px-1">
                <span className="font-medium text-gray-700">Audio Ready for Processing</span>
                <span className="text-gray-400">Duration: {audioData.duration}</span>
              </div>
              <AudioPreview
                audioUrl={audioData.url}
                duration={audioData.duration}
                onDiscard={onAudioDiscard}
                title="Recorded Meeting Audio"
              />
            </div>
          )}
        </div>

        {/* Bottom Action Footer */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 text-center sm:text-left">
            {hasText && hasAudio
              ? 'Both transcript and audio recorded will be processed.'
              : hasText
              ? 'Ready to process pasted transcript.'
              : hasAudio
              ? 'Ready to process recorded audio.'
              : 'Add a transcript or record audio to enable generation.'}
          </p>

          <button
            type="button"
            onClick={onGenerateNotes}
            disabled={!canGenerate}
            className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white transition-all shadow-2xs ${
              canGenerate
                ? 'bg-gray-900 hover:bg-black active:bg-gray-800 cursor-pointer'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed opacity-70'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate Notes</span>
          </button>
        </div>
      </div>
    </div>
  )
}
