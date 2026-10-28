"""
Reusable AWS S3 utility module for MeetNote AI.

Provides functions to generate presigned PUT upload URLs and presigned GET download URLs,
enforcing strict file-type validation, unique S3 key generation, and private bucket security.
Credentials are read strictly from Django settings / environment variables.
"""

import os
import uuid
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# Supported meeting file categories, target folders, and allowed MIME types
SUPPORTED_FILE_TYPES: Dict[str, Dict[str, Any]] = {
    'audio': {
        'folder': 'audio',
        'allowed_content_types': {
            'audio/webm': '.webm',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
        },
    },
    'transcript': {
        'folder': 'transcripts',
        'allowed_content_types': {
            'text/plain': '.txt',
        },
    },
    'summary': {
        'folder': 'summaries',
        'allowed_content_types': {
            'text/plain': '.txt',
        },
    },
}

# Alias mapping for plural inputs
FILE_TYPE_ALIASES = {
    'transcripts': 'transcript',
    'summaries': 'summary',
    'audios': 'audio',
}


def normalize_file_type(file_type: str) -> str:
    """Normalize input file_type string to canonical singular key."""
    if not file_type or not isinstance(file_type, str):
        raise ValueError("file_type must be a non-empty string.")
    cleaned = file_type.strip().lower()
    return FILE_TYPE_ALIASES.get(cleaned, cleaned)


def validate_file_type(file_type: str, content_type: str) -> tuple[str, str]:
    """
    Validate that the file_type and content_type are strictly supported.

    Args:
        file_type: 'audio', 'transcript', or 'summary'
        content_type: MIME type (e.g., 'audio/webm', 'text/plain')

    Returns:
        tuple (folder_name, default_extension)

    Raises:
        ValueError: If file_type or content_type is unsupported.
    """
    canonical_type = normalize_file_type(file_type)

    if canonical_type not in SUPPORTED_FILE_TYPES:
        allowed_types = list(SUPPORTED_FILE_TYPES.keys())
        raise ValueError(
            f"Unsupported file_type '{file_type}'. Supported types are: {allowed_types}"
        )

    config = SUPPORTED_FILE_TYPES[canonical_type]
    allowed_content_types = config['allowed_content_types']

    cleaned_content_type = content_type.strip().lower() if content_type else ''
    if cleaned_content_type not in allowed_content_types:
        supported_mimes = list(allowed_content_types.keys())
        raise ValueError(
            f"Unsupported content_type '{content_type}' for file_type '{canonical_type}'. "
            f"Supported content types: {supported_mimes}"
        )

    folder_name = config['folder']
    default_extension = allowed_content_types[cleaned_content_type]
    return folder_name, default_extension


def generate_s3_key(
    meeting_id: Union[int, str],
    file_type: str,
    content_type: str,
    original_filename: Optional[str] = None
) -> str:
    """
    Generate a unique S3 object key organized by meeting ID and file type.

    Format:
        meetings/<meeting_id>/audio/<unique_filename>.webm
        meetings/<meeting_id>/transcripts/<unique_filename>.txt
        meetings/<meeting_id>/summaries/<unique_filename>.txt

    Args:
        meeting_id: Identifier of the meeting
        file_type: 'audio', 'transcript', or 'summary'
        content_type: MIME type of the file
        original_filename: Optional original filename to preserve extension if matching

    Returns:
        Unique S3 object key string
    """
    if not meeting_id:
        raise ValueError("meeting_id must be provided to organize S3 object keys.")

    folder, default_ext = validate_file_type(file_type, content_type)

    # Determine extension
    ext = default_ext
    if original_filename:
        file_ext = Path(original_filename).suffix.lower()
        allowed_exts = SUPPORTED_FILE_TYPES[normalize_file_type(file_type)]['allowed_content_types'].values()
        if file_ext in allowed_exts:
            ext = file_ext

    # Generate UUID-based unique filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    return f"meetings/{meeting_id}/{folder}/{unique_filename}"


