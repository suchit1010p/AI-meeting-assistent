import json
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
    BatchTranscribeRequestSerializer,
    GenerateSummaryRequestSerializer,
)
from .s3_utils import (
    generate_presigned_upload_url,
    generate_presigned_download_url,
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
from .summary_service import (
    generate_notes_from_transcript_text,
    format_summary_as_markdown,
    SummaryError,
    SummaryConfigurationError,
    SummaryAuthenticationError,
    SummaryRateLimitError,
    SummaryTimeoutError,
    SummaryBadRequestError,
    SummaryServiceError,
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

    def patch(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MeetingCreateSerializer(meeting, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_meeting = serializer.save()
        output_serializer = MeetingSerializer(updated_meeting)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete S3 objects associated with meeting
        for file_obj in meeting.files.all():
            try:
                delete_s3_object(file_obj.s3_key)
            except Exception as e:
                logger.warning(f"Could not delete S3 object {file_obj.s3_key}: {e}")

        meeting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class MeetingFileDownloadUrlView(APIView):
    """
    GET /api/meetings/<pk>/files/<file_id>/download-url/
    Verify meeting/file ownership, check S3 object existence, and return a short-lived presigned GET URL.
    """

    def get(self, request, pk, file_id):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            meeting_file = MeetingFile.objects.get(pk=file_id)
        except MeetingFile.DoesNotExist:
            return Response(
                {"error": f"File with id {file_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Confirm ownership
        if meeting_file.meeting_id != meeting.id:
            return Response(
                {"error": f"File with id {file_id} does not belong to meeting {meeting.id}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify S3 object exists
        if not check_s3_object_exists(meeting_file.s3_key):
            return Response(
                {"error": f"Object with key '{meeting_file.s3_key}' does not exist in S3 storage."},
                status=status.HTTP_404_NOT_FOUND
            )

        download_url = generate_presigned_download_url(
            s3_key=meeting_file.s3_key,
            expiration=300
        )

        return Response({
            'download_url': download_url,
            's3_key': meeting_file.s3_key,
            'file_type': meeting_file.file_type,
            'original_filename': meeting_file.original_filename,
            'expires_in': 300,
        }, status=status.HTTP_200_OK)


class MeetingFileDetailView(APIView):
    """
    DELETE /api/meetings/<pk>/files/<file_id>/
    Delete a specific file from SQLite and S3.
    """

    def delete(self, request, pk, file_id):
        try:
            meeting = Meeting.objects.get(pk=pk)
        except Meeting.DoesNotExist:
            return Response(
                {"error": f"Meeting with id {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            meeting_file = MeetingFile.objects.get(pk=file_id, meeting=meeting)
        except MeetingFile.DoesNotExist:
            return Response(
                {"error": f"File with id {file_id} does not exist for meeting {pk}."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Remove from S3
        delete_s3_object(meeting_file.s3_key)

        # Remove from SQLite
        meeting_file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
                audio_file=audio_file,
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
            'audio_file_id': audio_file.id,
            'original_audio_filename': audio_file.original_filename,
            's3_key': transcript_s3_key,
            'original_filename': transcript_filename,
            'status': 'completed',
            'confidence': transcription_result.get('confidence', 1.0),
            'words_count': transcription_result.get('words_count', 0),
            'language': transcription_result.get('language', language),
        }, status=status.HTTP_200_OK)


class MeetingBatchGenerateTranscriptsView(APIView):
    """
    POST /api/meetings/<id>/generate-transcripts/
    Processes all audio files belonging to a meeting.
    Retrieves each audio file using its saved S3 key, checks S3 existence,
    calls Deepgram API with multilingual support (Gujarati, Hindi, English),
    saves each transcript as a UTF-8 .txt file in private S3,
    and records a MeetingFile record linked to the original audio file.
    """

    def post(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)

        serializer = BatchTranscribeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        language = serializer.validated_data.get('language') or 'multi'
        retranscribe = serializer.validated_data.get('retranscribe', False)

        audio_files = meeting.files.filter(file_type='audio').order_by('created_at')
        if not audio_files.exists():
            return Response(
                {"error": "No audio files found for this meeting. Please record or upload audio first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        successful_count = 0
        failed_count = 0

        for audio_file in audio_files:
            audio_stem = Path(audio_file.original_filename).stem if audio_file.original_filename else f"audio_{audio_file.id}"
            transcript_filename = f"{audio_stem}_transcript.txt"

            # Check for existing transcript for this specific audio file
            existing_transcript = meeting.files.filter(
                file_type='transcript',
                audio_file=audio_file
            ).first()

            if not existing_transcript:
                # Also check by original_filename convention
                existing_transcript = meeting.files.filter(
                    file_type='transcript',
                    original_filename=transcript_filename
                ).first()
                if existing_transcript and not existing_transcript.audio_file:
                    existing_transcript.audio_file = audio_file
                    existing_transcript.save(update_fields=['audio_file'])

            if existing_transcript and not retranscribe:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'transcript_file_id': existing_transcript.id,
                    'transcript_filename': existing_transcript.original_filename,
                    's3_key': existing_transcript.s3_key,
                    'status': 'already_exists',
                    'message': 'Existing transcript reused.',
                })
                successful_count += 1
                continue

            # Verify audio file exists in S3
            if not check_s3_object_exists(audio_file.s3_key):
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': f"Audio file not found in S3 ({audio_file.s3_key}).",
                })
                failed_count += 1
                continue

            # Call Deepgram API
            try:
                transcription_result = transcribe_audio_from_s3(
                    s3_key=audio_file.s3_key,
                    language=language
                )
                transcript_text = transcription_result.get('transcript', '')

                # Upload transcript to S3 as UTF-8 .txt
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

                # Save or update MeetingFile record
                if existing_transcript and retranscribe:
                    existing_transcript.s3_key = transcript_s3_key
                    existing_transcript.audio_file = audio_file
                    existing_transcript.original_filename = transcript_filename
                    existing_transcript.save()
                    transcript_file = existing_transcript
                else:
                    transcript_file = MeetingFile.objects.create(
                        meeting=meeting,
                        audio_file=audio_file,
                        file_type='transcript',
                        s3_key=transcript_s3_key,
                        original_filename=transcript_filename
                    )

                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'transcript_file_id': transcript_file.id,
                    'transcript_filename': transcript_filename,
                    's3_key': transcript_s3_key,
                    'status': 'completed',
                    'words_count': transcription_result.get('words_count', 0),
                    'language': transcription_result.get('language', language),
                })
                successful_count += 1

            except TranscriptionConfigurationError:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': 'Deepgram API key is not configured in backend environment.',
                })
                failed_count += 1
            except TranscriptionAuthenticationError:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': 'Deepgram authentication failed. Please verify DEEPGRAM_API_KEY.',
                })
                failed_count += 1
            except TranscriptionRateLimitError:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': 'Deepgram rate limit reached. Please try again shortly.',
                })
                failed_count += 1
            except TranscriptionTimeoutError:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': 'Deepgram request timed out.',
                })
                failed_count += 1
            except TranscriptionBadRequestError as err:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': f"Invalid audio request: {str(err)}",
                })
                failed_count += 1
            except TranscriptionServiceError:
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': 'Deepgram service is temporarily unavailable.',
                })
                failed_count += 1
            except Exception as err:
                logger.error(f"Error transcribing audio file {audio_file.id}: {err}")
                results.append({
                    'audio_file_id': audio_file.id,
                    'audio_filename': audio_file.original_filename,
                    'status': 'failed',
                    'error': str(err),
                })
                failed_count += 1

        return Response({
            'message': f"Processed {len(audio_files)} audio file(s): {successful_count} succeeded, {failed_count} failed.",
            'total': len(audio_files),
            'successful': successful_count,
            'failed': failed_count,
            'results': results,
        }, status=status.HTTP_200_OK if successful_count > 0 or len(audio_files) == 0 else status.HTTP_502_BAD_GATEWAY)


