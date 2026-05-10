import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/globals.css'

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('Root element not found')

createRoot(rootEl).render(
  <StrictMode>
    <div style={{ padding: '2rem' }}>
      <h1 style={{ color: 'var(--color-anthropic-orange)', fontFamily: 'var(--font-mono)' }}>
        S46 React + Anthropic/Cyberpunk Tokens Ready
      </h1>
      <p style={{ color: 'var(--color-text-secondary)', marginTop: '1rem' }}>
        Design tokens loaded. App component coming in T3.
      </p>
    </div>
  </StrictMode>
)
