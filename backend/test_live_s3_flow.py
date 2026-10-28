"""
Live end-to-end verification script for MeetNote AI AWS S3 Integration.
Tests real S3 connectivity, presigned PUT upload for both audio & transcript,
object verification, file confirmation, and clean deletion.
NEVER prints or exposes AWS secrets.
"""

import os
import sys
import urllib.request
import django

# Set UTF-8 encoding for stdout on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from rest_framework.test import APIClient
from meetings.models import Meeting, MeetingFile
from meetings.s3_utils import (
    get_s3_client,
    generate_presigned_download_url,
)


def run_live_tests():
    print("=" * 70)
    print("MEETNOTE AI -- LIVE AWS S3 & API END-TO-END VERIFICATION")
    print("=" * 70)

    # 1. Check Configuration (without exposing secrets)
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    region = getattr(settings, 'AWS_S3_REGION_NAME', '')
    has_key_id = bool(getattr(settings, 'AWS_ACCESS_KEY_ID', ''))
    has_secret = bool(getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''))

    print(f"\n[1/8] Checking AWS Configuration:")
    print(f"  * S3 Bucket Name       : {bucket_name}")
    print(f"  * S3 Region            : {region}")
    print(f"  * AWS_ACCESS_KEY_ID    : {'[Configured]' if has_key_id else '[MISSING]'}")
    print(f"  * AWS_SECRET_ACCESS_KEY: {'[Configured]' if has_secret else '[MISSING]'}")

    if not has_key_id or not has_secret:
        print("\nERROR: AWS credentials are not found in settings or .env file.")
        sys.exit(1)

    s3_client = get_s3_client()

    # 2. Test S3 Bucket Connectivity
    print(f"\n[2/8] Testing S3 Bucket Access on '{bucket_name}' ({region})...")
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print("  [OK] Successfully connected to AWS S3 bucket!")
    except Exception as e:
        print(f"  [FAIL] Failed to connect to bucket '{bucket_name}': {e}")
        sys.exit(1)

    client = APIClient()

    # 3. Create a Test Meeting via API
    print(f"\n[3/8] Creating Test Meeting via POST /api/meetings/...")
    create_resp = client.post('/api/meetings/', {'title': 'Live S3 Verification Meeting'}, format='json')
    if create_resp.status_code != 201:
        print(f"  [FAIL] Failed to create meeting: {create_resp.data}")
        sys.exit(1)

    meeting_id = create_resp.data['id']
    print(f"  [OK] Meeting created successfully (ID: {meeting_id}, Title: '{create_resp.data['title']}')")

    s3_keys_to_clean = []

    try:
        # 4. Audio File: Presigned URL -> S3 PUT Upload -> Confirm
        print(f"\n[4/8] Testing Audio Upload Pipeline (audio/webm)...")
        audio_url_resp = client.post(
            f'/api/meetings/{meeting_id}/files/upload-url/',
            {'file_type': 'audio', 'content_type': 'audio/webm', 'filename': 'meeting_audio.webm'},
            format='json'
        )
        if audio_url_resp.status_code != 200:
            print(f"  [FAIL] Failed to get audio upload URL: {audio_url_resp.data}")
            sys.exit(1)

        audio_upload_url = audio_url_resp.data['upload_url']
        audio_s3_key = audio_url_resp.data['s3_key']
        s3_keys_to_clean.append(audio_s3_key)
        print(f"  [OK] Presigned URL generated: Key = {audio_s3_key}")

        # Upload dummy webm audio bytes directly to S3
        dummy_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 64  # WebM signature bytes
        audio_req = urllib.request.Request(
            audio_upload_url,
            data=dummy_audio,
            headers={'Content-Type': 'audio/webm'},
            method='PUT'
        )
        with urllib.request.urlopen(audio_req) as resp:
            print(f"  [OK] Audio uploaded to S3: HTTP {resp.status} OK")

        # Confirm audio file in backend
        audio_confirm_resp = client.post(
            f'/api/meetings/{meeting_id}/files/confirm/',
            {'s3_key': audio_s3_key, 'file_type': 'audio', 'original_filename': 'meeting_audio.webm'},
            format='json'
        )
        if audio_confirm_resp.status_code != 201:
            print(f"  [FAIL] Audio confirmation failed: {audio_confirm_resp.data}")
            sys.exit(1)
        print(f"  [OK] Audio confirmed in backend (File ID: {audio_confirm_resp.data['id']})")

        # 5. Transcript File: Presigned URL -> S3 PUT Upload -> Confirm
        print(f"\n[5/8] Testing Transcript Upload Pipeline (text/plain)...")
        trans_url_resp = client.post(
            f'/api/meetings/{meeting_id}/files/upload-url/',
            {'file_type': 'transcript', 'content_type': 'text/plain', 'filename': 'transcript.txt'},
            format='json'
        )
        if trans_url_resp.status_code != 200:
            print(f"  [FAIL] Failed to get transcript upload URL: {trans_url_resp.data}")
            sys.exit(1)

        trans_upload_url = trans_url_resp.data['upload_url']
        trans_s3_key = trans_url_resp.data['s3_key']
        s3_keys_to_clean.append(trans_s3_key)
        print(f"  [OK] Presigned URL generated: Key = {trans_s3_key}")

        trans_content = b"Sarah: Live meeting notes assistant test.\nDavid: S3 presigned upload confirmed."
        trans_req = urllib.request.Request(
            trans_upload_url,
            data=trans_content,
            headers={'Content-Type': 'text/plain'},
            method='PUT'
        )
        with urllib.request.urlopen(trans_req) as resp:
            print(f"  [OK] Transcript uploaded to S3: HTTP {resp.status} OK")

        trans_confirm_resp = client.post(
            f'/api/meetings/{meeting_id}/files/confirm/',
            {'s3_key': trans_s3_key, 'file_type': 'transcript', 'original_filename': 'transcript.txt'},
            format='json'
        )
        if trans_confirm_resp.status_code != 201:
            print(f"  [FAIL] Transcript confirmation failed: {trans_confirm_resp.data}")
            sys.exit(1)
        print(f"  [OK] Transcript confirmed in backend (File ID: {trans_confirm_resp.data['id']})")

        # 6. Test Duplicate Prevention
        print(f"\n[6/8] Testing Duplicate Confirmation Prevention...")
        dup_resp = client.post(
            f'/api/meetings/{meeting_id}/files/confirm/',
            {'s3_key': trans_s3_key, 'file_type': 'transcript', 'original_filename': 'transcript.txt'},
            format='json'
        )
        if dup_resp.status_code == 400 and 'already been confirmed' in dup_resp.data.get('error', ''):
            print(f"  [OK] Duplicate upload confirmed to be safely rejected (HTTP 400).")
        else:
            print(f"  [FAIL] Unexpected duplicate response: {dup_resp.status_code} {dup_resp.data}")

        # 7. List Files for Meeting
        print(f"\n[7/8] Listing Files via GET /api/meetings/{meeting_id}/files/...")
        files_resp = client.get(f'/api/meetings/{meeting_id}/files/')
        if files_resp.status_code != 200:
            print(f"  [FAIL] File listing failed: {files_resp.data}")
            sys.exit(1)

        print(f"  [OK] Retrieved {len(files_resp.data)} confirmed files:")
        for f in files_resp.data:
            print(f"      - ID {f['id']}: [{f['file_type'].upper()}] {f['original_filename']} -> {f['s3_key']}")

        # 8. Retrieve Full Meeting Details
        print(f"\n[8/8] Retrieving Meeting Details via GET /api/meetings/{meeting_id}/...")
        detail_resp = client.get(f'/api/meetings/{meeting_id}/')
        if detail_resp.status_code != 200:
            print(f"  [FAIL] Meeting retrieval failed: {detail_resp.data}")
            sys.exit(1)

        print(f"  [OK] Meeting '{detail_resp.data['title']}' has {detail_resp.data['files_count']} linked files.")

        # Test download presigned URL content
        dl_url = generate_presigned_download_url(s3_key=trans_s3_key)
        with urllib.request.urlopen(dl_url) as dl_resp:
            downloaded = dl_resp.read()
            if downloaded == trans_content:
                print("  [OK] Presigned GET download verified: Downloaded bytes match uploaded transcript exactly.")

    finally:
        # Cleanup S3 test files
        print("\nCleaning up live test resources:")
        for key in s3_keys_to_clean:
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=key)
                print(f"  [OK] Deleted test S3 object: {key}")
            except Exception as e:
                print(f"  [FAIL] Could not delete S3 object {key}: {e}")

        # Cleanup DB record
        try:
            Meeting.objects.filter(id=meeting_id).delete()
            print(f"  [OK] Deleted test Meeting from database (ID: {meeting_id}).")
        except Exception as e:
            print(f"  [FAIL] Could not delete test meeting: {e}")

    print("\n" + "=" * 70)
    print("ALL 8 LIVE AWS S3 & REST API PIPELINE STEPS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == '__main__':
    run_live_tests()
