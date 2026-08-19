import { useState, useRef } from 'react'
import { uploadDocument } from '../api/documents'

interface DocumentUploadProps {
  onUploadSuccess: () => void
}

export function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [statusMessage, setStatusMessage] = useState<{
    type: 'success' | 'error' | 'info'
    text: string
  } | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0]
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        setStatusMessage({
          type: 'error',
          text: 'Only PDF files (.pdf) are supported.',
        })
        setFile(null)
        return
      }
      setFile(selected)
      setStatusMessage(null)
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setIsUploading(true)
    setStatusMessage({
      type: 'info',
      text: `Uploading and ingesting "${file.name}"...`,
    })

    try {
      const result = await uploadDocument(file)
      setStatusMessage({
        type: 'success',
        text: `Successfully ingested "${result.original_filename}" (${result.page_count ?? 0} pages, ${result.chunk_count} chunks).`,
      })
      setFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      onUploadSuccess()
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err.message || 'An error occurred during upload.',
      })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="upload-container card">
      <div className="upload-header">
        <span className="card-icon">📄</span>
        <h3>Upload PDF Document</h3>
        <p>Select a PDF to extract text and generate document chunks.</p>
      </div>

      <form onSubmit={handleUpload} className="upload-form">
        <div className="file-input-wrapper">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            disabled={isUploading}
            id="pdf-file-input"
            className="file-input"
          />
          <label htmlFor="pdf-file-input" className="file-label">
            {file ? file.name : 'Choose a PDF file...'}
          </label>
        </div>

        <button
          type="submit"
          disabled={!file || isUploading}
          className="btn btn-primary"
        >
          {isUploading ? 'Ingesting...' : 'Ingest Document'}
        </button>
      </form>

      {statusMessage && (
        <div className={`alert alert-${statusMessage.type}`}>
          {statusMessage.text}
        </div>
      )}
    </div>
  )
}
