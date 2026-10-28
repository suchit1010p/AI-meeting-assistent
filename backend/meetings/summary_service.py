"""
Meeting Summary and Analysis Service for MeetNote AI using Groq LLM API.

Retrieves transcript text from private S3, sends combined transcripts to Groq,
and returns structured meeting notes (summary, key points, decisions, action items, open questions).
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

import requests
from django.conf import settings
from .s3_utils import get_s3_object_bytes

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')


# ==============================================================================
# Custom Exceptions for Granular Error Handling
# ==============================================================================

class SummaryError(Exception):
    """Base exception for meeting summary errors."""
    pass


class SummaryConfigurationError(SummaryError):
    """Raised when GROQ_API_KEY is missing or invalid."""
    pass


class SummaryAuthenticationError(SummaryError):
    """Raised when Groq rejects the API key (HTTP 401/403)."""
    pass


class SummaryRateLimitError(SummaryError):
    """Raised when Groq rate limits are encountered (HTTP 429)."""
    pass


class SummaryTimeoutError(SummaryError):
    """Raised when Groq request times out."""
    pass


class SummaryBadRequestError(SummaryError):
    """Raised when Groq returns HTTP 400."""
    pass


class SummaryServiceError(SummaryError):
    """Raised when Groq returns HTTP 5xx."""
    pass


# ==============================================================================
# Groq System Prompt
# ==============================================================================

SYSTEM_PROMPT = """You are an accurate meeting analysis assistant. Analyze the supplied meeting transcripts and produce structured meeting notes.

Return the following sections:

1. Meeting Summary: A concise overview of the meeting.
2. Key Discussion Points: The important topics discussed.
3. Decisions Made: Only decisions explicitly supported by the transcript.
4. Action Items: Each task with its description, assigned owner, and deadline when available.
5. Open Questions: Unresolved questions and issues requiring follow-up.

Rules:
- Never invent facts, decisions, participants, task owners, or deadlines.
- If an owner or deadline is not stated, use 'Not specified'.
- Distinguish a proposed idea from a confirmed decision.
- Preserve important names, numbers, technical terms, and commitments.
- Support Gujarati, Hindi, English, and mixed-language transcripts.
- When multiple audio transcripts belong to one meeting, analyze them together and avoid duplicate action items.
- If the transcript is unclear, explicitly state the uncertainty.
- Return structured, valid JSON with consistent fields so the frontend can display the results reliably.

