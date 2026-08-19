import type {
  DocumentListResponse,
  DocumentDetail,
  DocumentUploadResponse,
} from '../types/document'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(
      errorData.detail || `Upload failed with HTTP status ${res.status}`
    )
  }

  return res.json()
}

export async function fetchDocuments(
  limit = 50,
  offset = 0
): Promise<DocumentListResponse> {
  const res = await fetch(`${API_BASE_URL}/documents?limit=${limit}&offset=${offset}`)

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(
      errorData.detail || `Failed to fetch documents: HTTP ${res.status}`
    )
  }

  return res.json()
}

export async function fetchDocumentById(id: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE_URL}/documents/${id}`)

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(
      errorData.detail || `Failed to fetch document: HTTP ${res.status}`
    )
  }

  return res.json()
}

export async function deleteDocument(id: string): Promise<{ message: string; id: string }> {
  const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
    method: 'DELETE',
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(
      errorData.detail || `Failed to delete document: HTTP ${res.status}`
    )
  }

  return res.json()
}
