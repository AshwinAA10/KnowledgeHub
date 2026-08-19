import { useState } from 'react'
import './App.css'
import { DocumentUpload } from './components/DocumentUpload'
import { DocumentList } from './components/DocumentList'

function App() {
  const [refreshKey, setRefreshKey] = useState(0)

  const handleUploadSuccess = () => {
    setRefreshKey((prev) => prev + 1)
  }

  return (
    <div className="app">
      <header className="hero">
        <div className="hero-content">
          <div className="logo-mark">
            <span className="logo-icon">⬡</span>
          </div>
          <h1 className="title">KnowledgeHub</h1>
          <p className="subtitle">
            AI-powered personal knowledge platform
          </p>
          <div className="milestone-badge">
            Milestone 1A — Document Ingestion
          </div>
        </div>
      </header>

      <main className="main">
        {/* Document Ingestion Section */}
        <section className="documents-section">
          <h2>Document Ingestion Pipeline</h2>
          <div className="documents-grid">
            <DocumentUpload onUploadSuccess={handleUploadSuccess} />
            <DocumentList refreshTrigger={refreshKey} />
          </div>
        </section>

        {/* Technology Stack Section */}
        <section className="stack-section">
          <h2>Technology Stack</h2>
          <div className="cards">
            <div className="card">
              <span className="card-icon">⚛</span>
              <h3>Frontend</h3>
              <p>React 19 · TypeScript · Vite</p>
            </div>
            <div className="card">
              <span className="card-icon">⚡</span>
              <h3>Backend</h3>
              <p>Python 3.12 · FastAPI · pypdf · asyncpg</p>
            </div>
            <div className="card">
              <span className="card-icon">🗄</span>
              <h3>Database</h3>
              <p>PostgreSQL 17 · pgvector 0.8.6</p>
            </div>
          </div>
        </section>

        {/* Roadmap Section */}
        <section className="roadmap-section">
          <h2>Roadmap</h2>
          <ol className="roadmap">
            <li className="roadmap-item completed">
              <span className="step-num">0</span>
              <span className="step-label">Project Foundation</span>
              <span className="step-status done">Done</span>
            </li>
            <li className="roadmap-item active">
              <span className="step-num">1A</span>
              <span className="step-label">Document Ingestion & Chunking</span>
              <span className="step-status current">Current</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">1B</span>
              <span className="step-label">Embeddings & Vector Storage</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">2</span>
              <span className="step-label">Semantic Retrieval</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">3</span>
              <span className="step-label">RAG + LLM Answers</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">4</span>
              <span className="step-label">Evaluation + Citations</span>
            </li>
          </ol>
        </section>
      </main>

      <footer className="footer">
        <p>
          Backend API:{' '}
          <a
            href={`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            {import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/docs
          </a>
        </p>
      </footer>
    </div>
  )
}

export default App