Output JSON format strictly conforming to this schema:
{
  "meeting_summary": "A concise overview of the meeting (string)",
  "key_discussion_points": ["Important topic 1", "Important topic 2"],
  "decisions_made": ["Explicitly agreed decision 1"],
  "action_items": [
    {
      "task": "Task description",
      "owner": "Assigned owner name or 'Not specified'",
      "deadline": "Deadline date/time or 'Not specified'"
    }
  ],
  "open_questions": ["Unresolved question or issue 1"]
}
"""


def get_groq_api_key() -> str:
    """Retrieve and validate the Groq API key from Django settings / env."""
    api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')
    if not api_key or not api_key.strip():
        raise SummaryConfigurationError(
            "GROQ_API_KEY is not configured in backend environment or settings."
        )
    return api_key.strip()


def format_summary_as_markdown(notes_dict: Dict[str, Any]) -> str:
    """Helper to convert structured JSON notes into human-readable Markdown."""
    lines = []

    lines.append("## Meeting Summary")
    lines.append(notes_dict.get('meeting_summary', '').strip() or "No summary available.")
    lines.append("")

    lines.append("## Key Discussion Points")
    points = notes_dict.get('key_discussion_points', [])
    if points:
        for p in points:
            lines.append(f"- {p}")
    else:
        lines.append("- No key discussion points recorded.")
    lines.append("")

    lines.append("## Decisions Made")
    decisions = notes_dict.get('decisions_made', [])
    if decisions:
        for d in decisions:
            lines.append(f"- {d}")
    else:
        lines.append("- No explicit decisions were recorded.")
    lines.append("")

    lines.append("## Action Items")
    actions = notes_dict.get('action_items', [])
    if actions:
        lines.append("| Task | Owner | Deadline |")
        lines.append("| --- | --- | --- |")
        for item in actions:
            if isinstance(item, dict):
                task = item.get('task', 'Task')
                owner = item.get('owner', 'Not specified')
                deadline = item.get('deadline', 'Not specified')
                lines.append(f"| {task} | {owner} | {deadline} |")
            else:
                lines.append(f"| {item} | Not specified | Not specified |")
    else:
        lines.append("- No action items were assigned.")
    lines.append("")

    lines.append("## Open Questions")
    questions = notes_dict.get('open_questions', [])
    if questions:
        for q in questions:
            lines.append(f"- {q}")
    else:
        lines.append("- No unresolved questions.")
    lines.append("")

    return "\n".join(lines)


def generate_notes_from_transcript_text(
    transcript_text: str,
    model: str = None,
    api_key: Optional[str] = None,
    timeout: int = 90
) -> Dict[str, Any]:
    """
    Send combined transcript text to Groq LLM API and parse structured JSON.

    Args:
        transcript_text: Combined transcript text
        model: Optional model override (defaults to DEFAULT_GROQ_MODEL)
        api_key: Optional API key override
        timeout: Timeout in seconds

    Returns:
        Dict with keys:
            - meeting_summary (str)
            - key_discussion_points (list[str])
            - decisions_made (list[str])
            - action_items (list[dict])
            - open_questions (list[str])
            - raw_json (dict)
            - markdown (str)
            - model (str)
    """
    if not transcript_text or not transcript_text.strip():
        raise SummaryBadRequestError("Combined transcript text is empty.")

    key = api_key or get_groq_api_key()
    selected_model = model or DEFAULT_GROQ_MODEL

    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }

    payload = {
        'model': selected_model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {
                'role': 'user',
                'content': f"Here are the meeting transcripts to analyze:\n\n{transcript_text}"
            }
        ],
        'temperature': 0.2,
        'response_format': {'type': 'json_object'},
        'max_tokens': 4096,
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
    except requests.exceptions.Timeout as e:
        logger.error(f"Groq API request timed out: {e}")
        raise SummaryTimeoutError(f"Groq summary request timed out after {timeout} seconds.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Groq API connection error: {e}")
        raise SummaryError(f"Failed to connect to Groq API: {e}")

    # Handle HTTP error status codes
    if response.status_code in (401, 403):
        raise SummaryAuthenticationError(
            "Groq API authentication failed. Please verify GROQ_API_KEY in backend .env."
        )
    elif response.status_code == 429:
        raise SummaryRateLimitError("Groq API rate limit exceeded. Please try again shortly.")
    elif response.status_code == 400:
        err_msg = ""
        try:
            err_msg = response.json().get('error', {}).get('message', '')
        except Exception:
            err_msg = response.text
        raise SummaryBadRequestError(f"Groq rejected the request: {err_msg}")
    elif response.status_code >= 500:
        raise SummaryServiceError(f"Groq service error (HTTP {response.status_code}).")
    elif response.status_code != 200:
        raise SummaryError(f"Groq returned unexpected status HTTP {response.status_code}: {response.text}")

    # Parse response JSON
    try:
        data = response.json()
    except Exception as e:
        logger.error(f"Malformed JSON from Groq: {e}")
        raise SummaryError("Failed to parse Groq API response.")

    raw_content = ""
    choices = data.get('choices', [])
    if choices and len(choices) > 0:
        message = choices[0].get('message', {})
        raw_content = message.get('content', '')

    if not raw_content:
        raise SummaryError("Groq returned an empty response.")

    try:
        parsed_notes = json.loads(raw_content)
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON content: {raw_content} (Error: {e})")
        # Attempt fallback extraction if wrapped in codeblocks
        import re
        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if match:
            parsed_notes = json.loads(match.group(0))
        else:
            raise SummaryError(f"Groq output was not valid JSON: {raw_content[:200]}")

    # Ensure all required keys exist with default structures
    validated_notes = {
        'meeting_summary': parsed_notes.get('meeting_summary', ''),
        'key_discussion_points': parsed_notes.get('key_discussion_points', []),
        'decisions_made': parsed_notes.get('decisions_made', []),
        'action_items': parsed_notes.get('action_items', []),
        'open_questions': parsed_notes.get('open_questions', []),
    }

    if not isinstance(validated_notes['key_discussion_points'], list):
        validated_notes['key_discussion_points'] = [str(validated_notes['key_discussion_points'])]
    if not isinstance(validated_notes['decisions_made'], list):
        validated_notes['decisions_made'] = [str(validated_notes['decisions_made'])]
    if not isinstance(validated_notes['action_items'], list):
        validated_notes['action_items'] = []
    if not isinstance(validated_notes['open_questions'], list):
        validated_notes['open_questions'] = [str(validated_notes['open_questions'])]

    markdown_version = format_summary_as_markdown(validated_notes)

    return {
        'notes': validated_notes,
        'meeting_summary': validated_notes['meeting_summary'],
        'key_discussion_points': validated_notes['key_discussion_points'],
        'decisions_made': validated_notes['decisions_made'],
        'action_items': validated_notes['action_items'],
        'open_questions': validated_notes['open_questions'],
        'markdown': markdown_version,
        'model': selected_model,
        'usage': data.get('usage', {}),
    }
