import { useState } from 'react'
import {
  FileText,
  ExternalLink,
  Trash2,
  Clock,
  BookOpen,
  X,
  Copy,
  Check,
} from 'lucide-react'

/**
 * Meeting Notes Card — Fourth Section of the Main Workspace.
 * - Title "Meeting Notes", document icon, subtle divider
 * - List of notes associated with the current meeting session
 * - Displays short title, content preview, timestamp, view button, and delete action
 * - Empty state when no notes exist
 * - Full note viewing dialog modal
 */
export default function MeetingNotesCard({
  notes = [],
  onDeleteNote,
}) {
  const [selectedNote, setSelectedNote] = useState(null)
  const [copied, setCopied] = useState(false)

  const handleCopyContent = async (content) => {
    if (content) {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 shadow-2xs">
      {/* Card Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-700 shrink-0">
            <BookOpen className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 leading-tight">
              Meeting Notes
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Generated notes and action items for this meeting session.
            </p>
          </div>
        </div>

        <span className="text-[11px] text-gray-400 font-medium">
          {notes.length} {notes.length === 1 ? 'note' : 'notes'}
        </span>
      </div>

      {/* Notes List */}
      <div className="mt-4">
        {notes.length > 0 ? (
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden bg-white">
            {notes.map((note) => (
              <div
                key={note.id}
                className="p-4 hover:bg-gray-50/60 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                {/* Note Info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-gray-500 shrink-0" />
                    <h4 className="text-xs font-semibold text-gray-900 truncate">
                      {note.title}
                    </h4>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 line-clamp-2 leading-relaxed">
                    {note.preview || note.content}
                  </p>
                  <div className="mt-2 flex items-center gap-1.5 text-[11px] text-gray-400">
                    <Clock className="w-3 h-3" />
                    <span>{note.timestamp}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <button
                    type="button"
                    onClick={() => setSelectedNote(note)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 active:bg-gray-100 transition-colors"
                  >
                    <span>View Note</span>
                    <ExternalLink className="w-3 h-3 text-gray-400" />
                  </button>

                  {onDeleteNote && (
                    <button
                      type="button"
                      onClick={() => onDeleteNote(note.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                      title="Delete note"
                      aria-label={`Delete note ${note.title}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 border border-dashed border-gray-200 rounded-lg text-center bg-gray-50/50">
            <FileText className="w-5 h-5 text-gray-400 mx-auto mb-2" />
            <p className="text-xs font-medium text-gray-700">
              No notes yet
            </p>
            <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
              Your meeting notes will appear here after processing.
            </p>
          </div>
        )}
      </div>

      {/* Full Note Viewer Modal */}
      {selectedNote && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-2xs"
          role="dialog"
          aria-modal="true"
          onClick={() => setSelectedNote(null)}
        >
          <div
            className="w-full max-w-xl bg-white border border-gray-200 rounded-xl shadow-xl p-6 max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-3 border-b border-gray-100">
              <div>
                <h3 className="text-sm md:text-base font-semibold text-gray-900">
                  {selectedNote.title}
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  {selectedNote.timestamp}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedNote(null)}
                className="p-1 text-gray-400 hover:text-gray-700 rounded-md hover:bg-gray-100"
                aria-label="Close note"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto py-4 text-xs md:text-sm text-gray-800 leading-relaxed font-sans whitespace-pre-line space-y-3">
              {selectedNote.content}
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
              <button
                type="button"
                onClick={() => handleCopyContent(selectedNote.content)}
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
                    <span>Copy Note</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => setSelectedNote(null)}
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
