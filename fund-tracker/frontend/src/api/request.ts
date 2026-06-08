import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, AxiosError } from 'axios'
import { resolveApiBaseUrl } from '@/platform/apiConfig'

// 重试配置
const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000, // 基础延迟时间（毫秒）
  retryDelayMultiplier: 2, // 延迟倍数（指数退避）
  retryableStatuses: [408, 429, 500, 502, 503, 504], // 可重试的HTTP状态码
  retryableErrors: ['ECONNABORTED', 'ETIMEDOUT', 'ECONNRESET', 'NETWORK_ERROR']
}

// 请求队列（用于去重）
const pendingRequests = new Map<string, Promise<unknown>>()

interface EnhancedApiError extends Error {
  code: string
  originalError: AxiosError
  isRetryable: boolean
  retryCount: number
}

function redactRequestData(value: unknown): unknown {
  if (!value || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map(redactRequestData)

  const redacted: Record<string, unknown> = {}
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    redacted[key] = /api[_-]?key|authorization|token|secret|password/i.test(key)
      ? '***'
      : redactRequestData(item)
  }
  return redacted
}

function formatServerErrorPayload(payload: unknown): string {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) {
    return payload
      .map(item => formatServerErrorPayload(item))
      .filter(Boolean)
      .join('；')
  }
  if (typeof payload === 'object') {
    const data = payload as Record<string, unknown>
    const direct = data.detail ?? data.message ?? data.error
    if (direct) return formatServerErrorPayload(direct)
    if (typeof data.msg === 'string') return data.msg
    try {
      return JSON.stringify(data)
    } catch {
      return ''
    }
  }
  return String(payload)
}

// 创建 axios 实例
const service: AxiosInstance = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 生成请求唯一标识
 */
function generateRequestKey(config: AxiosRequestConfig): string {
  return `${config.method?.toUpperCase()}_${config.url}_${JSON.stringify(config.params || {})}_${JSON.stringify(config.data || {})}`
}

/**
 * 检查错误是否可重试
 */
function isRetryableError(error: AxiosError): boolean {
  // 检查状态码
  if (error.response?.status && RETRY_CONFIG.retryableStatuses.includes(error.response.status)) {
    return true
  }
  
  // 检查错误代码
  if (error.code && RETRY_CONFIG.retryableErrors.includes(error.code)) {
    return true
  }
  
  // 网络错误
  if (!error.response && error.request) {
    return true
  }
  
  return false
}

/**
 * 延迟函数
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 执行带重试的请求（仅对幂等方法重试）
 */
