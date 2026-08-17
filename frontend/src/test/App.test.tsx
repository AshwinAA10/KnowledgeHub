/**
 * Smoke Test — App Component
 * ===========================
 * Verifies that the KnowledgeHub root component:
 *  - Renders without throwing
 *  - Displays the application title
 *  - Displays the current milestone badge
 *
 * This is intentionally minimal. Component-level tests will be added
 * as the UI grows in later milestones.
 */

import { render, screen } from '@testing-library/react'
import App from '../App'

describe('App — smoke test', () => {
  it('renders the KnowledgeHub title', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('KnowledgeHub')
  })

  it('displays the milestone badge', () => {
    render(<App />)
    expect(screen.getByText(/Milestone 0/i)).toBeInTheDocument()
  })

  it('renders three technology stack cards', () => {
    render(<App />)
    expect(screen.getByText('Frontend')).toBeInTheDocument()
    expect(screen.getByText('Backend')).toBeInTheDocument()
    expect(screen.getByText('Database')).toBeInTheDocument()
  })
})
