from django.urls import path
from .views import (
    MeetingListCreateView,
    MeetingDetailView,
    MeetingFileUploadUrlView,
    MeetingFileConfirmView,
    MeetingFileListView,
    MeetingTranscribeView,
)

app_name = 'meetings'

urlpatterns = [
    path('', MeetingListCreateView.as_view(), name='meeting-list-create'),
    path('<int:pk>/', MeetingDetailView.as_view(), name='meeting-detail'),
    path('<int:pk>/files/upload-url/', MeetingFileUploadUrlView.as_view(), name='meeting-file-upload-url'),
    path('<int:pk>/files/confirm/', MeetingFileConfirmView.as_view(), name='meeting-file-confirm'),
    path('<int:pk>/files/', MeetingFileListView.as_view(), name='meeting-file-list'),
    path('<int:pk>/transcribe/', MeetingTranscribeView.as_view(), name='meeting-transcribe'),
]
