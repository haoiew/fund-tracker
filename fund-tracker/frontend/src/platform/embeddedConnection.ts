export interface EmbeddedConnection {
  apiBaseUrl: string
  accessToken: string
}

let connection: EmbeddedConnection | undefined

export function setEmbeddedConnection(value: EmbeddedConnection): void {
  // Only accept the private loopback API, never an arbitrary destination for the secret.
  if (!/^http:\/\/127\.0\.0\.1:\d+\/api\/v1$/.test(value.apiBaseUrl) || !value.accessToken) {
    throw new Error('内置数据服务返回了无效的连接信息')
  }
  connection = { ...value }
}

export function getEmbeddedApiBaseUrl(): string | undefined {
  return connection?.apiBaseUrl
}

export function getEmbeddedAccessToken(baseUrl: string, requestUrl = ''): string | undefined {
  if (!connection || baseUrl !== connection.apiBaseUrl) return undefined
  if (/^[a-z][a-z\d+.-]*:/i.test(requestUrl) || requestUrl.startsWith('//')) return undefined
  return connection.accessToken
}
