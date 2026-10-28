import re
from rest_framework import serializers
from .models import Meeting, MeetingFile
from .s3_utils import (
    validate_file_type,
    normalize_file_type,
    SUPPORTED_FILE_TYPES,
    generate_presigned_download_url,
)


class MeetingFileSerializer(serializers.ModelSerializer):
    """Serializer for displaying MeetingFile metadata."""
    meeting_id = serializers.IntegerField(source='meeting.id', read_only=True)
    download_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MeetingFile
        fields = [
            'id',
            'meeting_id',
            'file_type',
            's3_key',
            'original_filename',
            'download_url',
            'created_at',
        ]
        read_only_fields = ['id', 'meeting_id', 'download_url', 'created_at']

    def get_download_url(self, obj):
        if not obj or not obj.s3_key:
            return None
        try:
            return generate_presigned_download_url(obj.s3_key, expiration=3600)
        except Exception:
            return None


class MeetingSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and listing Meeting sessions with attached files."""
    files = MeetingFileSerializer(many=True, read_only=True)
    files_count = serializers.IntegerField(source='files.count', read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id',
            'title',
            'created_at',
            'updated_at',
            'files_count',
            'files',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'files_count', 'files']


class MeetingCreateSerializer(serializers.ModelSerializer):
    """Serializer for validating Meeting creation requests."""
    title = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            'required': 'Meeting title is required.',
            'blank': 'Meeting title cannot be blank.',
        }
    )

    class Meta:
        model = Meeting
        fields = ['id', 'title', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UploadUrlRequestSerializer(serializers.Serializer):
    """Serializer for validating presigned upload URL requests."""
    file_type = serializers.CharField(
        required=True,
        error_messages={'required': 'file_type is required.'}
    )
    content_type = serializers.CharField(
        required=True,
        error_messages={'required': 'content_type is required.'}
    )
    filename = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default=''
    )

    def validate(self, attrs):
        file_type = attrs.get('file_type')
        content_type = attrs.get('content_type')

        try:
            canonical_type = normalize_file_type(file_type)
            validate_file_type(canonical_type, content_type)
            attrs['file_type'] = canonical_type
        except ValueError as err:
            raise serializers.ValidationError({'error': str(err)})

        return attrs


class ConfirmFileRequestSerializer(serializers.Serializer):
    """Serializer for validating file confirmation requests."""
    s3_key = serializers.CharField(
        max_length=1024,
        required=True,
        allow_blank=False,
        error_messages={'required': 's3_key is required.'}
    )
    file_type = serializers.CharField(
        required=False,
        allow_blank=True,
        default=''
    )
    filename = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default=''
    )
    original_filename = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default=''
    )

    def validate_file_type(self, value):
        if not value:
            return ''
        try:
            return normalize_file_type(value)
        except ValueError as err:
            raise serializers.ValidationError(str(err))


class TranscribeRequestSerializer(serializers.Serializer):
    """Serializer for validating audio transcription requests."""
    audio_file_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional ID of specific MeetingFile (file_type='audio') to transcribe."
    )
    language = serializers.CharField(
        max_length=32,
        required=False,
        default='multi',
        allow_blank=True,
        help_text="Target language or 'multi' for multilingual code-switching across Gujarati, Hindi, English."
    )
    retranscribe = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Force re-transcription if a transcript already exists."
    )


class TranscribeResponseSerializer(serializers.Serializer):
    """Serializer representing the transcription endpoint response structure."""
    transcript = serializers.CharField(allow_blank=True)
    transcript_file_id = serializers.IntegerField()
    s3_key = serializers.CharField()
    original_filename = serializers.CharField()
    status = serializers.CharField()
    language = serializers.CharField(required=False)
    confidence = serializers.FloatField(required=False)
    words_count = serializers.IntegerField(required=False)
