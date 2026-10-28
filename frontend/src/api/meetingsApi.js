/**
 * Centralized API Client for MeetNote AI Django REST Framework Backend
 * Manages meetings, direct S3 uploads, file confirmations, and presigned download URLs.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

/**
 * Low-level HTTP helper with structured error handling.
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`
  const headers = {
    Accept: 'application/json',
    ...(options.headers || {}),
  }

  if (options.body && !(options.body instanceof FormData) && typeof options.body === 'object') {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  let response
  try {
    response = await fetch(url, { ...options, headers })
  } catch (networkError) {
    console.error(`[API Network Error] ${options.method || 'GET'} ${url}:`, networkError)
    throw new Error(`Unable to connect to backend server at ${API_BASE_URL}. Please ensure Django is running.`)
  }

  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  let responseData
  if (contentType.includes('application/json')) {
    responseData = await response.json().catch(() => null)
  } else {
    responseData = await response.text().catch(() => null)
  }

  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status})`
    if (responseData) {
      if (typeof responseData === 'string') {
        message = responseData
      } else if (responseData.error) {
        message = responseData.error
      } else if (responseData.detail) {
        message = responseData.detail
      } else {
        message = Object.entries(responseData)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : val}`)
          .join('; ')
      }
    }
    const error = new Error(message)
    error.status = response.status
    error.data = responseData
    throw error
  }

  return responseData
}

export const meetingsApi = {
  /**
   * List all meetings, ordered newest first.
   */
  async listMeetings() {
    return apiRequest('/api/meetings/')
  },

  /**
   * Retrieve a specific meeting and its associated files.
   */
  async getMeeting(meetingId) {
    return apiRequest(`/api/meetings/${meetingId}/`)
  },

  /**
   * Create a new meeting session.
   */
  async createMeeting(title) {
    return apiRequest('/api/meetings/', {
      method: 'POST',
      body: { title: title || 'New Meeting' },
    })
  },

  /**
   * Update a meeting title.
   */
  async updateMeeting(meetingId, data) {
    return apiRequest(`/api/meetings/${meetingId}/`, {
      method: 'PATCH',
      body: data,
    })
  },

  /**
   * Delete a meeting and all associated files.
   */
  async deleteMeeting(meetingId) {
    return apiRequest(`/api/meetings/${meetingId}/`, {
      method: 'DELETE',
    })
  },

  /**
   * List files for a meeting, optionally filtered by file_type ('audio', 'transcript', 'summary').
   */
  async listFiles(meetingId, fileType) {
    const query = fileType ? `?file_type=${encodeURIComponent(fileType)}` : ''
    return apiRequest(`/api/meetings/${meetingId}/files/${query}`)
  },

  /**
   * Request a presigned PUT URL for direct S3 upload from the browser.
   */
  async getUploadUrl(meetingId, { file_type, content_type, filename }) {
    return apiRequest(`/api/meetings/${meetingId}/files/upload-url/`, {
      method: 'POST',
      body: {
        file_type,
        content_type,
        filename: filename || '',
      },
    })
  },

  /**
   * Upload raw Blob or File directly to private AWS S3 using presigned PUT URL.
   * Note: AWS credentials are NOT exposed to frontend; S3 enforces headers signed in presigned URL.
   */
  async uploadToS3(uploadUrl, fileBlob, contentType) {
    const headers = {}
    if (contentType) {
      headers['Content-Type'] = contentType
    }

    let response
    try {
      response = await fetch(uploadUrl, {
        method: 'PUT',
        headers,
        body: fileBlob,
      })
    } catch (err) {
      console.error('[S3 Upload Network Error]', err)
      throw new Error(`Failed to upload file directly to S3: ${err.message}`)
    }

    if (!response.ok) {
      let detail = ''
      try {
        detail = await response.text()
      } catch (e) {
        // ignore
      }
      console.error('[S3 Upload Error]', response.status, detail)
      throw new Error(`AWS S3 rejected the direct upload (HTTP ${response.status}). ${detail ? 'Details: ' + detail : ''}`.trim())
    }

    return true
  },

  /**
   * Confirm that an S3 object was successfully uploaded and record its metadata in SQLite.
   */
  async confirmFile(meetingId, { s3_key, file_type, original_filename, filename }) {
    return apiRequest(`/api/meetings/${meetingId}/files/confirm/`, {
      method: 'POST',
      body: {
        s3_key,
        file_type: file_type || '',
        original_filename: original_filename || filename || '',
        filename: filename || original_filename || '',
      },
    })
  },

  /**
   * Request a fresh presigned GET download URL for secure remote file access.
   */
  async getFileDownloadUrl(meetingId, fileId) {
    return apiRequest(`/api/meetings/${meetingId}/files/${fileId}/download-url/`)
  },

  /**
   * Delete a specific file from SQLite and S3.
   */
  async deleteFile(meetingId, fileId) {
    return apiRequest(`/api/meetings/${meetingId}/files/${fileId}/`, {
      method: 'DELETE',
    })
  },

  /**
   * Fetch UTF-8 text content directly from a presigned S3 GET URL.
   */
  async fetchTextFromS3(presignedGetUrl) {
    if (!presignedGetUrl) return ''
    try {
      const response = await fetch(presignedGetUrl)
      if (!response.ok) {
        throw new Error(`Failed to fetch text from S3 (HTTP ${response.status})`)
      }
      return await response.text()
    } catch (err) {
      console.warn('[S3 Text Retrieval Error]', err)
      throw err
    }
  },
}

export default meetingsApi