def get_s3_client():
    """
    Initialize and return a boto3 S3 client configured with Signature Version 4.
    Credentials are read from Django settings (which source from environment variables).
    """
    aws_access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None) or os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None) or os.environ.get('AWS_SECRET_ACCESS_KEY')
    region_name = getattr(settings, 'AWS_S3_REGION_NAME', None) or os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')

    # Configure client with signature version s3v4 (required for modern presigned URLs)
    client_config = Config(
        signature_version='s3v4',
        region_name=region_name,
        retries={'max_attempts': 3, 'mode': 'standard'}
    )

    client_kwargs = {
        'service_name': 's3',
        'config': client_config,
        'region_name': region_name,
    }

    endpoint_url = getattr(settings, 'AWS_S3_ENDPOINT_URL', None) or os.environ.get('AWS_S3_ENDPOINT_URL')
    if not endpoint_url and region_name:
        endpoint_url = f"https://s3.{region_name}.amazonaws.com"

    if endpoint_url:
        client_kwargs['endpoint_url'] = endpoint_url

    if aws_access_key and aws_secret_key:
        client_kwargs['aws_access_key_id'] = aws_access_key
        client_kwargs['aws_secret_access_key'] = aws_secret_key

    return boto3.client(**client_kwargs)


def generate_presigned_upload_url(
    meeting_id: Union[int, str],
    file_type: str,
    content_type: str,
    original_filename: Optional[str] = None,
    expiration: Optional[int] = None,
    s3_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate a presigned PUT URL allowing clients to upload a file directly to private S3.

    Args:
        meeting_id: Meeting ID to organize folder path
        file_type: 'audio', 'transcript', or 'summary'
        content_type: MIME type of the file ('audio/webm', 'text/plain', etc.)
        original_filename: Optional original filename
        expiration: URL lifetime in seconds (defaults to settings.AWS_S3_PRESIGNED_EXPIRATION or 300)
        s3_client: Optional boto3 client instance (useful for dependency injection or testing)

    Returns:
        dict:
            - upload_url: Presigned PUT URL
            - s3_key: Generated S3 object key
            - bucket: S3 bucket name
            - file_type: Canonical file type ('audio', 'transcript', 'summary')
            - content_type: Validated MIME type
            - expires_in: Expiration duration in seconds

    Raises:
        ValueError: If parameters or MIME types are invalid
        ClientError / BotoCoreError: If S3 client encounters an error
    """
    canonical_type = normalize_file_type(file_type)
    validate_file_type(canonical_type, content_type)

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get(
        'AWS_STORAGE_BUCKET_NAME', 'aimeeting-assistant'
    )
    if not bucket_name:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not configured.")

    exp_seconds = expiration or getattr(settings, 'AWS_S3_PRESIGNED_EXPIRATION', 300)

    # Generate unique key
    s3_key = generate_s3_key(
        meeting_id=meeting_id,
        file_type=canonical_type,
        content_type=content_type,
        original_filename=original_filename
    )

    client = s3_client or get_s3_client()

    try:
        presigned_url = client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type,
            },
            ExpiresIn=exp_seconds,
            HttpMethod='PUT'
        )

        return {
            'upload_url': presigned_url,
            's3_key': s3_key,
            'bucket': bucket_name,
            'file_type': canonical_type,
            'content_type': content_type,
            'expires_in': exp_seconds,
        }
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to generate presigned S3 upload URL for key '{s3_key}': {e}")
        raise


def generate_presigned_download_url(
    s3_key: str,
    expiration: Optional[int] = None,
    s3_client: Optional[Any] = None
) -> str:
    """
    Generate a presigned GET URL for securely downloading/viewing a private S3 object.
    Bucket remains private; no public ACLs are used.

    Args:
        s3_key: S3 object key
        expiration: URL lifetime in seconds (defaults to settings.AWS_S3_PRESIGNED_EXPIRATION or 300)
        s3_client: Optional boto3 client instance

    Returns:
        str: Presigned GET URL
    """
    if not s3_key or not isinstance(s3_key, str):
        raise ValueError("s3_key must be a non-empty string.")

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get(
        'AWS_STORAGE_BUCKET_NAME', 'aimeeting-assistant'
    )
    if not bucket_name:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not configured.")

    exp_seconds = expiration or getattr(settings, 'AWS_S3_PRESIGNED_EXPIRATION', 300)
    client = s3_client or get_s3_client()

    try:
        return client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
            },
            ExpiresIn=exp_seconds,
            HttpMethod='GET'
        )
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to generate presigned S3 download URL for key '{s3_key}': {e}")
        raise


def check_s3_object_exists(
    s3_key: str,
    s3_client: Optional[Any] = None
) -> bool:
    """
    Verify if an object exists in the configured S3 bucket using head_object.

    Args:
        s3_key: S3 object key to check
        s3_client: Optional boto3 client instance

    Returns:
        bool: True if object exists in the bucket, False otherwise.
    """
    if not s3_key or not isinstance(s3_key, str):
        return False

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get(
        'AWS_STORAGE_BUCKET_NAME', 'aimeeting-assistant'
    )
    if not bucket_name:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not configured.")

    client = s3_client or get_s3_client()
    try:
        client.head_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        error_code = str(e.response.get('Error', {}).get('Code', ''))
        if error_code in ('404', 'NoSuchKey', 'NotFound'):
            return False
        logger.warning(f"S3 head_object error for key '{s3_key}': {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error checking S3 object existence for '{s3_key}': {e}")
        return False


def verify_s3_key_belongs_to_meeting(s3_key: str, meeting_id: Union[int, str]) -> bool:
    """
    Verify that an S3 key follows the expected structure and belongs to the specified meeting.
    Expected prefix: 'meetings/<meeting_id>/'

    Args:
        s3_key: S3 object key to inspect
        meeting_id: Meeting ID

    Returns:
        bool: True if key belongs to the meeting, False otherwise.
    """
    if not s3_key or not meeting_id:
        return False
    expected_prefix = f"meetings/{meeting_id}/"
    return s3_key.startswith(expected_prefix)


def get_s3_object_bytes(s3_key: str, s3_client: Optional[Any] = None) -> bytes:
    """
    Download and return bytes of an S3 object from the private bucket.

    Args:
        s3_key: S3 object key
        s3_client: Optional boto3 client instance

    Returns:
        bytes: Raw object content
    """
    if not s3_key:
        raise ValueError("s3_key must be provided.")

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get(
        'AWS_STORAGE_BUCKET_NAME', 'aimeeting-assistant'
    )
    if not bucket_name:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not configured.")

    client = s3_client or get_s3_client()
    try:
        response = client.get_object(Bucket=bucket_name, Key=s3_key)
        return response['Body'].read()
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to read S3 object '{s3_key}': {e}")
        raise


def upload_s3_object_bytes(
    s3_key: str,
    data: bytes,
    content_type: str = 'text/plain; charset=utf-8',
    s3_client: Optional[Any] = None
) -> None:
    """
    Upload raw bytes directly to the private S3 bucket.

    Args:
        s3_key: Destination S3 key
        data: Raw bytes to upload
        content_type: MIME type
        s3_client: Optional boto3 client instance
    """
    if not s3_key:
        raise ValueError("s3_key must be provided.")

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get(
        'AWS_STORAGE_BUCKET_NAME', 'aimeeting-assistant'
    )
    if not bucket_name:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not configured.")

    client = s3_client or get_s3_client()
    try:
        client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=data,
            ContentType=content_type
        )
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to upload S3 object '{s3_key}': {e}")
        raise


def delete_s3_object(s3_key: str, s3_client: Optional[Any] = None) -> bool:
    """
    Delete an S3 object from the configured bucket.

    Args:
        s3_key: S3 object key to delete
        s3_client: Optional boto3 client instance

    Returns:
        bool: True if deleted or already absent, False on error.
    """
    if not s3_key:
        return False

    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None) or os.environ.get(
        'AWS_STORAGE_BUCKET_NAME', 'aimeeting-assistant'
    )
    if not bucket_name:
        raise ValueError("AWS_STORAGE_BUCKET_NAME is not configured.")

    client = s3_client or get_s3_client()
    try:
        client.delete_object(Bucket=bucket_name, Key=s3_key)
        return True
    except Exception as e:
        logger.warning(f"Failed to delete S3 object '{s3_key}': {e}")
        return False


