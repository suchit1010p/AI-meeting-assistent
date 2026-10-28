import sys
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8000'

print("=== Starting End-to-End Live Workflow Verification ===")

# 1. Create meeting
m_resp = requests.post(f'{BASE}/api/meetings/', json={'title': 'Live End-to-End Test Meeting'})
assert m_resp.status_code == 201, f'Create failed: {m_resp.text}'
meeting = m_resp.json()
meeting_id = meeting['id']
print(f'[OK] 1. Created meeting ID {meeting_id}: {meeting["title"]}')

# 2. Presigned upload URL for audio
up_resp = requests.post(
    f'{BASE}/api/meetings/{meeting_id}/files/upload-url/',
    json={'file_type': 'audio', 'content_type': 'audio/webm', 'filename': 'live_test.webm'}
)
assert up_resp.status_code == 200, f'Upload URL failed: {up_resp.text}'
up_data = up_resp.json()
upload_url = up_data['upload_url']
s3_key = up_data['s3_key']
print(f'[OK] 2. Generated upload URL for S3 key: {s3_key}')

# 3. Direct PUT to S3
dummy_audio = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
s3_put = requests.put(upload_url, data=dummy_audio, headers={'Content-Type': 'audio/webm'})
assert s3_put.status_code in (200, 204), f'S3 PUT failed ({s3_put.status_code}): {s3_put.text}'
print(f'[OK] 3. Direct upload to AWS S3 succeeded (HTTP {s3_put.status_code})')

# 4. Confirm upload
conf_resp = requests.post(
    f'{BASE}/api/meetings/{meeting_id}/files/confirm/',
    json={'s3_key': s3_key, 'file_type': 'audio', 'original_filename': 'live_test.webm'}
)
assert conf_resp.status_code == 201, f'Confirm failed: {conf_resp.text}'
conf_data = conf_resp.json()
file_id = conf_data['id']
print(f'[OK] 4. Confirmed file with Django, MeetingFile ID {file_id}')

# 5. List files
list_resp = requests.get(f'{BASE}/api/meetings/{meeting_id}/files/')
assert list_resp.status_code == 200
files = list_resp.json()
assert any(f['id'] == file_id for f in files)
print(f'[OK] 5. Meeting file list returns confirmed file ({len(files)} file(s))')

# 6. Presigned download URL
dl_resp = requests.get(f'{BASE}/api/meetings/{meeting_id}/files/{file_id}/download-url/')
assert dl_resp.status_code == 200
dl_data = dl_resp.json()
download_url = dl_data['download_url']
print(f'[OK] 6. Presigned download URL generated: {download_url[:60]}...')

# 7. Secure download verification
dl_fetch = requests.get(download_url)
assert dl_fetch.status_code == 200
assert dl_fetch.content == dummy_audio
print(f'[OK] 7. Securely downloaded audio bytes match uploaded data ({len(dl_fetch.content)} bytes)')

# 8. Test Transcript upload and retrieval
tr_url_resp = requests.post(
    f'{BASE}/api/meetings/{meeting_id}/files/upload-url/',
    json={'file_type': 'transcript', 'content_type': 'text/plain', 'filename': 'notes.txt'}
)
tr_up_data = tr_url_resp.json()
test_text = 'Discussion about integration and AWS S3 storage.'
tr_put = requests.put(tr_up_data['upload_url'], data=test_text.encode('utf-8'), headers={'Content-Type': 'text/plain'})
assert tr_put.status_code in (200, 204)
tr_conf = requests.post(
    f'{BASE}/api/meetings/{meeting_id}/files/confirm/',
    json={'s3_key': tr_up_data['s3_key'], 'file_type': 'transcript', 'original_filename': 'notes.txt'}
)
assert tr_conf.status_code == 201
tr_file_id = tr_conf.json()['id']
tr_dl = requests.get(f'{BASE}/api/meetings/{meeting_id}/files/{tr_file_id}/download-url/').json()['download_url']
retrieved_text = requests.get(tr_dl).text
assert retrieved_text == test_text
print(f'[OK] 8. Transcript uploaded to S3, confirmed in DB, and retrieved: "{retrieved_text}"')

# 9. Test Meeting Title Rename
patch_resp = requests.patch(f'{BASE}/api/meetings/{meeting_id}/', json={'title': 'Updated Title For Sync'})
assert patch_resp.status_code == 200
assert patch_resp.json()['title'] == 'Updated Title For Sync'
print('[OK] 9. Meeting title rename succeeded via PATCH')

# 10. Test Deletion of single file
del_file_resp = requests.delete(f'{BASE}/api/meetings/{meeting_id}/files/{file_id}/')
assert del_file_resp.status_code == 204
print('[OK] 10. Single file deletion succeeded via DELETE')

print("=== ALL 10 INTEGRATION VERIFICATION CHECKS PASSED SUCCESSFULLY ===")
