import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('Vitest + RTL infra smoke', () => {
  it('renders a simple component', () => {
    render(<div data-testid="smoke">hello</div>)
    expect(screen.getByTestId('smoke')).toHaveTextContent('hello')
  })

  it('localStorage polyfill works', () => {
    window.localStorage.setItem('k', 'v')
    expect(window.localStorage.getItem('k')).toBe('v')
    window.localStorage.clear()
    expect(window.localStorage.getItem('k')).toBeNull()
  })
})
