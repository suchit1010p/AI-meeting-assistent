import os
import re
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
)
from .s3_utils import (
    generate_presigned_upload_url,
    check_s3_object_exists,
    verify_s3_key_belongs_to_meeting,
    normalize_file_type,
)


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
