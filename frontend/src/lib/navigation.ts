export const VERIFY_REQUIRED_PATH = '/verify-required'

const NEVER_RETURN_TO = new Set(['/login', VERIFY_REQUIRED_PATH])

/**
 * Returns the saved return address if it's a safe in-app path worth going back to,
 * otherwise the dashboard.
 */
export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string') return '/'
  if (!value.startsWith('/') || value.startsWith('//')) return '/'
  if (NEVER_RETURN_TO.has(value)) return '/'
  return value
}
