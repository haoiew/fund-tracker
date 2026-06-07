export type AppShell = 'web' | 'tauri' | 'electron'

declare global {
  interface Window {
    __TAURI__?: unknown
    electronAPI?: {
      isElectron?: boolean
    }
  }
}

export interface RuntimeInfo {
  shell: AppShell
  isDesktopShell: boolean
  isMobileViewport: boolean
  supportsLocalBackend: boolean
}

export function detectRuntime(): RuntimeInfo {
  const shell: AppShell = window.__TAURI__
    ? 'tauri'
    : window.electronAPI?.isElectron
      ? 'electron'
      : 'web'

  return {
    shell,
    isDesktopShell: shell === 'tauri' || shell === 'electron',
    isMobileViewport: window.matchMedia('(max-width: 760px)').matches,
    supportsLocalBackend: shell !== 'web' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  }
}

export const runtimeInfo = detectRuntime()
