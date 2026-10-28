/**
 * Mock meeting history data for MeetNote AI demonstration.
 * In a production environment, this data would be fetched from a backend API and database.
 */

const mockMeetings = [
  {
    id: "meeting-1",
    title: "Product Planning & Roadmap Q4",
    date: "2026-10-27",
    audioDuration: "14:20",
    audioUrl: null, // Audio stream placeholder
    transcript: `Sarah: Let's review the Q4 roadmap priorities. The main focus is completing the audio recording pipeline and latency reduction for real-time transcription.
David: On the frontend, we have implemented the pure white minimal interface. The MediaRecorder API is capturing local blobs without issues.
Sarah: Excellent. How are we handling long recordings? Is there memory pressure?
David: We release Object URLs when recordings are discarded or replaced to avoid memory leaks. We also enforce chunking before backend uploads.
Alex: From the backend side, once integration begins, we will process the stream through Whisper and generate structured action items.
Sarah: Great. Let's aim to have the API contracts finalized by Wednesday so we can start integration testing.`,
    summary: `### Summary
The team met to align on Q4 engineering objectives, focusing on the audio recording pipeline and memory optimization.

### Key Decisions
- Finalize API contracts for audio uploads and transcription by Wednesday.
- Maintain strict frontend memory management by revoking Object URLs on discard.

### Action Items
- [ ] Sarah: Publish Q4 milestone schedule in the project board.
- [ ] David: Verify cross-browser MediaRecorder compatibility on mobile Safari and Chrome.
- [ ] Alex: Share draft OpenAPI spec for the transcription endpoint.`
  },
  {
    id: "meeting-2",
    title: "Weekly Team Sync",
    date: "2026-10-26",
    audioDuration: "08:45",
    audioUrl: null,
    transcript: `Marcus: Morning everyone. Quick standup today. Elena, any blockers on the design system?
Elena: None. All components have been aligned with the minimal pure white theme. Borders are set to #E5E7EB with crisp typography and subtle hover states.
Marcus: Sounds solid. Are the folder tree icons intuitive for the collapsible sidebar?
Elena: Yes, using Lucide icons: Folder, Volume2 for audio, FileText for transcripts, and Sparkles for AI summaries.
Marcus: Perfect. Keep everything restrained—no gradients or heavy drop shadows.`,
    summary: `### Summary
Weekly standup confirming design system guidelines and iconography for the meeting folder tree.

### Key Highlights
- UI theme adheres strictly to pure white background and subtle borders.
- Lucide React icons standardized across the sidebar tree.

### Action Items
- [ ] Elena: Deliver finalized token specs for interactive focus rings.`
  },
  {
    id: "meeting-3",
    title: "Client Feedback Review - Acme Corp",
    date: "2026-10-24",
    audioDuration: "22:15",
    audioUrl: null,
    transcript: `Rachel: Acme Corp tested the meeting notes prototype last Friday. Overall sentiment was very positive, especially around simplicity.
Jason: Did they mention anything about the transcript editor?
Rachel: They loved having the text paste option right alongside the audio recorder rather than hidden behind tabs or wizard steps.
Jason: That validates our single-workspace design decision. What about export formats?
Rachel: They requested Markdown and PDF exports for next quarter once the backend is ready.`,
    summary: `### Summary
Review of customer feedback from Acme Corp's beta testing of the meeting note capture workflow.

### Key Highlights
- Single-workspace layout (text + audio recording together) received high praise.
- Future requests logged for Markdown and PDF export capabilities.

### Action Items
- [ ] Rachel: Send thank-you note to Acme Corp's pilot group.`
  },
  {
    id: "meeting-4",
    title: "Engineering Architecture Discussion",
    date: "2026-10-22",
    audioDuration: "18:02",
    audioUrl: null,
    transcript: `Tom: Let's discuss how we will separate the client recording buffer from the streaming backend.
Maya: We should keep the frontend recording logic completely decoupled from meeting history state. React hooks should handle the MediaRecorder lifecycle.
Tom: Agreed. When the user stops recording, we create a local Blob and pass it to an AudioPreview component.
Maya: And if the user cancels or discards, the MediaStream tracks are terminated immediately.`,
    summary: `### Summary
Architecture discussion focusing on decoupling MediaRecorder lifecycle from workspace state.

### Key Decisions
- Isolate audio recording hooks and state from meeting history logic.
- Ensure all hardware MediaStream tracks stop promptly when recording stops or cancels.

### Action Items
- [ ] Tom: Document the audio lifecycle state machine diagram.`
  }
];

export default mockMeetings;
