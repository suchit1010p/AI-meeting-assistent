import { useState, useRef, useEffect } from 'react'
import { Mic, Square, AlertCircle, RefreshCw } from 'lucide-react'

/**
 * Functional browser audio recorder using the MediaRecorder API.
 * Handles microphone permissions, real-time duration counting, track cleanup,
 * and passes the recorded local Blob and duration back to the parent.
 */
export default function AudioRecorder({ onRecordingComplete, onRecordingStateChange }) {
  const [isRecording, setIsRecording] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [errorMessage, setErrorMessage] = useState(null)
  const [audioLevel, setAudioLevel] = useState(0)

  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const timerIntervalRef = useRef(null)
  const audioChunksRef = useRef([])
  const animationFrameRef = useRef(null)
  const audioContextRef = useRef(null)

  // Notify parent of recording status change
  useEffect(() => {
    onRecordingStateChange?.(isRecording)
  }, [isRecording, onRecordingStateChange])

  // Clean up all resources when component unmounts
  useEffect(() => {
    return () => {
      cleanupMedia()
    }
  }, [])

  const cleanupMedia = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current)
      timerIntervalRef.current = null
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        audioContextRef.current.close()
      } catch {
        // Ignore close error
      }
      audioContextRef.current = null
    }
  }

  // Format seconds to mm:ss
  const formatTime = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const startRecording = async () => {
    setErrorMessage(null)
    setElapsedSeconds(0)
    audioChunksRef.current = []

    // 1. Check browser support
    if (
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia ||
      typeof window.MediaRecorder === 'undefined'
    ) {
      setErrorMessage(
        'Audio recording is not supported in this browser. Please use Chrome, Edge, Safari, or Firefox.'
      )
      return
    }

    try {
      // 2. Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // 3. Optional: Web Audio API analyzer for minimal live visualizer
      try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext
        if (AudioContextClass) {
          const ctx = new AudioContextClass()
          audioContextRef.current = ctx
          const source = ctx.createMediaStreamSource(stream)
          const analyser = ctx.createAnalyser()
          analyser.fftSize = 64
          source.connect(analyser)

          const dataArray = new Uint8Array(analyser.frequencyBinCount)
          const updateLevel = () => {
            analyser.getByteFrequencyData(dataArray)
            let sum = 0
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i]
            }
            const average = sum / dataArray.length
            setAudioLevel(Math.min(100, Math.round((average / 128) * 100)))
            animationFrameRef.current = requestAnimationFrame(updateLevel)
          }
          updateLevel()
        }
      } catch (e) {
        console.warn('Audio analyzer initialization skipped:', e)
      }

      // 4. Determine supported mime type
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        '',
      ].find((type) => (type ? MediaRecorder.isTypeSupported(type) : true))

      const options = mimeType ? { mimeType } : undefined
      const recorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const recordedBlob = new Blob(audioChunksRef.current, {
          type: mimeType || 'audio/webm',
        })
        const audioUrl = URL.createObjectURL(recordedBlob)

        // Capture final duration string
        const durationFormatted = formatTime(elapsedSeconds)

        // Clean up tracks
        cleanupMedia()
        setIsRecording(false)

        // Notify parent
        onRecordingComplete?.({
          blob: recordedBlob,
          url: audioUrl,
          duration: durationFormatted,
          durationSeconds: elapsedSeconds,
        })
      }

      // 5. Start MediaRecorder
      recorder.start(250) // collect data in 250ms chunks
      setIsRecording(true)

      // 6. Start elapsed timer
      timerIntervalRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1)
      }, 1000)
    } catch (err) {
      console.error('Error accessing microphone:', err)
      cleanupMedia()
      setIsRecording(false)

      if (
        err.name === 'NotAllowedError' ||
        err.name === 'PermissionDeniedError'
      ) {
        setErrorMessage(
          'Microphone permission was denied. Please allow microphone access in your browser settings to record audio.'
        )
      } else if (err.name === 'NotFoundError') {
        setErrorMessage(
          'No microphone device was found. Please connect a microphone and try again.'
        )
      } else {
        setErrorMessage(`Unable to access microphone: ${err.message || 'Unknown error'}`)
      }
    }
  }

  const stopRecording = () => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== 'inactive'
    ) {
      mediaRecorderRef.current.stop()
    } else {
      cleanupMedia()
      setIsRecording(false)
    }
  }

  return (
    <div className="w-full">
      {/* Error Notice */}
      {errorMessage && (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5 text-xs text-red-700">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">Microphone Error</p>
            <p className="mt-0.5 text-red-600 leading-relaxed">{errorMessage}</p>
          </div>
          <button
            type="button"
            onClick={startRecording}
            className="shrink-0 flex items-center gap-1 font-medium text-red-700 hover:text-red-900 underline text-xs ml-2"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {/* Recording Control Bar */}
      {!isRecording ? (
        <button
          type="button"
          onClick={startRecording}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 active:bg-gray-100 transition-all shadow-2xs cursor-pointer"
        >
          <Mic className="w-4 h-4 text-gray-700" />
          <span>Record Audio</span>
        </button>
      ) : (
        <div className="flex items-center gap-3 p-2 px-3 bg-gray-50 border border-gray-200 rounded-lg max-w-sm">
          {/* Pulsing indicator */}
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-600"></span>
            </span>
            <span className="text-xs font-mono font-medium text-gray-900 tracking-wider">
              {formatTime(elapsedSeconds)}
            </span>
          </div>

          {/* Minimal live waveform bars */}
          <div className="flex items-center gap-0.5 h-4 px-2 border-l border-r border-gray-200 flex-1 justify-center">
            {[0.4, 0.7, 1.0, 0.8, 0.5, 0.9, 0.6].map((multiplier, idx) => {
              const heightPercent = Math.max(
                20,
                Math.min(100, Math.round((audioLevel || 20) * multiplier))
              )
              return (
                <span
                  key={idx}
                  className="w-1 bg-red-500/70 rounded-full transition-all duration-75"
                  style={{ height: `${heightPercent}%` }}
                />
              )
            })}
          </div>

          {/* Stop Button */}
          <button
            type="button"
            onClick={stopRecording}
            className="flex items-center gap-1.5 px-3 py-1 bg-gray-900 hover:bg-black text-white text-xs font-medium rounded-md transition-colors"
          >
            <Square className="w-3 h-3 fill-current" />
            <span>Stop</span>
          </button>
        </div>
      )}
    </div>
  )
}
