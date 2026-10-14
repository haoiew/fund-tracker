import { runtimeInfo } from './runtime'
import { chooseApiBaseUrl } from './apiDefaults'
import { loadConfiguredApiUrl } from './appSettings'

export function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim()
  const stored = loadConfiguredApiUrl()
  const shellMode = import.meta.env.MODE
  const isTauriMode = shellMode === 'tauri' || runtimeInfo.shell === 'tauri'

  return chooseApiBaseUrl({ stored, configured, isTauri: isTauriMode,
    tauriConfigured: import.meta.env.VITE_TAURI_API_BASE_URL, dev: import.meta.env.DEV })
}
