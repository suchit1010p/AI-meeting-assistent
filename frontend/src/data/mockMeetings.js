/**
 * Mock meeting history data for MeetNote AI demonstration.
 * Each meeting session maintains its own recordings, transcripts, and notes.
 */

const mockMeetings = [
  {
    id: "meeting-1",
    title: "Product Planning & Roadmap Q4",
    date: "2026-10-27",
    recordings: [
      {
        id: "rec-1-1",
        name: "Audio Session 1 - Planning",
        duration: "14:20",
        timestamp: "Oct 27, 2026 • 10:30 AM",
        audioUrl: null
      }
    ],
    audioDuration: "14:20",
    audioUrl: null,
    transcripts: [
      {
        id: "trans-1-1",
        name: "Transcript 1",
        text: `Sarah: Let's review the Q4 roadmap priorities. The main focus is completing the audio recording pipeline and latency reduction for real-time transcription.
David: On the frontend, we have implemented the pure white minimal interface. The MediaRecorder API is capturing local blobs without issues.
Sarah: Excellent. How are we handling long recordings? Is there memory pressure?
David: We release Object URLs when recordings are discarded or replaced to avoid memory leaks. We also enforce chunking before backend uploads.
Alex: From the backend side, once integration begins, we will process the stream through Whisper and generate structured action items.
Sarah: Great. Let's aim to have the API contracts finalized by Wednesday so we can start integration testing.`,
        wordCount: 104,
        charCount: 685,
        timestamp: "Oct 27, 2026 • 10:35 AM"
      }
    ],
    transcript: `Sarah: Let's review the Q4 roadmap priorities. The main focus is completing the audio recording pipeline and latency reduction for real-time transcription.
David: On the frontend, we have implemented the pure white minimal interface. The MediaRecorder API is capturing local blobs without issues.
Sarah: Excellent. How are we handling long recordings? Is there memory pressure?
David: We release Object URLs when recordings are discarded or replaced to avoid memory leaks. We also enforce chunking before backend uploads.
Alex: From the backend side, once integration begins, we will process the stream through Whisper and generate structured action items.
Sarah: Great. Let's aim to have the API contracts finalized by Wednesday so we can start integration testing.`,
    notes: [
      {
        id: "note-1-1",
        title: "Q4 Roadmap Key Decisions & Action Items",
        preview: "Team aligned on audio recording pipeline and latency reduction for real-time transcription...",
        timestamp: "Oct 27, 2026 • 11:15 AM",
        content: `### Summary
The team met to align on Q4 engineering objectives, focusing on the audio recording pipeline and memory optimization.

### Key Decisions
- Finalize API contracts for audio uploads and transcription by Wednesday.
- Maintain strict frontend memory management by revoking Object URLs on discard.

### Action Items
- [ ] Sarah: Publish Q4 milestone schedule in the project board.
- [ ] David: Verify cross-browser MediaRecorder compatibility on mobile Safari and Chrome.
- [ ] Alex: Share draft OpenAPI spec for the transcription endpoint.`
      }
    ],
    summary: `### Summary
The team met to align on Q4 engineering objectives, focusing on the audio recording pipeline and memory optimization.`
  },
  {
    id: "meeting-2",
    title: "Weekly Team Sync",
    date: "2026-10-26",
    recordings: [
      {
        id: "rec-2-1",
        name: "Standup Audio",
        duration: "08:45",
        timestamp: "Oct 26, 2026 • 09:15 AM",
        audioUrl: null
      }
    ],
    audioDuration: "08:45",
    audioUrl: null,
    transcripts: [
      {
        id: "trans-2-1",
        name: "Transcript 1",
        text: `Marcus: Morning everyone. Quick standup today. Elena, any blockers on the design system?
Elena: None. All components have been aligned with the minimal pure white theme. Borders are set to #E5E7EB with crisp typography and subtle hover states.
Marcus: Sounds solid. Are the folder tree icons intuitive for the collapsible sidebar?
Elena: Yes, using Lucide icons: Folder, Volume2 for audio, FileText for transcripts, and Sparkles for AI summaries.
Marcus: Perfect. Keep everything restrained—no gradients or heavy drop shadows.`,
        wordCount: 77,
        charCount: 489,
        timestamp: "Oct 26, 2026 • 09:20 AM"
      }
    ],
    transcript: `Marcus: Morning everyone. Quick standup today. Elena, any blockers on the design system?
Elena: None. All components have been aligned with the minimal pure white theme. Borders are set to #E5E7EB with crisp typography and subtle hover states.
Marcus: Sounds solid. Are the folder tree icons intuitive for the collapsible sidebar?
Elena: Yes, using Lucide icons: Folder, Volume2 for audio, FileText for transcripts, and Sparkles for AI summaries.
Marcus: Perfect. Keep everything restrained—no gradients or heavy drop shadows.`,
    notes: [
      {
        id: "note-2-1",
        title: "Weekly Standup Notes & Iconography Review",
        preview: "Weekly standup confirming design system guidelines and Lucide React iconography for tree navigation...",
        timestamp: "Oct 26, 2026 • 09:30 AM",
        content: `### Summary
Weekly standup confirming design system guidelines and iconography for the meeting folder tree.

### Key Highlights
- UI theme adheres strictly to pure white background and subtle borders.
- Lucide React icons standardized across the sidebar tree.

### Action Items
- [ ] Elena: Deliver finalized token specs for interactive focus rings.`
      }
    ],
    summary: `### Summary
Weekly standup confirming design system guidelines and iconography for the meeting folder tree.`
  },
  {
    id: "meeting-3",
    title: "Client Feedback Review - Acme Corp",
    date: "2026-10-24",
    recordings: [
      {
        id: "rec-3-1",
        name: "Customer Interview Audio",
        duration: "22:15",
        timestamp: "Oct 24, 2026 • 02:00 PM",
        audioUrl: null
      }
    ],
    audioDuration: "22:15",
    audioUrl: null,
    transcripts: [
      {
        id: "trans-3-1",
        name: "Transcript 1",
        text: `Rachel: Acme Corp tested the meeting notes prototype last Friday. Overall sentiment was very positive, especially around simplicity.
Jason: Did they mention anything about the transcript editor?
Rachel: They loved having the text paste option right alongside the audio recorder rather than hidden behind tabs or wizard steps.
Jason: That validates our single-workspace design decision. What about export formats?
Rachel: They requested Markdown and PDF exports for next quarter once the backend is ready.`,
        wordCount: 78,
        charCount: 512,
        timestamp: "Oct 24, 2026 • 02:30 PM"
      }
    ],
    transcript: `Rachel: Acme Corp tested the meeting notes prototype last Friday. Overall sentiment was very positive, especially around simplicity.
Jason: Did they mention anything about the transcript editor?
Rachel: They loved having the text paste option right alongside the audio recorder rather than hidden behind tabs or wizard steps.
Jason: That validates our single-workspace design decision. What about export formats?
Rachel: They requested Markdown and PDF exports for next quarter once the backend is ready.`,
    notes: [
      {
        id: "note-3-1",
        title: "Acme Corp Feedback Summary",
        preview: "Review of customer feedback from Acme Corp's beta testing of the meeting capture workflow...",
        timestamp: "Oct 24, 2026 • 03:00 PM",
        content: `### Summary
Review of customer feedback from Acme Corp's beta testing of the meeting note capture workflow.

### Key Highlights
- Single-workspace layout (text + audio recording together) received high praise.
- Future requests logged for Markdown and PDF export capabilities.

### Action Items
- [ ] Rachel: Send thank-you note to Acme Corp's pilot group.`
      }
    ],
    summary: `### Summary
Review of customer feedback from Acme Corp's beta testing of the meeting note capture workflow.`
  },
  {
    id: "meeting-4",
    title: "Engineering Architecture Discussion",
    date: "2026-10-22",
    recordings: [
      {
        id: "rec-4-1",
        name: "Architecture Discussion Audio",
        duration: "18:02",
        timestamp: "Oct 22, 2026 • 04:30 PM",
        audioUrl: null
      }
    ],
    audioDuration: "18:02",
    audioUrl: null,
    transcripts: [
      {
        id: "trans-4-1",
        name: "Transcript 1",
        text: `Tom: Let's discuss how we will separate the client recording buffer from the streaming backend.
Maya: We should keep the frontend recording logic completely decoupled from meeting history state. React hooks should handle the MediaRecorder lifecycle.
Tom: Agreed. When the user stops recording, we create a local Blob and pass it to an AudioPreview component.
Maya: And if the user cancels or discards, the MediaStream tracks are terminated immediately.`,
        wordCount: 70,
        charCount: 462,
        timestamp: "Oct 22, 2026 • 04:45 PM"
      }
    ],
    transcript: `Tom: Let's discuss how we will separate the client recording buffer from the streaming backend.
Maya: We should keep the frontend recording logic completely decoupled from meeting history state. React hooks should handle the MediaRecorder lifecycle.
Tom: Agreed. When the user stops recording, we create a local Blob and pass it to an AudioPreview component.
Maya: And if the user cancels or discards, the MediaStream tracks are terminated immediately.`,
    notes: [
      {
        id: "note-4-1",
        title: "MediaRecorder Architecture Decisions",
        preview: "Architecture discussion focusing on decoupling MediaRecorder lifecycle from workspace state...",
        timestamp: "Oct 22, 2026 • 05:15 PM",
        content: `### Summary
Architecture discussion focusing on decoupling MediaRecorder lifecycle from workspace state.

### Key Decisions
- Isolate audio recording hooks and state from meeting history logic.
- Ensure all hardware MediaStream tracks stop promptly when recording stops or cancels.

### Action Items
- [ ] Tom: Document the audio lifecycle state machine diagram.`
      }
    ],
    summary: `### Summary
Architecture discussion focusing on decoupling MediaRecorder lifecycle from workspace state.`
  }
];

export default mockMeetings;
