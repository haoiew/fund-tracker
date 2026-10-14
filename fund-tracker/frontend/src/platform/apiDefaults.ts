export const DEFAULT_WEB_API_BASE = '/api'
export const DEFAULT_NATIVE_API_BASE = 'http://127.0.0.1:8001/api/v1'

export function chooseApiBaseUrl({ stored = '', configured = '', tauriConfigured = '', isTauri = false, dev = false }: {
  stored?: string
  configured?: string
  tauriConfigured?: string
  isTauri?: boolean
  dev?: boolean
}): string {
  if (isTauri) return tauriConfigured.trim() || stored.trim() || configured.trim() || DEFAULT_NATIVE_API_BASE
  // Older settings persisted the native default even for the web shell.
  // Keep custom backends, but let the development proxy own its own default.
  if (dev && stored.trim() === DEFAULT_NATIVE_API_BASE) return configured.trim() || DEFAULT_WEB_API_BASE
  return stored.trim() || configured.trim() || DEFAULT_WEB_API_BASE
}
