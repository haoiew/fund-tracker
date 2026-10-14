import { invoke } from '@tauri-apps/api/core'
import { setEmbeddedConnection, type EmbeddedConnection } from './embeddedConnection'

export async function startEmbeddedBackend(): Promise<void> {
  const connection = await invoke<EmbeddedConnection>('plugin:fund-backend|start_backend')
  setEmbeddedConnection(connection)
}

export async function saveAndroidFile(filename: string, mimeType: string, content: string): Promise<boolean> {
  const result = await invoke<{ saved: boolean }>('plugin:fund-backend|save_file', {
    file: { filename, mimeType, content },
  })
  return result.saved
}
