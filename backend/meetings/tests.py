import re
from unittest.mock import patch, MagicMock
import requests
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from meetings.models import Meeting, MeetingFile
from meetings.s3_utils import (
    validate_file_type,
    generate_s3_key,
    generate_presigned_upload_url,
    generate_presigned_download_url,
    SUPPORTED_FILE_TYPES,
)
from meetings.transcription_service import (
    transcribe_audio_bytes,
    transcribe_audio_from_s3,
    get_deepgram_api_key,
    resolve_audio_content_type,
    TranscriptionError,
    TranscriptionConfigurationError,
    TranscriptionAuthenticationError,
    TranscriptionRateLimitError,
    TranscriptionTimeoutError,
    TranscriptionBadRequestError,
    TranscriptionServiceError,
)


@override_settings(
    AWS_ACCESS_KEY_ID='TEST_KEY_ID',
    AWS_SECRET_ACCESS_KEY='TEST_SECRET_KEY',
    AWS_STORAGE_BUCKET_NAME='aimeeting-assistant',
    AWS_S3_REGION_NAME='us-east-1',
    AWS_S3_PRESIGNED_EXPIRATION=300
)
class S3UtilsTestCase(TestCase):
    """Unit tests for S3 utility functions."""

    def test_supported_audio_types(self):
        """Verify all required audio content types validate successfully."""
        for mime in ['audio/webm', 'audio/wav', 'audio/mpeg']:
            folder, ext = validate_file_type('audio', mime)
            self.assertEqual(folder, 'audio')
            self.assertTrue(ext in ['.webm', '.wav', '.mp3'])

    def test_supported_transcript_types(self):
        """Verify text transcripts validate successfully."""
        folder, ext = validate_file_type('transcript', 'text/plain')
        self.assertEqual(folder, 'transcripts')
        self.assertEqual(ext, '.txt')

    def test_supported_summary_types(self):
        """Verify text summaries validate successfully."""
        folder, ext = validate_file_type('summary', 'text/plain')
        self.assertEqual(folder, 'summaries')
        self.assertEqual(ext, '.txt')

    def test_unsupported_file_category_raises_error(self):
        """Verify invalid file categories raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            validate_file_type('video', 'video/mp4')
        self.assertIn("Unsupported file_type", str(ctx.exception))

    def test_unsupported_content_type_raises_error(self):
        """Verify unsupported MIME types raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            validate_file_type('audio', 'application/pdf')
        self.assertIn("Unsupported content_type", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            validate_file_type('transcript', 'application/json')
        self.assertIn("Unsupported content_type", str(ctx.exception))

    def test_s3_key_structure(self):
        """Verify S3 object keys are organized as meetings/<meeting_id>/<folder>/<uuid>.<ext>."""
        key_audio = generate_s3_key(meeting_id=42, file_type='audio', content_type='audio/webm')
        self.assertTrue(key_audio.startswith('meetings/42/audio/'))
        self.assertTrue(key_audio.endswith('.webm'))

        key_trans = generate_s3_key(meeting_id='meet-abc', file_type='transcript', content_type='text/plain')
        self.assertTrue(key_trans.startswith('meetings/meet-abc/transcripts/'))
        self.assertTrue(key_trans.endswith('.txt'))

        key_sum = generate_s3_key(meeting_id=1, file_type='summary', content_type='text/plain')
        self.assertTrue(key_sum.startswith('meetings/1/summaries/'))
        self.assertTrue(key_sum.endswith('.txt'))

    def test_s3_key_uniqueness(self):
        """Verify consecutive keys for the same meeting are distinct."""
        key1 = generate_s3_key(10, 'audio', 'audio/webm')
        key2 = generate_s3_key(10, 'audio', 'audio/webm')
        self.assertNotEqual(key1, key2)

    def test_generate_presigned_upload_url_audio(self):
        """Verify presigned upload URL generation for audio files."""
        result = generate_presigned_upload_url(
            meeting_id=99,
            file_type='audio',
            content_type='audio/webm',
            original_filename='recording.webm',
            expiration=300
        )

        self.assertIn('upload_url', result)
        self.assertIn('s3_key', result)
        self.assertEqual(result['bucket'], 'aimeeting-assistant')
        self.assertEqual(result['file_type'], 'audio')
        self.assertEqual(result['content_type'], 'audio/webm')
        self.assertEqual(result['expires_in'], 300)

        # Check URL structure
        url = result['upload_url']
        self.assertIn('aimeeting-assistant', url)
        self.assertIn('meetings/99/audio/', url)
        self.assertIn('X-Amz-Signature=', url)

    def test_generate_presigned_upload_url_transcript(self):
        """Verify presigned upload URL generation for transcripts."""
        result = generate_presigned_upload_url(
            meeting_id=101,
            file_type='transcript',
            content_type='text/plain',
            original_filename='notes.txt'
        )

        self.assertIn('meetings/101/transcripts/', result['s3_key'])
        self.assertTrue(result['s3_key'].endswith('.txt'))
        self.assertEqual(result['content_type'], 'text/plain')

    def test_generate_presigned_download_url(self):
        """Verify presigned GET download URL generation."""
        s3_key = 'meetings/12/audio/sample.webm'
        url = generate_presigned_download_url(s3_key=s3_key, expiration=600)

        self.assertIn('aimeeting-assistant', url)
        self.assertIn(s3_key, url)
        self.assertIn('X-Amz-Signature=', url)


@override_settings(
    AWS_ACCESS_KEY_ID='TEST_KEY_ID',
    AWS_SECRET_ACCESS_KEY='TEST_SECRET_KEY',
    AWS_STORAGE_BUCKET_NAME='aimeeting-assistant',
    AWS_S3_REGION_NAME='us-east-1',
    AWS_S3_PRESIGNED_EXPIRATION=300
)
class MeetingAPITestCase(APITestCase):
    """Test suite for the 6 Meeting API endpoints."""

    def setUp(self):
        self.meeting1 = Meeting.objects.create(title="Q4 Architecture Review")
        self.meeting2 = Meeting.objects.create(title="Sprint Retrospective")

    # -------------------------------------------------------------
    # 1. Meeting Creation & Listing
    # -------------------------------------------------------------
    def test_create_meeting_success(self):
        """POST /api/meetings/ should create and return a meeting with 201 Created."""
        payload = {'title': 'Weekly Executive Sync'}
        response = self.client.post('/api/meetings/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['title'], 'Weekly Executive Sync')
        self.assertEqual(response.data['files'], [])
        self.assertEqual(response.data['files_count'], 0)
        self.assertTrue(Meeting.objects.filter(id=response.data['id']).exists())

    def test_create_meeting_blank_title_rejected(self):
        """POST /api/meetings/ with empty title should return 400 Bad Request."""
        response = self.client.post('/api/meetings/', {'title': '   '}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_empty = self.client.post('/api/meetings/', {}, format='json')
        self.assertEqual(response_empty.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_meetings_newest_first(self):
        """GET /api/meetings/ should return all meetings ordered newest first."""
        response = self.client.get('/api/meetings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
        # Verify ordering: meeting2 was created after meeting1
        self.assertEqual(response.data[0]['id'], self.meeting2.id)
        self.assertEqual(response.data[1]['id'], self.meeting1.id)

    # -------------------------------------------------------------
    # 2. Meeting Retrieval
    # -------------------------------------------------------------
    def test_retrieve_existing_meeting(self):
        """GET /api/meetings/<id>/ should return meeting details and files."""
        # Attach a file
        MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/test.webm",
            original_filename="rec.webm"
        )

        response = self.client.get(f'/api/meetings/{self.meeting1.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.meeting1.id)
        self.assertEqual(response.data['title'], self.meeting1.title)
        self.assertEqual(len(response.data['files']), 1)
        self.assertEqual(response.data['files'][0]['file_type'], 'audio')

    def test_retrieve_nonexistent_meeting(self):
        """GET /api/meetings/<id>/ with unknown ID should return 404 Not Found."""
        response = self.client.get('/api/meetings/999999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    # -------------------------------------------------------------
    # 3. Presigned Upload URL Generation
    # -------------------------------------------------------------
    def test_generate_upload_url_valid(self):
        """POST /api/meetings/<id>/files/upload-url/ should generate presigned PUT URL."""
        payload = {
            'file_type': 'audio',
            'content_type': 'audio/webm',
            'filename': 'my_recording.webm'
        }
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/files/upload-url/',
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('upload_url', response.data)
        self.assertIn('s3_key', response.data)
        self.assertEqual(response.data['http_method'], 'PUT')
        self.assertEqual(response.data['required_headers'], {'Content-Type': 'audio/webm'})
        self.assertTrue(response.data['s3_key'].startswith(f"meetings/{self.meeting1.id}/audio/"))
        self.assertTrue(response.data['s3_key'].endswith('.webm'))

    def test_generate_upload_url_invalid_file_type(self):
        """POST /api/meetings/<id>/files/upload-url/ with invalid file_type should return 400."""
        payload = {
            'file_type': 'video',
            'content_type': 'video/mp4'
        }
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/files/upload-url/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_upload_url_invalid_content_type(self):
        """POST /api/meetings/<id>/files/upload-url/ with mismatched MIME should return 400."""
        payload = {
            'file_type': 'audio',
            'content_type': 'application/pdf'
        }
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/files/upload-url/',
            payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_upload_url_nonexistent_meeting(self):
        """POST /api/meetings/<id>/files/upload-url/ with unknown meeting should return 404."""
        payload = {
            'file_type': 'transcript',
            'content_type': 'text/plain'
        }
        response = self.client.post('/api/meetings/999999/files/upload-url/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------
    # 4. File Confirmation
    # -------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    def test_confirm_file_success(self, mock_check_s3):
        """POST /api/meetings/<id>/files/confirm/ creates record when S3 object exists."""
        mock_check_s3.return_value = True
        s3_key = f"meetings/{self.meeting1.id}/audio/test-uuid-123.webm"

        payload = {
            's3_key': s3_key,
            'file_type': 'audio',
            'original_filename': 'session_audio.webm'
        }
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/files/confirm/',
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['s3_key'], s3_key)
        self.assertEqual(response.data['file_type'], 'audio')
        self.assertEqual(response.data['original_filename'], 'session_audio.webm')
        self.assertTrue(MeetingFile.objects.filter(s3_key=s3_key).exists())

    @patch('meetings.views.check_s3_object_exists')
    def test_confirm_file_fails_when_s3_object_missing(self, mock_check_s3):
        """POST /api/meetings/<id>/files/confirm/ should return 400 if file does not exist in S3."""
        mock_check_s3.return_value = False
        s3_key = f"meetings/{self.meeting1.id}/audio/missing-uuid.webm"

        payload = {'s3_key': s3_key}
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/files/confirm/',
            payload,
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertFalse(MeetingFile.objects.filter(s3_key=s3_key).exists())

    def test_confirm_file_fails_when_key_belongs_to_another_meeting(self):
        """POST /api/meetings/<id>/files/confirm/ should reject keys belonging to a different meeting."""
        other_meeting_key = f"meetings/{self.meeting2.id}/audio/other.webm"

        # Attempt to confirm meeting2's key against meeting1
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/files/confirm/',
            {'s3_key': other_meeting_key},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('does not belong to meeting', response.data['error'])

    @patch('meetings.views.check_s3_object_exists')
    def test_confirm_file_prevents_duplicate_records(self, mock_check_s3):
        """POST /api/meetings/<id>/files/confirm/ should reject duplicate confirmations for the same S3 key."""
        mock_check_s3.return_value = True
        s3_key = f"meetings/{self.meeting1.id}/transcripts/doc-1.txt"

        payload = {'s3_key': s3_key, 'file_type': 'transcript', 'original_filename': 'notes.txt'}

        # First confirmation -> 201 Created
        first_resp = self.client.post(f'/api/meetings/{self.meeting1.id}/files/confirm/', payload, format='json')
        self.assertEqual(first_resp.status_code, status.HTTP_201_CREATED)

        # Duplicate confirmation -> 400 Bad Request
        dup_resp = self.client.post(f'/api/meetings/{self.meeting1.id}/files/confirm/', payload, format='json')
        self.assertEqual(dup_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already been confirmed', dup_resp.data['error'])

        # Verify only 1 record exists
        self.assertEqual(MeetingFile.objects.filter(s3_key=s3_key).count(), 1)

    # -------------------------------------------------------------
    # 5. File Listing
    # -------------------------------------------------------------
    def test_list_files_for_meeting(self):
        """GET /api/meetings/<id>/files/ should list files belonging to that meeting."""
        file1 = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/1.webm",
            original_filename="rec1.webm"
        )
        file2 = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='transcript',
            s3_key=f"meetings/{self.meeting1.id}/transcripts/1.txt",
            original_filename="transcript.txt"
        )
        # Create a file for meeting2 to ensure isolation
        MeetingFile.objects.create(
            meeting=self.meeting2,
            file_type='audio',
            s3_key=f"meetings/{self.meeting2.id}/audio/2.webm",
            original_filename="rec2.webm"
        )

        response = self.client.get(f'/api/meetings/{self.meeting1.id}/files/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        file_ids = [f['id'] for f in response.data]
        self.assertIn(file1.id, file_ids)
        self.assertIn(file2.id, file_ids)

    def test_list_files_nonexistent_meeting(self):
        """GET /api/meetings/<id>/files/ for nonexistent meeting should return 404."""
        response = self.client.get('/api/meetings/999999/files/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_meeting_title(self):
        """PATCH /api/meetings/<id>/ should update meeting title."""
        response = self.client.patch(
            f'/api/meetings/{self.meeting1.id}/',
            {'title': 'Renamed Architecture Review'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Renamed Architecture Review')
        self.meeting1.refresh_from_db()
        self.assertEqual(self.meeting1.title, 'Renamed Architecture Review')

    @patch('meetings.views.delete_s3_object')
    def test_delete_meeting(self, mock_delete_s3):
        """DELETE /api/meetings/<id>/ should delete meeting and its files."""
        MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/to_del.webm",
            original_filename="to_del.webm"
        )
        response = self.client.delete(f'/api/meetings/{self.meeting1.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Meeting.objects.filter(id=self.meeting1.id).exists())
        self.assertFalse(MeetingFile.objects.filter(meeting_id=self.meeting1.id).exists())
        mock_delete_s3.assert_called_once()

    @patch('meetings.views.check_s3_object_exists')
    def test_get_file_download_url_success(self, mock_check_s3):
        """GET /api/meetings/<id>/files/<file_id>/download-url/ returns presigned download URL."""
        mock_check_s3.return_value = True
        file_obj = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/play.webm",
            original_filename="play.webm"
        )
        response = self.client.get(f'/api/meetings/{self.meeting1.id}/files/{file_obj.id}/download-url/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('download_url', response.data)
        self.assertIn('s3_key', response.data)
        self.assertEqual(response.data['file_type'], 'audio')
        self.assertEqual(response.data['original_filename'], 'play.webm')
        self.assertIn('aimeeting-assistant', response.data['download_url'])

    @patch('meetings.views.check_s3_object_exists')
    def test_get_file_download_url_missing_s3_object(self, mock_check_s3):
        """GET /api/meetings/<id>/files/<file_id>/download-url/ returns 404 if S3 object is missing."""
        mock_check_s3.return_value = False
        file_obj = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/missing.webm",
            original_filename="missing.webm"
        )
        response = self.client.get(f'/api/meetings/{self.meeting1.id}/files/{file_obj.id}/download-url/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('does not exist in S3', response.data['error'])

    def test_get_file_download_url_foreign_meeting_file(self):
        """GET /api/meetings/<id>/files/<file_id>/download-url/ returns 400 if file belongs to another meeting."""
        file_m2 = MeetingFile.objects.create(
            meeting=self.meeting2,
            file_type='audio',
            s3_key=f"meetings/{self.meeting2.id}/audio/other.webm",
            original_filename="other.webm"
        )
        response = self.client.get(f'/api/meetings/{self.meeting1.id}/files/{file_m2.id}/download-url/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('does not belong to meeting', response.data['error'])

    @patch('meetings.views.delete_s3_object')
    def test_delete_file_success(self, mock_delete_s3):
        """DELETE /api/meetings/<id>/files/<file_id>/ deletes file from DB and S3."""
        file_obj = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/del_file.webm",
            original_filename="del_file.webm"
        )
        response = self.client.delete(f'/api/meetings/{self.meeting1.id}/files/{file_obj.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MeetingFile.objects.filter(id=file_obj.id).exists())
        mock_delete_s3.assert_called_once_with(file_obj.s3_key)


# ==============================================================================
# Step 3: Audio Transcription Tests
# ==============================================================================

@override_settings(DEEPGRAM_API_KEY='dummy-deepgram-key')
class TranscriptionServiceTestCase(TestCase):
    """Unit tests for the Deepgram Nova-3 transcription service."""

    def test_get_deepgram_api_key_success(self):
        """Verify API key is retrieved from settings."""
        self.assertEqual(get_deepgram_api_key(), 'dummy-deepgram-key')

    @override_settings(DEEPGRAM_API_KEY='')
    def test_get_deepgram_api_key_missing_raises_error(self):
        """Verify missing API key raises TranscriptionConfigurationError."""
        with patch.dict('os.environ', {'DEEPGRAM_API_KEY': ''}):
            with self.assertRaises(TranscriptionConfigurationError):
                get_deepgram_api_key()

    def test_resolve_audio_content_type(self):
        """Verify MIME inference from S3 file extensions."""
        self.assertEqual(resolve_audio_content_type('meetings/1/audio/rec.webm'), 'audio/webm')
        self.assertEqual(resolve_audio_content_type('meetings/1/audio/rec.wav'), 'audio/wav')
        self.assertEqual(resolve_audio_content_type('meetings/1/audio/rec.mp3'), 'audio/mpeg')
        self.assertEqual(resolve_audio_content_type('meetings/1/audio/rec.m4a'), 'audio/mp4')

    def test_transcribe_audio_bytes_empty_rejected(self):
        """Verify empty audio bytes raise TranscriptionBadRequestError."""
        with self.assertRaises(TranscriptionBadRequestError):
            transcribe_audio_bytes(b'')

    @patch('meetings.transcription_service.requests.post')
    def test_transcribe_audio_bytes_success(self, mock_post):
        """Verify successful transcription returns formatted text and metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': {
                'channels': [{
                    'alternatives': [{
                        'transcript': 'Namaste, this is an important meeting.',
                        'confidence': 0.97,
                        'words': [{'word': 'Namaste'}, {'word': 'this'}, {'word': 'is'}],
                        'paragraphs': {
                            'transcript': 'Namaste, this is an important meeting.'
                        }
                    }]
                }]
            }
        }
        mock_post.return_value = mock_response

        audio_data = b'fake-binary-audio-stream'
        result = transcribe_audio_bytes(audio_data, content_type='audio/webm', language='multi')

        self.assertEqual(result['transcript'], 'Namaste, this is an important meeting.')
        self.assertEqual(result['confidence'], 0.97)
        self.assertEqual(result['words_count'], 3)
        self.assertEqual(result['model'], 'nova-3')
        self.assertEqual(result['language'], 'multi')

        # Verify Deepgram request params
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['params']['model'], 'nova-3')
        self.assertEqual(kwargs['params']['language'], 'multi')
        self.assertEqual(kwargs['params']['smart_format'], 'true')
        self.assertEqual(kwargs['params']['punctuate'], 'true')

    @patch('meetings.transcription_service.requests.post')
    def test_transcribe_language_settings_gujarati_hindi_english(self, mock_post):
        """Verify language configurations for Gujarati, Hindi, and English."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': {
                'channels': [{
                    'alternatives': [{'transcript': 'Sample speech text'}]
                }]
            }
        }
        mock_post.return_value = mock_response

        # Gujarati
        transcribe_audio_bytes(b'audio-bytes', language='gu')
        self.assertEqual(mock_post.call_args[1]['params']['language'], 'gu')

        # Hindi
        transcribe_audio_bytes(b'audio-bytes', language='hi')
        self.assertEqual(mock_post.call_args[1]['params']['language'], 'hi')

        # English
        transcribe_audio_bytes(b'audio-bytes', language='en')
        self.assertEqual(mock_post.call_args[1]['params']['language'], 'en')

        # Multilingual code-switching
        transcribe_audio_bytes(b'audio-bytes', language='multi')
        self.assertEqual(mock_post.call_args[1]['params']['language'], 'multi')

    @patch('meetings.transcription_service.requests.post')
    def test_transcribe_empty_transcription_result(self, mock_post):
        """Verify handling when Deepgram detects no speech (empty transcript)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': {
                'channels': [{
                    'alternatives': [{
                        'transcript': '',
                        'confidence': 0.0,
                        'words': []
                    }]
                }]
            }
        }
        mock_post.return_value = mock_response

        result = transcribe_audio_bytes(b'audio-silence')
        self.assertEqual(result['transcript'], '')
        self.assertEqual(result['words_count'], 0)

    @patch('meetings.transcription_service.requests.post')
    def test_transcribe_deepgram_error_mappings(self, mock_post):
        """Verify Deepgram HTTP errors map to proper custom exceptions."""
        # 401 Unauthorized
        mock_resp_401 = MagicMock(status_code=401, text='Invalid API Key')
        mock_post.return_value = mock_resp_401
        with self.assertRaises(TranscriptionAuthenticationError):
            transcribe_audio_bytes(b'audio-data')

        # 429 Rate Limit
        mock_resp_429 = MagicMock(status_code=429, text='Rate limited')
        mock_post.return_value = mock_resp_429
        with self.assertRaises(TranscriptionRateLimitError):
            transcribe_audio_bytes(b'audio-data')

        # 400 Bad Request
        mock_resp_400 = MagicMock(status_code=400, text='Invalid payload')
        mock_resp_400.json.return_value = {'err_msg': 'Invalid payload'}
        mock_post.return_value = mock_resp_400
        with self.assertRaises(TranscriptionBadRequestError):
            transcribe_audio_bytes(b'audio-data')

        # 500 Service Error
        mock_resp_500 = MagicMock(status_code=500, text='Server Error')
        mock_post.return_value = mock_resp_500
        with self.assertRaises(TranscriptionServiceError):
            transcribe_audio_bytes(b'audio-data')

        # Timeout
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
        with self.assertRaises(TranscriptionTimeoutError):
            transcribe_audio_bytes(b'audio-data')


@override_settings(
    AWS_ACCESS_KEY_ID='TEST_KEY_ID',
    AWS_SECRET_ACCESS_KEY='TEST_SECRET_KEY',
    AWS_STORAGE_BUCKET_NAME='aimeeting-assistant',
    AWS_S3_REGION_NAME='us-east-1',
    AWS_S3_PRESIGNED_EXPIRATION=300,
    DEEPGRAM_API_KEY='test-deepgram-api-key'
)
class MeetingTranscribeAPITestCase(APITestCase):
    """Test suite for POST /api/meetings/<id>/transcribe/ endpoint."""

    def setUp(self):
        self.meeting1 = Meeting.objects.create(title="Sprint Planning & Review")
        self.meeting2 = Meeting.objects.create(title="Design Sync")

        # Audio file attached to meeting1
        self.audio_file1 = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/rec_01.webm",
            original_filename="rec_01.webm"
        )

    # --------------------------------------------------------------------------
    # 1. Successful Transcription & Transcript Storage
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_transcribe_success_auto_single_audio(
        self,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """POST /api/meetings/<id>/transcribe/ with single audio auto-selects and stores transcript."""
        mock_check_s3.return_value = True
        mock_transcribe.return_value = {
            'transcript': 'Welcome team. We are discussing Q3 roadmap items.',
            'confidence': 0.98,
            'words_count': 8,
            'language': 'multi',
            'model': 'nova-3',
        }

        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['transcript'], 'Welcome team. We are discussing Q3 roadmap items.')
        self.assertIn('transcript_file_id', response.data)
        self.assertTrue(response.data['s3_key'].startswith(f"meetings/{self.meeting1.id}/transcripts/"))
        self.assertEqual(response.data['original_filename'], 'rec_01_transcript.txt')

        # Verify DB record created
        transcript_file = MeetingFile.objects.get(id=response.data['transcript_file_id'])
        self.assertEqual(transcript_file.file_type, 'transcript')
        self.assertEqual(transcript_file.meeting_id, self.meeting1.id)
        self.assertEqual(transcript_file.s3_key, response.data['s3_key'])

        # Verify S3 upload called
        mock_upload_s3.assert_called_once()
        upload_call = mock_upload_s3.call_args
        self.assertEqual(upload_call[1]['s3_key'], response.data['s3_key'])
        self.assertEqual(upload_call[1]['data'], b'Welcome team. We are discussing Q3 roadmap items.')
        self.assertEqual(upload_call[1]['content_type'], 'text/plain; charset=utf-8')

    # --------------------------------------------------------------------------
    # 2. Language Settings (Gujarati, Hindi, English, Multilingual)
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_transcribe_language_settings(
        self,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """POST /api/meetings/<id>/transcribe/ correctly forwards language codes to service."""
        mock_check_s3.return_value = True

        for lang in ['gu', 'hi', 'en', 'multi']:
            mock_transcribe.return_value = {
                'transcript': f'Transcription in {lang}',
                'confidence': 0.99,
                'words_count': 3,
                'language': lang,
                'model': 'nova-3',
            }

            response = self.client.post(
                f'/api/meetings/{self.meeting1.id}/transcribe/',
                {'language': lang, 'retranscribe': True},
                format='json'
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(mock_transcribe.call_args[1]['language'], lang)

    # --------------------------------------------------------------------------
    # 3. Multiple Audio Files Handling
    # --------------------------------------------------------------------------
    def test_transcribe_multiple_audio_files_without_id_returns_400(self):
        """POST /api/meetings/<id>/transcribe/ returns 400 when multiple audios exist without audio_file_id."""
        # Add second audio file to meeting1
        MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/rec_02.webm",
            original_filename="rec_02.webm"
        )

        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Multiple audio files exist', response.data['error'])

    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_transcribe_multiple_audio_files_with_explicit_id_succeeds(
        self,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """POST /api/meetings/<id>/transcribe/ succeeds when specific audio_file_id is provided."""
        audio_file2 = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='audio',
            s3_key=f"meetings/{self.meeting1.id}/audio/rec_02.webm",
            original_filename="rec_02.webm"
        )

        mock_check_s3.return_value = True
        mock_transcribe.return_value = {
            'transcript': 'Selected audio 2 transcribed.',
            'confidence': 0.95,
            'words_count': 4,
            'language': 'multi',
            'model': 'nova-3',
        }

        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {'audio_file_id': audio_file2.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_transcribe.call_args[1]['s3_key'], audio_file2.s3_key)

    # --------------------------------------------------------------------------
    # 4. Audio Verification & File Ownership
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    def test_transcribe_missing_audio_object_in_s3_returns_400(self, mock_check_s3):
        """POST /api/meetings/<id>/transcribe/ returns 400 when S3 audio object is missing."""
        mock_check_s3.return_value = False

        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('does not exist in S3', response.data['error'])

    def test_transcribe_invalid_audio_file_id_returns_404(self):
        """POST /api/meetings/<id>/transcribe/ with nonexistent audio_file_id returns 404."""
        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {'audio_file_id': 999999},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transcribe_audio_file_belongs_to_different_meeting_returns_400(self):
        """POST /api/meetings/<id>/transcribe/ rejects audio file belonging to another meeting."""
        file_m2 = MeetingFile.objects.create(
            meeting=self.meeting2,
            file_type='audio',
            s3_key=f"meetings/{self.meeting2.id}/audio/m2.webm",
            original_filename="m2.webm"
        )

        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {'audio_file_id': file_m2.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('does not belong to meeting', response.data['error'])

    def test_transcribe_file_not_audio_type_returns_400(self):
        """POST /api/meetings/<id>/transcribe/ rejects file when file_type is not 'audio'."""
        txt_file = MeetingFile.objects.create(
            meeting=self.meeting1,
            file_type='transcript',
            s3_key=f"meetings/{self.meeting1.id}/transcripts/doc.txt",
            original_filename="doc.txt"
        )

        response = self.client.post(
            f'/api/meetings/{self.meeting1.id}/transcribe/',
            {'audio_file_id': txt_file.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expected 'audio'", response.data['error'])

    def test_transcribe_meeting_without_any_audio_returns_404(self):
        """POST /api/meetings/<id>/transcribe/ returns 404 when meeting has 0 audio files."""
        empty_meeting = Meeting.objects.create(title="Empty Meeting")
        response = self.client.post(
            f'/api/meetings/{empty_meeting.id}/transcribe/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transcribe_nonexistent_meeting_returns_404(self):
        """POST /api/meetings/<id>/transcribe/ returns 404 when meeting ID does not exist."""
        response = self.client.post('/api/meetings/999999/transcribe/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --------------------------------------------------------------------------
    # 5. Deepgram API Failures, Timeouts, Missing Key
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    def test_transcribe_missing_deepgram_api_key_returns_500(self, mock_transcribe, mock_check_s3):
        """POST /api/meetings/<id>/transcribe/ returns 500 when Deepgram API key is missing."""
        mock_check_s3.return_value = True
        mock_transcribe.side_effect = TranscriptionConfigurationError("No API key")

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('API key is not configured', response.data['error'])

    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    def test_transcribe_deepgram_auth_failure_returns_502(self, mock_transcribe, mock_check_s3):
        """POST /api/meetings/<id>/transcribe/ returns 502 when Deepgram rejects authentication."""
        mock_check_s3.return_value = True
        mock_transcribe.side_effect = TranscriptionAuthenticationError("Bad credentials")

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('authentication failed', response.data['error'])

    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    def test_transcribe_deepgram_rate_limit_returns_429(self, mock_transcribe, mock_check_s3):
        """POST /api/meetings/<id>/transcribe/ returns 429 when Deepgram rate limit is reached."""
        mock_check_s3.return_value = True
        mock_transcribe.side_effect = TranscriptionRateLimitError("Rate limit exceeded")

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    def test_transcribe_deepgram_timeout_returns_504(self, mock_transcribe, mock_check_s3):
        """POST /api/meetings/<id>/transcribe/ returns 504 on Deepgram timeout."""
        mock_check_s3.return_value = True
        mock_transcribe.side_effect = TranscriptionTimeoutError("Timed out")

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_504_GATEWAY_TIMEOUT)

    # --------------------------------------------------------------------------
    # 6. Empty Transcription Result Handling
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_transcribe_empty_transcription_result(
        self,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """POST /api/meetings/<id>/transcribe/ handles empty speech without crashing."""
        mock_check_s3.return_value = True
        mock_transcribe.return_value = {
            'transcript': '',
            'confidence': 0.0,
            'words_count': 0,
            'language': 'multi',
            'model': 'nova-3',
        }

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['transcript'], '')
        self.assertTrue(MeetingFile.objects.filter(meeting=self.meeting1, file_type='transcript').exists())

    # --------------------------------------------------------------------------
    # 7. S3 Upload & DB Persistence Failure Handling & Cleanup
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_transcribe_s3_upload_failure_returns_500(
        self,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """POST /api/meetings/<id>/transcribe/ returns 500 if S3 transcript upload fails."""
        mock_check_s3.return_value = True
        mock_transcribe.return_value = {
            'transcript': 'Transcript text',
            'confidence': 0.99,
            'words_count': 2,
            'language': 'multi',
        }
        mock_upload_s3.side_effect = Exception("AWS S3 write timeout")

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('Failed to upload transcript to S3', response.data['error'])
        # Verify no misleading DB record created
        self.assertFalse(MeetingFile.objects.filter(meeting=self.meeting1, file_type='transcript').exists())

    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    @patch('meetings.views.delete_s3_object')
    @patch('meetings.models.MeetingFile.objects.create')
    def test_transcribe_db_save_failure_cleans_up_s3(
        self,
        mock_mf_create,
        mock_delete_s3,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """POST /api/meetings/<id>/transcribe/ cleans up S3 transcript if DB save fails."""
        mock_check_s3.return_value = True
        mock_transcribe.return_value = {
            'transcript': 'Transcript text',
            'confidence': 0.99,
            'words_count': 2,
            'language': 'multi',
        }
        mock_mf_create.side_effect = Exception("Database constraint error")

        response = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Verify S3 cleanup was called
        mock_delete_s3.assert_called_once()

    # --------------------------------------------------------------------------
    # 8. Duplicate Requests and Database Consistency
    # --------------------------------------------------------------------------
    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    @patch('meetings.views.get_s3_object_bytes')
    def test_transcribe_duplicate_requests_and_consistency(
        self,
        mock_get_s3_bytes,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """Verify repeated/retry requests return completed transcript without creating duplicate records."""
        mock_check_s3.return_value = True
        mock_transcribe.return_value = {
            'transcript': 'Initial transcript content.',
            'confidence': 0.96,
            'words_count': 3,
            'language': 'multi',
        }
        mock_get_s3_bytes.return_value = b'Initial transcript content.'

        # 1st request -> executes transcription & creates record
        resp1 = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp1.data['transcript'], 'Initial transcript content.')
        self.assertEqual(MeetingFile.objects.filter(meeting=self.meeting1, file_type='transcript').count(), 1)

        # 2nd duplicate request -> returns cached transcript, avoids duplicate record
        resp2 = self.client.post(f'/api/meetings/{self.meeting1.id}/transcribe/', {}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data['transcript'], 'Initial transcript content.')
        self.assertEqual(resp2.data['transcript_file_id'], resp1.data['transcript_file_id'])

        # DB must still have exactly 1 transcript file
        self.assertEqual(MeetingFile.objects.filter(meeting=self.meeting1, file_type='transcript').count(), 1)
        # Deepgram service was only called once, not twice
        self.assertEqual(mock_transcribe.call_count, 1)


@override_settings(
    AWS_ACCESS_KEY_ID='TEST_KEY',
    AWS_SECRET_ACCESS_KEY='TEST_SECRET',
    AWS_STORAGE_BUCKET_NAME='aimeeting-assistant',
    AWS_S3_REGION_NAME='ap-south-1',
    DEEPGRAM_API_KEY='test_deepgram_key',
    GROQ_API_KEY='test_groq_key'
)
class BatchTranscriptionAndSummaryAPITestCase(APITestCase):
    """Integration test suite for batch transcription, transcript retrieval, and Groq summary generation."""

    def setUp(self):
        self.meeting = Meeting.objects.create(title="Q4 Sprint Planning")
        self.audio1 = MeetingFile.objects.create(
            meeting=self.meeting,
            file_type='audio',
            s3_key='meetings/1/audio/rec1.webm',
            original_filename='recording_part1.webm'
        )
        self.audio2 = MeetingFile.objects.create(
            meeting=self.meeting,
            file_type='audio',
            s3_key='meetings/1/audio/rec2.webm',
            original_filename='recording_part2.webm'
        )

    def test_batch_transcribe_empty_meeting(self):
        """Meeting without audio files returns 400."""
        empty_meeting = Meeting.objects.create(title="Empty Meeting")
        res = self.client.post(f'/api/meetings/{empty_meeting.id}/generate-transcripts/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No audio files found', res.data['error'])

    @patch('meetings.views.check_s3_object_exists')
    @patch('meetings.views.transcribe_audio_from_s3')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_batch_transcribe_multiple_audio_files(
        self,
        mock_upload_s3,
        mock_transcribe,
        mock_check_s3
    ):
        """Processes all audio files, associates transcripts with audio files, and returns 200."""
        mock_check_s3.return_value = True
        mock_transcribe.side_effect = [
            {'transcript': 'First part transcript.', 'words_count': 3, 'language': 'multi'},
            {'transcript': 'Second part transcript.', 'words_count': 3, 'language': 'multi'},
        ]

        res = self.client.post(f'/api/meetings/{self.meeting.id}/generate-transcripts/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total'], 2)
        self.assertEqual(res.data['successful'], 2)
        self.assertEqual(len(res.data['results']), 2)

        # Transcripts exist and are linked to audio files
        transcripts = MeetingFile.objects.filter(meeting=self.meeting, file_type='transcript').order_by('id')
        self.assertEqual(transcripts.count(), 2)
        self.assertEqual(transcripts[0].audio_file, self.audio1)
        self.assertEqual(transcripts[1].audio_file, self.audio2)

        # Repeated call does not duplicate
        res_repeat = self.client.post(f'/api/meetings/{self.meeting.id}/generate-transcripts/', {}, format='json')
        self.assertEqual(res_repeat.status_code, status.HTTP_200_OK)
        self.assertEqual(MeetingFile.objects.filter(meeting=self.meeting, file_type='transcript').count(), 2)

    @patch('meetings.views.get_s3_object_bytes')
    def test_transcripts_list_and_detail_content(self, mock_get_s3_bytes):
        """Listing and reading transcript content from S3."""
        t_file = MeetingFile.objects.create(
            meeting=self.meeting,
            audio_file=self.audio1,
            file_type='transcript',
            s3_key='meetings/1/transcripts/rec1_transcript.txt',
            original_filename='recording_part1_transcript.txt'
        )
        mock_get_s3_bytes.return_value = "Hello world transcript text from S3.".encode('utf-8')

        # List
        res_list = self.client.get(f'/api/meetings/{self.meeting.id}/transcripts/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 1)
        self.assertEqual(res_list.data[0]['original_audio_filename'], 'recording_part1.webm')

        # Detail content
        res_detail = self.client.get(f'/api/meetings/{self.meeting.id}/transcripts/{t_file.id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data['content'], "Hello world transcript text from S3.")
        self.assertEqual(res_detail.data['original_audio_filename'], 'recording_part1.webm')

    def test_generate_summary_no_transcripts_error(self):
        """Generating notes with no transcripts returns 400."""
        res = self.client.post(f'/api/meetings/{self.meeting.id}/generate-summary/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No transcripts found', res.data['error'])

    @patch('meetings.views.get_s3_object_bytes')
    @patch('meetings.views.generate_notes_from_transcript_text')
    @patch('meetings.views.upload_s3_object_bytes')
    def test_generate_summary_and_get_summary_success(
        self,
        mock_upload_s3,
        mock_generate_notes,
        mock_get_s3_bytes
    ):
        """Complete workflow for generating structured notes and retrieving from S3."""
        t1 = MeetingFile.objects.create(
            meeting=self.meeting,
            audio_file=self.audio1,
            file_type='transcript',
            s3_key='meetings/1/transcripts/t1.txt',
            original_filename='part1_transcript.txt'
        )
        t2 = MeetingFile.objects.create(
            meeting=self.meeting,
            audio_file=self.audio2,
            file_type='transcript',
            s3_key='meetings/1/transcripts/t2.txt',
            original_filename='part2_transcript.txt'
        )

        mock_get_s3_bytes.side_effect = [
            b"Discussion about architecture and timeline.",
            b"Agreed to deploy on Friday. David is assigned.",
        ]

        mock_generate_notes.return_value = {
            'notes': {
                'meeting_summary': 'Sprint planning finalized timeline and deployment.',
                'key_discussion_points': ['Timeline', 'AWS Deployment'],
                'decisions_made': ['Deploy on Friday'],
                'action_items': [{'task': 'Deploy to AWS', 'owner': 'David', 'deadline': 'Friday 5 PM'}],
                'open_questions': ['Who reviews PR?'],
            },
            'meeting_summary': 'Sprint planning finalized timeline and deployment.',
            'key_discussion_points': ['Timeline', 'AWS Deployment'],
            'decisions_made': ['Deploy on Friday'],
            'action_items': [{'task': 'Deploy to AWS', 'owner': 'David', 'deadline': 'Friday 5 PM'}],
            'open_questions': ['Who reviews PR?'],
            'markdown': '## Meeting Summary\nSprint planning finalized.',
            'model': 'llama-3.3-70b-versatile',
        }

        # POST /generate-summary/
        res_post = self.client.post(f'/api/meetings/{self.meeting.id}/generate-summary/', {}, format='json')
        self.assertEqual(res_post.status_code, status.HTTP_200_OK)
        self.assertEqual(res_post.data['meeting_summary'], 'Sprint planning finalized timeline and deployment.')
        self.assertEqual(len(res_post.data['action_items']), 1)
        self.assertEqual(res_post.data['action_items'][0]['owner'], 'David')

        # Verify combined text passed to mock_generate_notes contains references to both audio files
        mock_generate_notes.assert_called_once()
        combined_arg = mock_generate_notes.call_args[0][0]
        self.assertIn('recording_part1.webm', combined_arg)
        self.assertIn('recording_part2.webm', combined_arg)

        # Verify summary MeetingFile was created
        summary_file = MeetingFile.objects.get(meeting=self.meeting, file_type='summary')
        self.assertIsNotNone(summary_file)

        # GET /summary/
        import json
        mock_get_s3_bytes.side_effect = None
        mock_get_s3_bytes.return_value = json.dumps(mock_generate_notes.return_value['notes']).encode('utf-8')

        res_get = self.client.get(f'/api/meetings/{self.meeting.id}/summary/')
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertTrue(res_get.data['exists'])
        self.assertEqual(res_get.data['meeting_summary'], 'Sprint planning finalized timeline and deployment.')
        self.assertEqual(res_get.data['action_items'][0]['task'], 'Deploy to AWS')

