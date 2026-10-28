import logging
from pathlib import Path
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Meeting, MeetingFile
from .serializers import (
    MeetingSerializer,
    MeetingCreateSerializer,
    MeetingFileSerializer,
    UploadUrlRequestSerializer,
    ConfirmFileRequestSerializer,
    TranscribeRequestSerializer,
    TranscribeResponseSerializer,
)
from .s3_utils import (
    generate_presigned_upload_url,
    check_s3_object_exists,
    verify_s3_key_belongs_to_meeting,
    normalize_file_type,
    generate_s3_key,
    get_s3_object_bytes,
    upload_s3_object_bytes,
    delete_s3_object,
)
from .transcription_service import (
    transcribe_audio_from_s3,
    TranscriptionError,
    TranscriptionConfigurationError,
    TranscriptionAuthenticationError,
    TranscriptionRateLimitError,
    TranscriptionTimeoutError,
    TranscriptionBadRequestError,
    TranscriptionServiceError,
)

logger = logging.getLogger(__name__)


class MeetingListCreateView(APIView):
    """
    POST /api/meetings/ - Create a new meeting session
    GET  /api/meetings/ - List meetings, newest first
    """

    def get(self, request):
        meetings = Meeting.objects.all().order_by('-created_at')
        serializer = MeetingSerializer(meetings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MeetingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        meeting = serializer.save()
        output_serializer = MeetingSerializer(meeting)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class MeetingDetailView(APIView):
    """
    GET /api/meetings/<id>/ - Retrieve a meeting and its associated files
    """

    def get(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MeetingSerializer(meeting)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MeetingFileUploadUrlView(APIView):
    """
    POST /api/meetings/<id>/files/upload-url/
    Generate a presigned S3 PUT upload URL for direct client upload
    """

    def post(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UploadUrlRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_type = serializer.validated_data['file_type']
        content_type = serializer.validated_data['content_type']
        filename = serializer.validated_data.get('filename') or None

        try:
            upload_data = generate_presigned_upload_url(
                meeting_id=meeting.id,
                file_type=file_type,
                content_type=content_type,
                original_filename=filename
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Failed to generate upload URL: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response_payload = {
            'upload_url': upload_data['upload_url'],
            'presigned_url': upload_data['upload_url'],
            's3_key': upload_data['s3_key'],
            'http_method': 'PUT',
            'required_headers': {
                'Content-Type': content_type,
            },
            'file_type': upload_data['file_type'],
            'expires_in': upload_data['expires_in'],
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class MeetingFileConfirmView(APIView):
    """
    POST /api/meetings/<id>/files/confirm/
    Verify that an uploaded S3 object exists in the bucket and belongs to this meeting,
    then record its metadata in MeetingFile. Prevents duplicate records.
    """

    def post(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ConfirmFileRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        s3_key = serializer.validated_data['s3_key'].strip()

        # 1. Verify key belongs to this meeting
        if not verify_s3_key_belongs_to_meeting(s3_key, meeting.id):
            return Response(
                {"error": f"S3 key '{s3_key}' does not belong to meeting {meeting.id}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Prevent duplicate file records for the same upload
        if MeetingFile.objects.filter(s3_key=s3_key).exists():
            return Response(
                {"error": f"A file record with S3 key '{s3_key}' has already been confirmed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Verify S3 object exists in bucket
        if not check_s3_object_exists(s3_key):
            return Response(
                {"error": f"Object with key '{s3_key}' does not exist in S3. Please upload the file before confirming."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Resolve file_type
        req_file_type = serializer.validated_data.get('file_type')
        if req_file_type:
            canonical_file_type = req_file_type
        else:
            # Infer from key path
            if '/audio/' in s3_key:
                canonical_file_type = 'audio'
            elif '/transcripts/' in s3_key:
                canonical_file_type = 'transcript'
            elif '/summaries/' in s3_key:
                canonical_file_type = 'summary'
            else:
                canonical_file_type = 'audio'

        # 5. Resolve filename
        original_filename = (
            serializer.validated_data.get('original_filename') or
            serializer.validated_data.get('filename') or
            Path(s3_key).name
        )

        # 6. Create record
        meeting_file = MeetingFile.objects.create(
            meeting=meeting,
            file_type=canonical_file_type,
            s3_key=s3_key,
            original_filename=original_filename
        )

        file_serializer = MeetingFileSerializer(meeting_file)
        return Response(file_serializer.data, status=status.HTTP_201_CREATED)


class MeetingFileListView(APIView):
    """
    GET /api/meetings/<id>/files/ - List files for a meeting
    """

    def get(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        files = meeting.files.all().order_by('-created_at')

        # Optional filter by file_type
        file_type = request.query_params.get('file_type')
        if file_type:
            try:
                canonical_type = normalize_file_type(file_type)
                files = files.filter(file_type=canonical_type)
            except ValueError:
                pass

        serializer = MeetingFileSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MeetingTranscribeView(APIView):
    """
    POST /api/meetings/<id>/transcribe/
    Transcribe a meeting's audio file using Deepgram Nova-3 API.
    Saves the resulting transcript as a UTF-8 .txt file in private S3
    and records its metadata in MeetingFile.
    """

    def post(self, request, pk):
        # 1. Confirm that meeting exists
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate request body
        serializer = TranscribeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        audio_file_id = serializer.validated_data.get('audio_file_id')
        language = serializer.validated_data.get('language') or 'multi'
        retranscribe = serializer.validated_data.get('retranscribe', False)

        # 2. Select audio file unambiguously
        if audio_file_id is not None:
            try:
                audio_file = MeetingFile.objects.get(id=audio_file_id)
            except MeetingFile.DoesNotExist:
                return Response(
                    {"error": f"Audio file with id {audio_file_id} does not exist."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Confirm file ownership
            if audio_file.meeting_id != meeting.id:
                return Response(
                    {"error": f"File with id {audio_file_id} does not belong to meeting {meeting.id}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Confirm file_type == 'audio'
            if audio_file.file_type != 'audio':
                return Response(
                    {"error": f"File with id {audio_file_id} is of type '{audio_file.file_type}', expected 'audio'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # No audio_file_id supplied
            audio_files = meeting.files.filter(file_type='audio')
            audio_count = audio_files.count()

            if audio_count == 0:
                return Response(
                    {"error": "No audio files found for this meeting."},
                    status=status.HTTP_404_NOT_FOUND
                )
            elif audio_count > 1:
                return Response(
                    {"error": "Multiple audio files exist for this meeting. Please specify 'audio_file_id'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                audio_file = audio_files.first()

        # 3. Duplicate handling / idempotency on retries
        audio_stem = Path(audio_file.original_filename).stem if audio_file.original_filename else f"audio_{audio_file.id}"
        transcript_filename = f"{audio_stem}_transcript.txt"

        if not retranscribe:
            existing_transcript = meeting.files.filter(
                file_type='transcript',
                original_filename=transcript_filename
            ).first()

            if existing_transcript and check_s3_object_exists(existing_transcript.s3_key):
                try:
                    cached_bytes = get_s3_object_bytes(existing_transcript.s3_key)
                    cached_text = cached_bytes.decode('utf-8', errors='replace')
                    return Response({
                        'transcript': cached_text,
                        'transcript_file_id': existing_transcript.id,
                        's3_key': existing_transcript.s3_key,
                        'original_filename': existing_transcript.original_filename,
                        'status': 'completed',
                        'message': 'Existing transcript returned.',
                    }, status=status.HTTP_200_OK)
                except Exception as err:
                    logger.warning(f"Could not read existing transcript from S3: {err}. Retranscribing...")

        # 4. Verify audio object exists in S3 bucket
        if not check_s3_object_exists(audio_file.s3_key):
            return Response(
                {"error": f"Audio file '{audio_file.s3_key}' does not exist in S3 storage."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. Send audio to Deepgram Nova-3 API
        try:
            transcription_result = transcribe_audio_from_s3(
                s3_key=audio_file.s3_key,
                language=language
            )
        except TranscriptionConfigurationError:
            return Response(
                {"error": "Deepgram API key is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except TranscriptionAuthenticationError:
            return Response(
                {"error": "Deepgram authentication failed. Please check your API key configuration."},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except TranscriptionRateLimitError:
            return Response(
                {"error": "Deepgram rate limit reached. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except TranscriptionTimeoutError:
            return Response(
                {"error": "Deepgram transcription request timed out."},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except TranscriptionBadRequestError as err:
            return Response(
                {"error": f"Invalid audio request: {str(err)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except TranscriptionServiceError:
            return Response(
                {"error": "Deepgram service is currently unavailable. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except TranscriptionError as err:
            return Response(
                {"error": f"Transcription failed: {str(err)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as err:
            logger.error(f"Unexpected error during transcription: {err}")
            return Response(
                {"error": "An unexpected error occurred during transcription."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        transcript_text = transcription_result.get('transcript', '')

        # 6. Upload transcript to S3 as UTF-8 .txt
        try:
            transcript_s3_key = generate_s3_key(
                meeting_id=meeting.id,
                file_type='transcript',
                content_type='text/plain',
                original_filename=transcript_filename
            )
            upload_s3_object_bytes(
                s3_key=transcript_s3_key,
                data=transcript_text.encode('utf-8'),
                content_type='text/plain; charset=utf-8'
            )
        except Exception as err:
            logger.error(f"Failed to upload transcript to S3 for meeting {meeting.id}: {err}")
            return Response(
                {"error": "Failed to upload transcript to S3 storage."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 7. Create MeetingFile record in SQLite
        try:
            transcript_file = MeetingFile.objects.create(
                meeting=meeting,
                file_type='transcript',
                s3_key=transcript_s3_key,
                original_filename=transcript_filename
            )
        except Exception as err:
            logger.error(f"Failed to save MeetingFile transcript record: {err}. Cleaning up S3 object...")
            delete_s3_object(transcript_s3_key)
            return Response(
                {"error": "Failed to persist transcript metadata in database."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 8. Return response
        return Response({
            'transcript': transcript_text,
            'transcript_file_id': transcript_file.id,
            's3_key': transcript_s3_key,
            'original_filename': transcript_filename,
            'status': 'completed',
            'confidence': transcription_result.get('confidence', 1.0),
            'words_count': transcription_result.get('words_count', 0),
            'language': transcription_result.get('language', language),
        }, status=status.HTTP_200_OK)
