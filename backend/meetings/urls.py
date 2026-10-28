from django.urls import path
from .views import (
    MeetingListCreateView,
    MeetingDetailView,
    MeetingFileUploadUrlView,
    MeetingFileConfirmView,
    MeetingFileListView,
    MeetingFileDownloadUrlView,
    MeetingFileDetailView,
    MeetingTranscribeView,
    MeetingBatchGenerateTranscriptsView,
    MeetingTranscriptsListView,
    MeetingTranscriptDetailContentView,
    MeetingSummaryView,
)

app_name = 'meetings'

urlpatterns = [
    path('', MeetingListCreateView.as_view(), name='meeting-list-create'),
    path('<int:pk>/', MeetingDetailView.as_view(), name='meeting-detail'),
    path('<int:pk>/files/upload-url/', MeetingFileUploadUrlView.as_view(), name='meeting-file-upload-url'),
    path('<int:pk>/files/confirm/', MeetingFileConfirmView.as_view(), name='meeting-file-confirm'),
    path('<int:pk>/files/<int:file_id>/download-url/', MeetingFileDownloadUrlView.as_view(), name='meeting-file-download-url'),
    path('<int:pk>/files/<int:file_id>/', MeetingFileDetailView.as_view(), name='meeting-file-detail'),
    path('<int:pk>/files/', MeetingFileListView.as_view(), name='meeting-file-list'),
    path('<int:pk>/transcribe/', MeetingTranscribeView.as_view(), name='meeting-transcribe'),
    path('<int:pk>/generate-transcripts/', MeetingBatchGenerateTranscriptsView.as_view(), name='meeting-generate-transcripts'),
    path('<int:pk>/transcripts/', MeetingTranscriptsListView.as_view(), name='meeting-transcripts-list'),
    path('<int:pk>/transcripts/<int:transcript_id>/', MeetingTranscriptDetailContentView.as_view(), name='meeting-transcript-detail-content'),
    path('<int:pk>/generate-summary/', MeetingSummaryView.as_view(), name='meeting-generate-summary'),
    path('<int:pk>/summary/', MeetingSummaryView.as_view(), name='meeting-summary'),
    path('<int:pk>/generate-notes/', MeetingSummaryView.as_view(), name='meeting-generate-notes'),
]

