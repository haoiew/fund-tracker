// API请求封装
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1'

// 默认超时时间（毫秒）
const DEFAULT_TIMEOUT = 30000

// 请求拦截器配置
const requestInterceptors = []
const responseInterceptors = []

/**
 * 添加请求拦截器
 * @param {Function} onFulfilled - 成功时的处理函数
 * @param {Function} onRejected - 失败时的处理函数
 */
export const addRequestInterceptor = (onFulfilled, onRejected) => {
  requestInterceptors.push({ onFulfilled, onRejected })
}

/**
 * 添加响应拦截器
 * @param {Function} onFulfilled - 成功时的处理函数
 * @param {Function} onRejected - 失败时的处理函数
 */
export const addResponseInterceptor = (onFulfilled, onRejected) => {
  responseInterceptors.push({ onFulfilled, onRejected })
}

/**
 * 创建带超时的fetch请求
 * @param {string} url - 请求URL
 * @param {Object} options - fetch选项
 * @param {number} timeout - 超时时间（毫秒）
 * @returns {Promise}
 */
const fetchWithTimeout = (url, options = {}, timeout = DEFAULT_TIMEOUT) => {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('请求超时')), timeout)
    )
  ])
}

/**
 * 应用请求拦截器
 * @param {Object} options - 请求选项
 * @returns {Object} 处理后的选项
 */
const applyRequestInterceptors = (options) => {
  let processedOptions = { ...options }
  for (const interceptor of requestInterceptors) {
    if (interceptor.onFulfilled) {
      processedOptions = interceptor.onFulfilled(processedOptions)
    }
  }
  return processedOptions
}

/**
 * 应用响应拦截器
 * @param {Response} response - fetch响应对象
 * @returns {Response} 处理后的响应
 */
const applyResponseInterceptors = async (response) => {
  let processedResponse = response
  for (const interceptor of responseInterceptors) {
    if (interceptor.onFulfilled) {
      processedResponse = await interceptor.onFulfilled(processedResponse)
    }
  }
  return processedResponse
}

/**
 * 统一错误处理
 * @param {Error} error - 错误对象
 * @returns {Object} 标准化的错误响应
 */
const handleError = (error) => {
  console.error('请求失败:', error)

  let errorMessage = '网络请求失败'
  let errorCode = -1

  if (error.message === '请求超时') {
    errorMessage = '请求超时，请稍后重试'
    errorCode = 408
  } else if (error.message.includes('Failed to fetch')) {
    errorMessage = '网络连接失败，请检查网络'
    errorCode = 0
  } else if (error.name === 'TypeError') {
    errorMessage = '请求格式错误'
    errorCode = 400
  }

  return {
    code: errorCode,
    message: errorMessage,
    data: null,
    success: false
  }
}

/**
 * 发送HTTP请求
 * @param {Object} options - 请求配置
 * @param {string} options.url - 请求路径（不包含BASE_URL）
 * @param {string} options.method - HTTP方法，默认GET
 * @param {Object} options.data - 请求体数据
 * @param {Object} options.headers - 自定义请求头
 * @param {number} options.timeout - 超时时间（毫秒）
 * @returns {Promise<Object>} 响应数据
 */
export const request = async (options) => {
  const {
    url,
    method = 'GET',
    data,
    headers = {},
    timeout = DEFAULT_TIMEOUT
  } = options

  // 构建请求配置
  let requestOptions = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    }
  }

  // 添加请求体（非GET请求）
  if (data && method !== 'GET') {
    requestOptions.body = JSON.stringify(data)
  }

  // 应用请求拦截器
  requestOptions = applyRequestInterceptors(requestOptions)

  try {
    const fullUrl = `${BASE_URL}${url}`
    const response = await fetchWithTimeout(fullUrl, requestOptions, timeout)

    // 应用响应拦截器
    const processedResponse = await applyResponseInterceptors(response)

    // 处理HTTP错误状态
    if (!processedResponse.ok) {
      const errorData = await processedResponse.json().catch(() => ({}))
      throw new Error(
        errorData.message || `HTTP ${processedResponse.status}: ${processedResponse.statusText}`
      )
    }

    // 解析响应数据
    const result = await processedResponse.json()

    // 处理业务逻辑错误
    if (result.code !== 200 && result.code !== undefined) {
      throw new Error(result.message || '请求失败')
    }

    return result
  } catch (error) {
    return handleError(error)
  }
}

/**
 * GET请求
 * @param {string} url - 请求路径
 * @param {Object} options - 其他选项
 * @returns {Promise<Object>}
 */
export const get = (url, options = {}) => {
  return request({ ...options, url, method: 'GET' })
}

/**
 * POST请求
 * @param {string} url - 请求路径
 * @param {Object} data - 请求体数据
 * @param {Object} options - 其他选项
 * @returns {Promise<Object>}
 */
export const post = (url, data, options = {}) => {
  return request({ ...options, url, method: 'POST', data })
}

/**
 * PUT请求
 * @param {string} url - 请求路径
 * @param {Object} data - 请求体数据
 * @param {Object} options - 其他选项
 * @returns {Promise<Object>}
 */
export const put = (url, data, options = {}) => {
  return request({ ...options, url, method: 'PUT', data })
}

/**
 * DELETE请求
 * @param {string} url - 请求路径
 * @param {Object} options - 其他选项
 * @returns {Promise<Object>}
 */
export const del = (url, options = {}) => {
  return request({ ...options, url, method: 'DELETE' })
}

// 默认导出
export default request
