import { runtimeInfo } from './runtime'
import { DEFAULT_NATIVE_API_BASE, DEFAULT_WEB_API_BASE } from './apiDefaults'
import { loadConfiguredApiUrl } from './appSettings'

export function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim()
  const stored = loadConfiguredApiUrl()
  const shellMode = import.meta.env.MODE
  const isTauriMode = shellMode === 'tauri' || runtimeInfo.shell === 'tauri'

  if (isTauriMode) {
    return import.meta.env.VITE_TAURI_API_BASE_URL?.trim() || stored || configured || DEFAULT_NATIVE_API_BASE
  }

  return stored || configured || DEFAULT_WEB_API_BASE
}
