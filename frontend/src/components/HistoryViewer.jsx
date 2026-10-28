import { useState } from 'react'
import {
  Volume2,
  FileText,
  Sparkles,
  Copy,
  Check,
  Calendar,
  Clock,
  ArrowLeft,
  ExternalLink,
} from 'lucide-react'
import AudioPreview from './AudioPreview'

/**
 * Read-only viewer for historical meetings selected from the sidebar.
 * Clearly marks content as mock data and allows switching between Audio, Transcript, and Summary.
 */
export default function HistoryViewer({
  meeting,
  selectedTab, // 'overview' | 'audio' | 'transcript' | 'summary'
  onTabChange,
  onNewMeeting,
}) {
  const [copied, setCopied] = useState(false)

  if (!meeting) return null

  const handleCopyTranscript = async () => {
    if (meeting.transcript) {
      await navigator.clipboard.writeText(meeting.transcript)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const activeTab = selectedTab || 'overview'

  return (
    <div className="w-full max-w-[760px] mx-auto px-4 md:px-6 py-8 md:py-10">
      {/* Top Banner indicating Mock Record */}
      <div className="mb-6 p-3 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-between text-xs text-gray-500">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
          Viewing sample history record (Read-only mock data)
        </span>
        <button
          type="button"
          onClick={onNewMeeting}
          className="text-gray-900 hover:underline font-medium flex items-center gap-1"
        >
          <ArrowLeft className="w-3 h-3" />
          <span>New Meeting</span>
        </button>
      </div>

      {/* Meeting Title & Meta */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 tracking-tight">
          {meeting.title}
        </h2>
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-gray-400" />
            {meeting.date}
          </span>
          {meeting.audioDuration && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-gray-400" />
              {meeting.audioDuration}
            </span>
          )}
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          type="button"
          onClick={() => onTabChange('overview')}
          className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'overview'
              ? 'border-gray-900 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Overview
        </button>
        <button
          type="button"
          onClick={() => onTabChange('transcript')}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'transcript'
              ? 'border-gray-900 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Transcript</span>
        </button>
        <button
          type="button"
          onClick={() => onTabChange('summary')}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'summary'
              ? 'border-gray-900 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Summary</span>
        </button>
        <button
          type="button"
          onClick={() => onTabChange('audio')}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'audio'
              ? 'border-gray-900 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Volume2 className="w-3.5 h-3.5" />
          <span>Audio</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div
              onClick={() => onTabChange('transcript')}
              className="p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-400 hover:shadow-2xs transition-all cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700 mb-3 group-hover:bg-gray-900 group-hover:text-white transition-colors">
                <FileText className="w-4 h-4" />
              </div>
              <h4 className="text-sm font-semibold text-gray-900">Transcript</h4>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {meeting.transcript || 'No transcript recorded.'}
              </p>
            </div>

            <div
              onClick={() => onTabChange('summary')}
              className="p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-400 hover:shadow-2xs transition-all cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700 mb-3 group-hover:bg-gray-900 group-hover:text-white transition-colors">
                <Sparkles className="w-4 h-4" />
              </div>
              <h4 className="text-sm font-semibold text-gray-900">Summary</h4>
              <p className="text-xs text-gray-500 mt-1">
                {meeting.summary ? 'Summary and action items ready' : 'Pending summary'}
              </p>
            </div>

            <div
              onClick={() => onTabChange('audio')}
              className="p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-400 hover:shadow-2xs transition-all cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700 mb-3 group-hover:bg-gray-900 group-hover:text-white transition-colors">
                <Volume2 className="w-4 h-4" />
              </div>
              <h4 className="text-sm font-semibold text-gray-900">Audio</h4>
              <p className="text-xs text-gray-500 mt-1">
                {meeting.audioDuration ? `${meeting.audioDuration} recording` : 'No audio attached'}
              </p>
            </div>
          </div>
        )}

        {/* Transcript Tab */}
        {activeTab === 'transcript' && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 md:p-6 shadow-2xs">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
              <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Full Transcript
              </span>
              <button
                type="button"
                onClick={handleCopyTranscript}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 active:bg-gray-100 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>

            <div className="text-sm text-gray-800 leading-relaxed font-sans whitespace-pre-line">
              {meeting.transcript}
            </div>
          </div>
        )}

        {/* Summary Tab */}
        {activeTab === 'summary' && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 md:p-6 shadow-2xs">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
              <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Meeting Summary & Notes
              </span>
              <span className="text-[11px] text-gray-400">Mock AI output</span>
            </div>

            {meeting.summary ? (
              <div className="text-sm text-gray-800 leading-relaxed space-y-4">
                {meeting.summary.split('\n\n').map((paragraph, idx) => {
                  if (paragraph.startsWith('### ')) {
                    return (
                      <h4
                        key={idx}
                        className="text-sm font-semibold text-gray-900 pt-2 border-t border-gray-100 first:border-t-0 first:pt-0"
                      >
                        {paragraph.replace('### ', '')}
                      </h4>
                    )
                  }
                  if (paragraph.startsWith('- [ ]') || paragraph.startsWith('- ')) {
                    return (
                      <ul key={idx} className="space-y-1.5 pl-1">
                        {paragraph.split('\n').map((item, itemIdx) => (
                          <li
                            key={itemIdx}
                            className="text-xs md:text-sm text-gray-700 flex items-start gap-2"
                          >
                            <span className="text-gray-400 mt-1.5">•</span>
                            <span>{item.replace(/^- \[[ x]\] |- /, '')}</span>
                          </li>
                        ))}
                      </ul>
                    )
                  }
                  return (
                    <p key={idx} className="text-sm text-gray-700">
                      {paragraph}
                    </p>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic">
                No summary generated for this meeting.
              </p>
            )}
          </div>
        )}

        {/* Audio Tab */}
        {activeTab === 'audio' && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 md:p-6 shadow-2xs space-y-4">
            <div className="pb-3 border-b border-gray-100 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Audio Recording
              </span>
              <span className="text-xs text-gray-400">
                Duration: {meeting.audioDuration || 'Not available'}
              </span>
            </div>

            {meeting.audioUrl ? (
              <AudioPreview
                audioUrl={meeting.audioUrl}
                duration={meeting.audioDuration}
                readOnly
                title={`${meeting.title} - Audio`}
              />
            ) : (
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500 space-y-2">
                <p className="font-medium text-gray-700">
                  Audio Storage Notice
                </p>
                <p>
                  In this frontend-only demonstration, audio streams from past meetings are not persisted to cloud storage (AWS S3). Live audio recording is functional when capturing a new meeting.
                </p>
                <p className="font-mono text-gray-600">
                  Simulated audio track duration: {meeting.audioDuration || '15:00'}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
