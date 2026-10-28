import re
from unittest.mock import patch
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
        self.assertTrue(url.startswith('https://aimeeting-assistant.s3.amazonaws.com/'))
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

        self.assertTrue(url.startswith('https://aimeeting-assistant.s3.amazonaws.com/'))
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
