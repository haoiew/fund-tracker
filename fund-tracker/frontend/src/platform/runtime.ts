export type AppShell = 'web' | 'tauri'

declare global {
  interface Window {
    __TAURI__?: unknown
  }
}

export interface RuntimeInfo {
  shell: AppShell
  isDesktopShell: boolean
  isAndroidShell: boolean
  isMobileViewport: boolean
  supportsLocalBackend: boolean
}

export function detectRuntime(): RuntimeInfo {
  const shell: AppShell = window.__TAURI__ ? 'tauri' : 'web'
  const isAndroidShell = shell === 'tauri' && /Android/i.test(navigator.userAgent)

  return {
    shell,
    isDesktopShell: shell === 'tauri' && !isAndroidShell,
    isAndroidShell,
    isMobileViewport: window.matchMedia('(max-width: 760px)').matches,
    supportsLocalBackend: shell !== 'web' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  }
}

export const runtimeInfo = detectRuntime()
