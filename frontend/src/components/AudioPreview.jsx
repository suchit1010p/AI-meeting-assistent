import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Trash2, Volume2, VolumeX, RotateCcw } from 'lucide-react'

/**
 * Clean audio preview player for recorded audio blobs or sample audio files.
 * Includes play/pause, scrub slider, duration, and discard action.
 */
export default function AudioPreview({
  audioUrl,
  duration,
  onDiscard,
  readOnly = false,
  title = 'Recorded Audio',
}) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [totalDuration, setTotalDuration] = useState(0)
  const [isMuted, setIsMuted] = useState(false)

  const audioRef = useRef(null)

  useEffect(() => {
    // Reset state when audioUrl changes
    setIsPlaying(false)
    setCurrentTime(0)
  }, [audioUrl])

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setTotalDuration(audioRef.current.duration)
    }
  }

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value)
    if (audioRef.current) {
      audioRef.current.currentTime = time
      setCurrentTime(time)
    }
  }

  const handleEnded = () => {
    setIsPlaying(false)
    setCurrentTime(0)
    if (audioRef.current) {
      audioRef.current.currentTime = 0
    }
  }

  const toggleMute = () => {
    if (!audioRef.current) return
    audioRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const formatSeconds = (secs) => {
    if (isNaN(secs) || secs === Infinity) return '00:00'
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="w-full bg-white border border-gray-200 rounded-lg p-3 shadow-2xs">
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
        className="hidden"
      />

      <div className="flex items-center justify-between gap-3">
        {/* Play / Pause Button */}
        <button
          type="button"
          onClick={togglePlay}
          className="w-9 h-9 rounded-lg bg-gray-900 hover:bg-black text-white flex items-center justify-center shrink-0 transition-colors shadow-2xs"
          aria-label={isPlaying ? 'Pause audio' : 'Play audio'}
        >
          {isPlaying ? (
            <Pause className="w-4 h-4 fill-current" />
          ) : (
            <Play className="w-4 h-4 fill-current translate-x-0.5" />
          )}
        </button>

        {/* Audio Information & Scrubber */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span className="font-medium text-gray-800 truncate">{title}</span>
            <span className="font-mono text-[11px] text-gray-400">
              {formatSeconds(currentTime)} /{' '}
              {duration || formatSeconds(totalDuration)}
            </span>
          </div>

          {/* Progress Range Slider */}
          <div className="relative flex items-center">
            <input
              type="range"
              min="0"
              max={totalDuration || 100}
              step="0.05"
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-gray-900"
              aria-label="Audio progress slider"
            />
          </div>
        </div>

        {/* Right Actions: Mute & Discard */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={toggleMute}
            className="p-1.5 text-gray-400 hover:text-gray-750 hover:bg-gray-100 rounded-md transition-colors"
            title={isMuted ? 'Unmute' : 'Mute'}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? (
              <VolumeX className="w-4 h-4" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>

          {!readOnly && onDiscard && (
            <button
              type="button"
              onClick={onDiscard}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              title="Discard recording"
              aria-label="Discard recording"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
