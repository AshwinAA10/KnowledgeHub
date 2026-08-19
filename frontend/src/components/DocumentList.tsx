import { useState, useEffect, useCallback } from 'react'
import type { DocumentItem, DocumentDetail } from '../types/document'
import { fetchDocuments, fetchDocumentById, deleteDocument } from '../api/documents'

interface DocumentListProps {
  refreshTrigger: number
}

export function DocumentList({ refreshTrigger }: DocumentListProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null)
  const [loadingDocId, setLoadingDocId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchDocuments()
      setDocuments(data.documents)
    } catch (err: any) {
      setError(err.message || 'Failed to load documents.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments, refreshTrigger])

  const handleDelete = async (docId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return
    }

    setDeletingId(docId)
    try {
      await deleteDocument(docId)
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null)
      }
      await loadDocuments()
    } catch (err: any) {
      setError(err.message || 'Failed to delete document.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleInspect = async (docId: string) => {
    if (selectedDoc?.id === docId) {
      setSelectedDoc(null)
      return
    }

    setLoadingDocId(docId)
    try {
      const doc = await fetchDocumentById(docId)
      setSelectedDoc(doc)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch document chunks.')
    } finally {
      setLoadingDocId(null)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="document-list-container card">
      <div className="list-header">
        <div className="list-title-group">
          <span className="card-icon">🗂</span>
          <h3>Ingested Documents ({documents.length})</h3>
        </div>
        <button
          type="button"
          onClick={loadDocuments}
          disabled={isLoading}
          className="btn btn-secondary btn-sm"
        >
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {isLoading && documents.length === 0 ? (
        <div className="empty-state">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          No documents uploaded yet. Upload a PDF document above to begin.
        </div>
      ) : (
        <div className="table-responsive">
          <table className="doc-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Size</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className={selectedDoc?.id === doc.id ? 'row-selected' : ''}>
                  <td className="doc-name-cell">
                    <span className="doc-name" title={doc.original_filename}>
                      {doc.original_filename}
                    </span>
                  </td>
                  <td>{formatFileSize(doc.file_size)}</td>
                  <td>{doc.page_count ?? '—'}</td>
                  <td>
                    <span className="badge badge-neutral">{doc.chunk_count}</span>
                  </td>
                  <td>
                    <span className={`status-badge status-${doc.processing_status}`}>
                      {doc.processing_status}
                    </span>
                  </td>
                  <td className="actions-cell">
                    <button
                      type="button"
                      onClick={() => handleInspect(doc.id)}
                      disabled={loadingDocId === doc.id}
                      className="btn btn-secondary btn-xs"
                      title="Inspect extracted chunks"
                    >
                      {loadingDocId === doc.id
                        ? 'Loading...'
                        : selectedDoc?.id === doc.id
                        ? 'Hide Chunks'
                        : 'Inspect Chunks'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id, doc.original_filename)}
                      disabled={deletingId === doc.id}
                      className="btn btn-danger btn-xs"
                      title="Delete document"
                    >
                      {deletingId === doc.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedDoc && (
        <div className="chunk-inspector">
          <div className="chunk-inspector-header">
            <h4>
              Chunks for &ldquo;{selectedDoc.original_filename}&rdquo; (
              {selectedDoc.chunks.length} total)
            </h4>
            <button
              type="button"
              onClick={() => setSelectedDoc(null)}
              className="btn btn-secondary btn-xs"
            >
              Close
            </button>
          </div>

          {selectedDoc.chunks.length === 0 ? (
            <p className="empty-state">No chunks found for this document.</p>
          ) : (
            <div className="chunk-grid">
              {selectedDoc.chunks.map((chunk) => (
                <div key={chunk.id} className="chunk-card">
                  <div className="chunk-meta">
                    <span className="badge badge-info">
                      Chunk #{chunk.chunk_index}
                    </span>
                    <span className="badge badge-neutral">
                      Page {chunk.page_number ?? '—'}
                    </span>
                    <span className="chunk-chars">
                      {chunk.character_count} chars
                    </span>
                  </div>
                  <pre className="chunk-content">{chunk.content}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
