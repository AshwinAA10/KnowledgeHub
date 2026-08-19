import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { DocumentUpload } from '../components/DocumentUpload'
import { DocumentList } from '../components/DocumentList'
import * as api from '../api/documents'

vi.mock('../api/documents')

describe('DocumentUpload Component', () => {
  const onUploadSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload picker and disabled upload button initially', () => {
    render(<DocumentUpload onUploadSuccess={onUploadSuccess} />)

    expect(screen.getByText('Upload PDF Document')).toBeInTheDocument()
    const submitBtn = screen.getByRole('button', { name: /ingest document/i })
    expect(submitBtn).toBeDisabled()
  })

  it('rejects non-pdf files with an error alert', () => {
    render(<DocumentUpload onUploadSuccess={onUploadSuccess} />)

    const input = document.getElementById('pdf-file-input') as HTMLInputElement
    const file = new File(['text content'], 'notes.txt', { type: 'text/plain' })

    fireEvent.change(input, { target: { files: [file] } })

    expect(
      screen.getByText('Only PDF files (.pdf) are supported.')
    ).toBeInTheDocument()
    const submitBtn = screen.getByRole('button', { name: /ingest document/i })
    expect(submitBtn).toBeDisabled()
  })

  it('handles successful upload workflow', async () => {
    vi.mocked(api.uploadDocument).mockResolvedValueOnce({
      id: 'doc-123',
      filename: 'uuid_sample.pdf',
      original_filename: 'sample.pdf',
      file_size: 1024,
      processing_status: 'completed',
      page_count: 2,
      chunk_count: 5,
      created_at: new Date().toISOString(),
    })

    render(<DocumentUpload onUploadSuccess={onUploadSuccess} />)

    const input = document.getElementById('pdf-file-input') as HTMLInputElement
    const file = new File(['dummy pdf content'], 'sample.pdf', {
      type: 'application/pdf',
    })

    fireEvent.change(input, { target: { files: [file] } })
    const submitBtn = screen.getByRole('button', { name: /ingest document/i })
    expect(submitBtn).not.toBeDisabled()

    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(api.uploadDocument).toHaveBeenCalledWith(file)
      expect(onUploadSuccess).toHaveBeenCalled()
      expect(
        screen.getByText(/Successfully ingested "sample.pdf"/)
      ).toBeInTheDocument()
    })
  })
})

describe('DocumentList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders document list from API', async () => {
    vi.mocked(api.fetchDocuments).mockResolvedValueOnce({
      total: 1,
      documents: [
        {
          id: 'doc-1',
          filename: 'stored_sample.pdf',
          original_filename: 'sample.pdf',
          file_type: 'application/pdf',
          file_size: 2048,
          processing_status: 'completed',
          page_count: 3,
          chunk_count: 6,
          created_at: '2026-08-19T00:00:00Z',
          updated_at: '2026-08-19T00:00:00Z',
        },
      ],
    })

    render(<DocumentList refreshTrigger={0} />)

    await waitFor(() => {
      expect(screen.getByText('sample.pdf')).toBeInTheDocument()
      expect(screen.getByText('completed')).toBeInTheDocument()
      expect(screen.getByText('6')).toBeInTheDocument()
    })
  })

  it('handles delete document interaction', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(api.fetchDocuments).mockResolvedValue({
      total: 1,
      documents: [
        {
          id: 'doc-1',
          filename: 'stored_sample.pdf',
          original_filename: 'sample.pdf',
          file_type: 'application/pdf',
          file_size: 2048,
          processing_status: 'completed',
          page_count: 1,
          chunk_count: 2,
          created_at: '2026-08-19T00:00:00Z',
          updated_at: '2026-08-19T00:00:00Z',
        },
      ],
    })
    vi.mocked(api.deleteDocument).mockResolvedValueOnce({
      message: 'Document deleted successfully',
      id: 'doc-1',
    })

    render(<DocumentList refreshTrigger={0} />)

    await waitFor(() => {
      expect(screen.getByText('sample.pdf')).toBeInTheDocument()
    })

    const deleteBtn = screen.getByRole('button', { name: /delete/i })
    fireEvent.click(deleteBtn)

    await waitFor(() => {
      expect(api.deleteDocument).toHaveBeenCalledWith('doc-1')
    })
  })
})
