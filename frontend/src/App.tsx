import './App.css'

function App() {
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
            Milestone 0 — Foundation
          </div>
        </div>
      </header>

      <main className="main">
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
              <p>Python 3.12 · FastAPI · asyncpg</p>
            </div>
            <div className="card">
              <span className="card-icon">🗄</span>
              <h3>Database</h3>
              <p>PostgreSQL 17 · pgvector</p>
            </div>
          </div>
        </section>

        <section className="roadmap-section">
          <h2>Roadmap</h2>
          <ol className="roadmap">
            <li className="roadmap-item active">
              <span className="step-num">0</span>
              <span className="step-label">Project Foundation</span>
              <span className="step-status current">Current</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">1</span>
              <span className="step-label">Document Ingestion</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">2</span>
              <span className="step-label">Embeddings + Vector Store</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">3</span>
              <span className="step-label">Semantic Retrieval</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">4</span>
              <span className="step-label">RAG + LLM Answers</span>
            </li>
            <li className="roadmap-item">
              <span className="step-num">5</span>
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
