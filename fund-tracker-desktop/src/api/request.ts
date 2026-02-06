import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'

// API 基础配置 - 从环境变量读取
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1'

// 创建 axios 实例
const service: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // 只在开发环境打印日志
    if (import.meta.env.DEV) {
      console.log('[API Request]', config.method?.toUpperCase(), config.url, config.data)
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
  (error) => {
    console.error('[API Error]', error.message, error.config?.url)
    let message = '网络请求失败'
    
    if (error.response) {
      switch (error.response.status) {
        case 400:
          message = '请求参数错误'
          break
        case 401:
          message = '未授权，请重新登录'
          break
        case 403:
          message = '拒绝访问'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 405:
          message = '请求方法不允许'
          break
        case 500:
          message = '服务器内部错误'
          break
        default:
          message = `请求失败: ${error.response.status}`
      }
    } else if (error.request) {
      message = '网络连接失败，请检查网络'
    } else if (error.code === 'ECONNABORTED') {
      message = '请求超时，请稍后重试'
    }
    
    return Promise.reject(new Error(message))
  }
)

// 封装请求方法
export const request = {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.get(url, config)
  },
  
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return service.post(url, data, config)
  },
  
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return service.put(url, data, config)
  },
  
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.delete(url, config)
  }
}

export default service
