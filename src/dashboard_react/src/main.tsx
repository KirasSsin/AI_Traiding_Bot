import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('Root element not found')

createRoot(rootEl).render(
  <StrictMode>
    <div style={{ padding: '2rem', color: '#cc785c', fontFamily: 'monospace' }}>
      <h1>S46 React Infrastructure Ready</h1>
      <p>App component будет implemented в T3</p>
    </div>
  </StrictMode>
)