class MeetingTranscriptsListView(APIView):
    """
    GET /api/meetings/<id>/transcripts/
    Lists saved transcript metadata for a meeting.
    """

    def get(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)
        transcripts = meeting.files.filter(file_type='transcript').order_by('-created_at')
        serializer = MeetingFileSerializer(transcripts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MeetingTranscriptDetailContentView(APIView):
    """
    GET /api/meetings/<id>/transcripts/<transcript_id>/
    Retrieves the actual transcript text directly from private S3 using its saved S3 key.
    """

    def get(self, request, pk, transcript_id):
        meeting = get_object_or_404(Meeting, pk=pk)
        transcript_file = get_object_or_404(
            MeetingFile,
            pk=transcript_id,
            meeting=meeting,
            file_type='transcript'
        )

        try:
            bytes_data = get_s3_object_bytes(transcript_file.s3_key)
            content = bytes_data.decode('utf-8', errors='replace')
        except Exception as err:
            logger.error(f"Failed to fetch transcript content from S3 ({transcript_file.s3_key}): {err}")
            return Response(
                {"error": "Failed to retrieve transcript content from S3 storage."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'id': transcript_file.id,
            'meeting_id': meeting.id,
            'audio_file_id': transcript_file.audio_file_id,
            'original_audio_filename': transcript_file.audio_file.original_filename if transcript_file.audio_file else None,
            'original_filename': transcript_file.original_filename,
            'content': content,
            's3_key': transcript_file.s3_key,
            'created_at': transcript_file.created_at,
        }, status=status.HTTP_200_OK)


class MeetingSummaryView(APIView):
    """
    POST /api/meetings/<id>/generate-summary/ (or /summary/)
    GET  /api/meetings/<id>/summary/

    POST:
    1. Retrieves all registered transcript files for the meeting from SQLite.
    2. Fetches each transcript's actual text from private S3.
    3. Combines transcripts in a deterministic order, referencing original audio filenames.
    4. Sends combined text to Groq API using the meeting analysis prompt.
    5. Saves structured JSON meeting notes to private S3.
    6. Creates/updates a MeetingFile record with file_type='summary'.
    7. Returns the generated notes and summary file ID.

    GET:
    Retrieves the saved summary from private S3 and returns structured notes.
    """

    def post(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)

        serializer = GenerateSummaryRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        regenerate = serializer.validated_data.get('regenerate', False)

        # 1. Retrieve all transcripts for this meeting
        transcripts = meeting.files.filter(file_type='transcript').order_by('created_at')
        if not transcripts.exists():
            return Response(
                {"error": "No transcripts found for this meeting. Please click 'Generate Transcripts' first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. If not regenerating, check if a summary file already exists and return it
        if not regenerate:
            existing_summary = meeting.files.filter(file_type='summary').order_by('-created_at').first()
            if existing_summary:
                try:
                    summary_bytes = get_s3_object_bytes(existing_summary.s3_key)
                    raw_text = summary_bytes.decode('utf-8', errors='replace')
                    try:
                        notes_data = json.loads(raw_text)
                    except Exception:
                        notes_data = {
                            'meeting_summary': raw_text,
                            'key_discussion_points': [],
                            'decisions_made': [],
                            'action_items': [],
                            'open_questions': [],
                        }

                    return Response({
                        'summary_file_id': existing_summary.id,
                        's3_key': existing_summary.s3_key,
                        'original_filename': existing_summary.original_filename,
                        'notes': notes_data,
                        'meeting_summary': notes_data.get('meeting_summary', ''),
                        'key_discussion_points': notes_data.get('key_discussion_points', []),
                        'decisions_made': notes_data.get('decisions_made', []),
                        'action_items': notes_data.get('action_items', []),
                        'open_questions': notes_data.get('open_questions', []),
                        'markdown': format_summary_as_markdown(notes_data) if isinstance(notes_data, dict) else raw_text,
                        'status': 'completed',
                        'already_existed': True,
                        'created_at': existing_summary.created_at,
                    }, status=status.HTTP_200_OK)
                except Exception as err:
                    logger.warning(f"Failed to read existing summary from S3: {err}. Generating new summary...")

        # 3. Retrieve text from S3 for all transcripts and combine
        combined_parts = []
        for idx, t in enumerate(transcripts, 1):
            audio_name = t.audio_file.original_filename if t.audio_file else (t.original_filename or f"Audio #{idx}")
            try:
                t_bytes = get_s3_object_bytes(t.s3_key)
                t_text = t_bytes.decode('utf-8', errors='replace').strip()
                if t_text:
                    combined_parts.append(f"=== Audio File {idx}: {audio_name} ===\n{t_text}")
            except Exception as err:
                logger.error(f"Failed to read transcript file {t.id} from S3: {err}")

        if not combined_parts:
            return Response(
                {"error": "Failed to read transcript text from S3 storage."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        combined_text = "\n\n".join(combined_parts)

        # 4. Call Groq LLM API
        try:
            result = generate_notes_from_transcript_text(combined_text)
        except SummaryConfigurationError as err:
            return Response({"error": str(err)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except SummaryAuthenticationError:
            return Response(
                {"error": "Groq authentication failed. Please verify GROQ_API_KEY in backend environment."},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except SummaryRateLimitError:
            return Response(
                {"error": "Groq rate limit exceeded. Please try again shortly."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except SummaryTimeoutError:
            return Response(
                {"error": "Groq request timed out. Please try again."},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except SummaryBadRequestError as err:
            return Response(
                {"error": f"Invalid summary request: {str(err)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SummaryServiceError:
            return Response(
                {"error": "Groq service is temporarily unavailable. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except SummaryError as err:
            return Response(
                {"error": f"Meeting notes generation failed: {str(err)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as err:
            logger.error(f"Unexpected error in summary generation: {err}")
            return Response(
                {"error": "An unexpected error occurred while generating meeting notes."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 5. Save generated notes to S3 as UTF-8 JSON file
        summary_filename = f"meeting_{meeting.id}_notes.json"
        try:
            summary_s3_key = generate_s3_key(
                meeting_id=meeting.id,
                file_type='summary',
                content_type='application/json',
                original_filename=summary_filename
            )
            json_bytes = json.dumps(result['notes'], indent=2).encode('utf-8')
            upload_s3_object_bytes(
                s3_key=summary_s3_key,
                data=json_bytes,
                content_type='application/json; charset=utf-8'
            )
        except Exception as err:
            logger.error(f"Failed to upload summary to S3 for meeting {meeting.id}: {err}")
            return Response(
                {"error": "Failed to upload generated notes to S3 storage."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 6. Create MeetingFile record in SQLite
        try:
            summary_file = MeetingFile.objects.create(
                meeting=meeting,
                file_type='summary',
                s3_key=summary_s3_key,
                original_filename=summary_filename
            )
        except Exception as err:
            logger.error(f"Failed to save MeetingFile summary record: {err}. Cleaning up S3 object...")
            delete_s3_object(summary_s3_key)
            return Response(
                {"error": "Failed to persist summary metadata in database."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'summary_file_id': summary_file.id,
            's3_key': summary_s3_key,
            'original_filename': summary_filename,
            'notes': result['notes'],
            'meeting_summary': result['meeting_summary'],
            'key_discussion_points': result['key_discussion_points'],
            'decisions_made': result['decisions_made'],
            'action_items': result['action_items'],
            'open_questions': result['open_questions'],
            'markdown': result['markdown'],
            'status': 'completed',
            'created_at': summary_file.created_at,
        }, status=status.HTTP_200_OK)

    def get(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)
        summary_file = meeting.files.filter(file_type='summary').order_by('-created_at').first()
        if not summary_file:
            return Response({
                'exists': False,
                'notes': None,
                'message': 'No saved meeting notes exist for this meeting.',
            }, status=status.HTTP_200_OK)

        try:
            bytes_data = get_s3_object_bytes(summary_file.s3_key)
            raw_text = bytes_data.decode('utf-8', errors='replace')
            try:
                notes_data = json.loads(raw_text)
            except Exception:
                notes_data = {
                    'meeting_summary': raw_text,
                    'key_discussion_points': [],
                    'decisions_made': [],
                    'action_items': [],
                    'open_questions': [],
                }
        except Exception as err:
            logger.error(f"Failed to fetch summary from S3 ({summary_file.s3_key}): {err}")
            return Response(
                {"error": "Failed to retrieve meeting notes from S3 storage."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'exists': True,
            'summary_file_id': summary_file.id,
            's3_key': summary_file.s3_key,
            'original_filename': summary_file.original_filename,
            'notes': notes_data,
            'meeting_summary': notes_data.get('meeting_summary', '') if isinstance(notes_data, dict) else '',
            'key_discussion_points': notes_data.get('key_discussion_points', []) if isinstance(notes_data, dict) else [],
            'decisions_made': notes_data.get('decisions_made', []) if isinstance(notes_data, dict) else [],
            'action_items': notes_data.get('action_items', []) if isinstance(notes_data, dict) else [],
            'open_questions': notes_data.get('open_questions', []) if isinstance(notes_data, dict) else [],
            'markdown': format_summary_as_markdown(notes_data) if isinstance(notes_data, dict) else raw_text,
            'created_at': summary_file.created_at,
        }, status=status.HTTP_200_OK)