async function requestWithRetry<T>(
  config: AxiosRequestConfig,
  retryCount: number = 0
): Promise<T> {
  try {
    const result = await service.request<T, T>(config)
    return result
  } catch (error) {
    const axiosError = error as AxiosError
    const method = config.method?.toUpperCase()

    // Only retry idempotent methods (GET, HEAD, OPTIONS)
    const isIdempotent = !method || method === 'GET' || method === 'HEAD' || method === 'OPTIONS'

    if (retryCount < RETRY_CONFIG.maxRetries && isIdempotent && isRetryableError(axiosError)) {
      let delayTime = RETRY_CONFIG.retryDelay * Math.pow(RETRY_CONFIG.retryDelayMultiplier, retryCount)

      // Respect Retry-After header for 429 responses
      if (axiosError.response?.status === 429) {
        const retryAfter = axiosError.response.headers['retry-after']
        if (retryAfter) {
          const retryAfterMs = parseInt(retryAfter, 10) * 1000
          if (!isNaN(retryAfterMs)) {
            delayTime = Math.max(delayTime, retryAfterMs)
          }
        }
      }

      if (import.meta.env.DEV) {
        console.warn(`[API Retry] 请求失败，${delayTime}ms后重试 (${retryCount + 1}/${RETRY_CONFIG.maxRetries}):`, config.url)
      }

      await delay(delayTime)
      return requestWithRetry<T>(config, retryCount + 1)
    }

    throw error
  }
}

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // 让设置页保存的 API 地址在下一次请求即时生效；Web 开发仍默认走 Vite 代理。
    config.baseURL = resolveApiBaseUrl()

    // 只在开发环境打印日志
    if (import.meta.env.DEV) {
      console.log('[API Request]', config.method?.toUpperCase(), config.url, redactRequestData(config.data))
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response
    
    // 只在开发环境打印日志
    if (import.meta.env.DEV) {
      console.log('[API Response]', response.config.url, data)
    }
    
    // 统一处理响应
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code !== 200) {
        console.error('[API Error]', data.code, data.message)
        return Promise.reject(new Error(data.message || '请求失败'))
      }
      return data.data
    }
    
    // 如果直接返回数据（没有包装）
    return data
  },
  (error: AxiosError) => {
    console.error('[API Error]', error.message, error.config?.url)
    let message = '网络请求失败'
    let errorCode = 'UNKNOWN_ERROR'
    
    if (error.response) {
      // 服务器返回错误
      const status = error.response.status
      errorCode = `HTTP_${status}`
      const serverMessage = formatServerErrorPayload(error.response.data)
      
      switch (status) {
        case 400:
          message = '请求参数错误'
          errorCode = 'BAD_REQUEST'
          break
        case 401:
          message = '未授权，请重新登录'
          errorCode = 'UNAUTHORIZED'
          // 可以在这里处理登出逻辑
          break
        case 403:
          message = '拒绝访问'
          errorCode = 'FORBIDDEN'
          break
        case 404:
          message = '请求的资源不存在'
          errorCode = 'NOT_FOUND'
          break
        case 405:
          message = '请求方法不允许'
          errorCode = 'METHOD_NOT_ALLOWED'
          break
        case 408:
          message = '请求超时，请稍后重试'
          errorCode = 'REQUEST_TIMEOUT'
          break
        case 409:
          message = '数据冲突，请刷新后重试'
          errorCode = 'CONFLICT'
          break
        case 422:
          message = '数据验证失败'
          errorCode = 'VALIDATION_ERROR'
          break
        case 429:
          message = '请求过于频繁，请稍后再试'
          errorCode = 'TOO_MANY_REQUESTS'
          break
        case 500:
          message = '服务器内部错误'
          errorCode = 'INTERNAL_SERVER_ERROR'
          break
        case 502:
          message = '网关错误'
          errorCode = 'BAD_GATEWAY'
          break
        case 503:
          message = '服务暂时不可用'
          errorCode = 'SERVICE_UNAVAILABLE'
          break
        case 504:
          message = '网关超时'
          errorCode = 'GATEWAY_TIMEOUT'
          break
        default:
          message = `请求失败: ${status}`
      }
      if (serverMessage) {
        message = serverMessage
      }
    } else if (error.request) {
      // 请求发送但没有收到响应
      errorCode = 'NETWORK_ERROR'
      
      if (error.code === 'ECONNABORTED') {
        message = '请求超时，请检查网络连接'
        errorCode = 'TIMEOUT'
      } else if (error.code === 'ECONNREFUSED') {
        message = '无法连接到服务器，请检查服务是否运行'
        errorCode = 'CONNECTION_REFUSED'
      } else if (error.code === 'ENETUNREACH') {
        message = '网络不可达，请检查网络连接'
        errorCode = 'NETWORK_UNREACHABLE'
      } else {
        message = '网络连接失败，请检查网络'
      }
    } else {
      // 请求配置错误
      errorCode = 'CONFIG_ERROR'
      message = `请求配置错误: ${error.message}`
    }
    
    // 创建增强的错误对象
    const enhancedError: EnhancedApiError = Object.assign(new Error(message), {
      code: errorCode,
      originalError: error,
      isRetryable: isRetryableError(error),
      retryCount: RETRY_CONFIG.maxRetries
    })
    
    return Promise.reject(enhancedError)
  }
)

// 封装请求方法
export const request = {
  /**
   * GET 请求（带自动重试和去重）
   */
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const requestKey = generateRequestKey({ ...config, method: 'GET', url })
    
    // 检查是否有相同请求正在进行
    if (pendingRequests.has(requestKey)) {
      console.log('[API Deduplication] 使用进行中的请求:', url)
      return pendingRequests.get(requestKey) as Promise<T>
    }
    
    const requestPromise = requestWithRetry<T>({ ...config, method: 'GET', url })
      .finally(() => {
        // 请求完成后从队列移除
        pendingRequests.delete(requestKey)
      })
    
    pendingRequests.set(requestKey, requestPromise)
    return requestPromise
  },
  
  /**
   * POST 请求（带自动重试）
   */
  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return service.request<T, T>({ ...config, method: 'POST', url, data }).then(res => res as T)
  },

  /**
   * PUT 请求（不重试，非幂等）
   */
  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return service.request<T, T>({ ...config, method: 'PUT', url, data }).then(res => res as T)
  },

  /**
   * DELETE 请求（不重试，非幂等）
   */
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.request<T, T>({ ...config, method: 'DELETE', url }).then(res => res as T)
  },

  /**
   * 手动重试失败的请求
   */
  async retry<T>(failedRequest: AxiosRequestConfig): Promise<T> {
    return requestWithRetry<T>(failedRequest, 0)
  }
}

export default service
