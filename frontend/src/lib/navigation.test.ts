import { describe, expect, it } from 'vitest'

import { safeReturnPath } from './navigation'

describe('safeReturnPath', () => {
  it('keeps an ordinary in-app path', () => {
    expect(safeReturnPath('/documents')).toBe('/documents')
  })

  it('falls back to the dashboard when there is no saved path', () => {
    expect(safeReturnPath(undefined)).toBe('/')
    expect(safeReturnPath(null)).toBe('/')
  })

  it('never returns to the login or verify gate pages', () => {
    expect(safeReturnPath('/login')).toBe('/')
    expect(safeReturnPath('/verify-required')).toBe('/')
  })

  it('rejects addresses that leave the app', () => {
    expect(safeReturnPath('https://evil.example')).toBe('/')
    expect(safeReturnPath('//evil.example')).toBe('/')
  })
})
