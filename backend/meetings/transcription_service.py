"""
Audio Transcription Service for MeetNote AI using Deepgram's Nova-3 API.

Supports multilingual code-switching across Gujarati, Hindi, and English.
Retrieves audio from private S3, sends to Deepgram, and extracts formatted transcripts.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import requests
from django.conf import settings
from .s3_utils import get_s3_object_bytes, get_s3_client

logger = logging.getLogger(__name__)

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"

# MIME type mapping based on file extension
EXTENSION_MIME_MAP = {
    '.webm': 'audio/webm',
    '.wav': 'audio/wav',
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    '.mp4': 'audio/mp4',
}


# ==============================================================================
# Custom Exceptions for Granular Error Handling
# ==============================================================================

class TranscriptionError(Exception):
    """Base exception for transcription failures."""
    pass


class TranscriptionConfigurationError(TranscriptionError):
    """Raised when required configuration (e.g., API key) is missing."""
    pass


class TranscriptionAuthenticationError(TranscriptionError):
    """Raised when Deepgram authentication fails (HTTP 401/403)."""
    pass


class TranscriptionRateLimitError(TranscriptionError):
    """Raised when Deepgram rate limit is reached (HTTP 429)."""
    pass


class TranscriptionTimeoutError(TranscriptionError):
    """Raised when Deepgram request times out."""
    pass


class TranscriptionBadRequestError(TranscriptionError):
    """Raised when Deepgram rejects audio parameters or format (HTTP 400)."""
    pass


class TranscriptionServiceError(TranscriptionError):
    """Raised when Deepgram returns a 5xx service error."""
    pass


# ==============================================================================
# Deepgram Transcription Logic
# ==============================================================================

def get_deepgram_api_key() -> str:
    """Retrieve and validate the Deepgram API key from Django settings / env."""
    api_key = getattr(settings, 'DEEPGRAM_API_KEY', None) or os.environ.get('DEEPGRAM_API_KEY')
    if not api_key or not api_key.strip():
        raise TranscriptionConfigurationError(
            "DEEPGRAM_API_KEY is not configured in environment or settings."
        )
    return api_key.strip()


def resolve_audio_content_type(s3_key: str, default: str = 'audio/webm') -> str:
    """Infer audio MIME type from S3 key file extension."""
    ext = Path(s3_key).suffix.lower()
    return EXTENSION_MIME_MAP.get(ext, default)


def transcribe_audio_bytes(
    audio_bytes: bytes,
    content_type: str = 'audio/webm',
    language: str = 'multi',
    api_key: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Send raw audio bytes to Deepgram Nova-3 API and extract transcript text.

    Args:
        audio_bytes: Raw audio data
        content_type: Audio MIME type (e.g. 'audio/webm', 'audio/wav')
        language: Language code or 'multi' for multilingual code-switching
        api_key: Optional API key override (defaults to environment setting)
        timeout: Request timeout in seconds

    Returns:
        dict:
            - transcript: Extracted formatted transcript text
            - confidence: Average transcription confidence
            - words_count: Number of recognized words
            - language: Language requested/detected
            - model: 'nova-3'

    Raises:
        TranscriptionError or specific subclass on failure.
    """
    if not audio_bytes or len(audio_bytes) == 0:
        raise TranscriptionBadRequestError("Audio content is empty (0 bytes).")

    key = api_key or get_deepgram_api_key()

    headers = {
        'Authorization': f'Token {key}',
        'Content-Type': content_type or 'audio/webm',
    }

    # Deepgram Nova-3 multilingual parameters
    params = {
        'model': 'nova-3',
        'smart_format': 'true',
        'punctuate': 'true',
        'paragraphs': 'true',
    }

    # Configure multilingual vs specific language
    cleaned_lang = language.strip().lower() if language else 'multi'
    if cleaned_lang in ('multi', 'multilingual'):
        params['language'] = 'multi'
    else:
        params['language'] = cleaned_lang

    try:
        response = requests.post(
            DEEPGRAM_API_URL,
            params=params,
            headers=headers,
            data=audio_bytes,
            timeout=timeout
        )
    except requests.exceptions.Timeout as e:
        logger.error(f"Deepgram API request timed out after {timeout}s: {e}")
        raise TranscriptionTimeoutError(f"Deepgram transcription request timed out: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Deepgram API connection error: {e}")
        raise TranscriptionError(f"Deepgram connection failed: {e}")

    # Handle HTTP error statuses
    if response.status_code == 401 or response.status_code == 403:
        raise TranscriptionAuthenticationError(
            "Deepgram authentication failed. Please verify DEEPGRAM_API_KEY."
        )
    elif response.status_code == 429:
        raise TranscriptionRateLimitError(
            "Deepgram API rate limit exceeded. Please retry later."
        )
    elif response.status_code == 400:
        try:
            err_json = response.json()
            err_msg = err_json.get('err_msg') or err_json.get('message') or response.text
        except Exception:
            err_msg = response.text
        raise TranscriptionBadRequestError(f"Deepgram rejected audio request: {err_msg}")
    elif response.status_code >= 500:
        raise TranscriptionServiceError(
            f"Deepgram service error (HTTP {response.status_code})."
        )
    elif response.status_code != 200:
        raise TranscriptionError(
            f"Deepgram unexpected status code HTTP {response.status_code}: {response.text}"
        )

    # Parse response JSON
    try:
        data = response.json()
    except Exception as e:
        logger.error(f"Malformed JSON response from Deepgram: {e}")
        raise TranscriptionError("Malformed JSON received from Deepgram.")

    # Extract transcript text
    transcript_text = ''
    confidence = 1.0
    words = []

    if isinstance(data, dict):
        results = data.get('results', {})
        channels = results.get('channels', []) if isinstance(results, dict) else []
        if channels and len(channels) > 0:
            alternatives = channels[0].get('alternatives', [])
            if alternatives and len(alternatives) > 0:
                primary = alternatives[0]
                paragraphs_obj = primary.get('paragraphs', {})
                transcript_text = (
                    paragraphs_obj.get('transcript')
                    or primary.get('transcript', '')
                    or ''
                )
                confidence = primary.get('confidence', 1.0)
                words = primary.get('words', [])
    else:
        raise TranscriptionError("Malformed JSON received from Deepgram (root is not a dict).")

    return {
        'transcript': transcript_text.strip() if isinstance(transcript_text, str) else '',
        'confidence': confidence,
        'words_count': len(words) if isinstance(words, list) else 0,
        'language': cleaned_lang,
        'model': 'nova-3',
        'raw_response': data,
    }


def transcribe_audio_from_s3(
    s3_key: str,
    language: str = 'multi',
    s3_client: Optional[Any] = None,
    api_key: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Retrieve audio file bytes from the private S3 bucket and transcribe via Deepgram.

    Args:
        s3_key: S3 object key of the audio file
        language: Language code ('multi', 'gu', 'hi', 'en')
        s3_client: Optional boto3 S3 client
        api_key: Optional Deepgram API key override
        timeout: Request timeout in seconds

    Returns:
        dict containing transcript text, confidence, words_count, language, model.
    """
    logger.info(f"Retrieving audio from S3 key '{s3_key}' for transcription...")
    audio_bytes = get_s3_object_bytes(s3_key, s3_client=s3_client)
    content_type = resolve_audio_content_type(s3_key)

    logger.info(f"Sending {len(audio_bytes)} bytes ({content_type}) to Deepgram Nova-3 (language={language})...")
    return transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        content_type=content_type,
        language=language,
        api_key=api_key,
        timeout=timeout
    )
