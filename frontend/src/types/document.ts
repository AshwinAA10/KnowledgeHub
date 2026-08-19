export interface Chunk {
  id: string
  document_id: string
  chunk_index: number
  content: string
  page_number: number | null
  character_count: number
  created_at: string
}

export interface DocumentItem {
  id: string
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message?: string | null
  page_count?: number | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  total: number
  documents: DocumentItem[]
}

export interface DocumentDetail extends DocumentItem {
  file_path: string
  source: string
  chunks: Chunk[]
}

export interface DocumentUploadResponse {
  id: string
  filename: string
  original_filename: string
  file_size: number
  processing_status: string
  page_count?: number | null
  chunk_count: number
  created_at: string
}
