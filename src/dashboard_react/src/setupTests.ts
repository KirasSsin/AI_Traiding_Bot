import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Auto-cleanup React tree после каждого теста — prevents test pollution
afterEach(() => {
  cleanup()
})

// uPlot вызывает matchMedia при module-load (setPxRatio). jsdom не реализует matchMedia.
// Stub достаточен для unit-тестов pure functions из DrawdownSubchart.
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (_query: string) => ({
      matches: false,
      media: _query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

// jsdom localStorage может отсутствовать ИЛИ быть broken stub — всегда install свой polyfill
if (typeof window !== 'undefined') {
  const hasWorkingStorage =
    !!window.localStorage && typeof window.localStorage.setItem === 'function'
  if (!hasWorkingStorage) {
    let store: Record<string, string> = {}
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: (key: string) => store[key] ?? null,
        setItem: (key: string, value: string) => { store[key] = String(value) },
        removeItem: (key: string) => { delete store[key] },
        clear: () => { store = {} },
        key: (index: number) => Object.keys(store)[index] ?? null,
        get length() { return Object.keys(store).length },
      },
      writable: true,
      configurable: true,
    })
  }
}
