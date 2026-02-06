/**
 * 前端缓存工具类
 * 使用 LocalStorage 实现数据缓存，减少 API 请求
 */

// 缓存配置
const CACHE_CONFIG = {
  REALTIME_TTL: 60 * 1000,      // 实时数据缓存 60 秒
  HISTORY_TTL: 5 * 60 * 1000,   // 历史数据缓存 5 分钟
  FUND_LIST_TTL: 60 * 60 * 1000,  // 基金列表缓存 1 小时
  SEARCH_TTL: 30 * 60 * 1000,   // 搜索结果缓存 30 分钟
  PREFIX: 'fund_tracker_cache_'
}

// 缓存统计
interface CacheStats {
  hits: number
  misses: number
  hitRate: number
}

class LocalStorageCache {
  private stats: CacheStats = {
    hits: 0,
    misses: 0,
    hitRate: 0
  }

  constructor() {
    this.loadStats()
  }

  private getCacheKey(key: string): string {
    return `${CACHE_CONFIG.PREFIX}${key}`
  }

  private isExpired(timestamp: number): boolean {
    return Date.now() > timestamp
  }

  private updateStats(hit: boolean): void {
    if (hit) {
      this.stats.hits++
    } else {
      this.stats.misses++
    }
    const total = this.stats.hits + this.stats.misses
    this.stats.hitRate = total > 0 ? (this.stats.hits / total * 100) : 0
    this.saveStats()
  }

  private saveStats(): void {
    try {
      localStorage.setItem(`${CACHE_CONFIG.PREFIX}stats`, JSON.stringify(this.stats))
    } catch (e) {
      console.warn('保存缓存统计失败:', e)
    }
  }

  private loadStats(): void {
    try {
      const stats = localStorage.getItem(`${CACHE_CONFIG.PREFIX}stats`)
      if (stats) {
        this.stats = JSON.parse(stats)
      }
    } catch (e) {
      console.warn('加载缓存统计失败:', e)
    }
  }

  get<T>(key: string): T | null {
    try {
      const cacheKey = this.getCacheKey(key)
      const item = localStorage.getItem(cacheKey)

      if (!item) {
        this.updateStats(false)
        return null
      }

      const cached = JSON.parse(item) as { data: T; timestamp: number }

      if (this.isExpired(cached.timestamp)) {
        this.remove(key)
        this.updateStats(false)
        return null
      }

      this.updateStats(true)
      return cached.data
    } catch (e) {
      console.warn('读取缓存失败:', e)
      this.updateStats(false)
      return null
    }
  }

  set<T>(key: string, data: T, ttl: number = CACHE_CONFIG.REALTIME_TTL): void {
    try {
      const cacheKey = this.getCacheKey(key)
      const item = {
        data,
        timestamp: Date.now() + ttl
      }
      localStorage.setItem(cacheKey, JSON.stringify(item))
    } catch (e) {
      console.warn('写入缓存失败:', e)
    }
  }

  remove(key: string): void {
    try {
      const cacheKey = this.getCacheKey(key)
      localStorage.removeItem(cacheKey)
    } catch (e) {
      console.warn('删除缓存失败:', e)
    }
  }

  clear(): void {
    try {
      const keys = Object.keys(localStorage)
      keys.forEach(key => {
        if (key.startsWith(CACHE_CONFIG.PREFIX)) {
          localStorage.removeItem(key)
        }
      })

      // 重置统计
      this.stats = {
        hits: 0,
        misses: 0,
        hitRate: 0
      }
      this.saveStats()
    } catch (e) {
      console.warn('清空缓存失败:', e)
    }
  }

  getStats(): CacheStats {
    return { ...this.stats }
  }

  clearExpired(): void {
    try {
      const keys = Object.keys(localStorage)
      let clearedCount = 0

      keys.forEach(key => {
        if (key.startsWith(CACHE_CONFIG.PREFIX)) {
          try {
            const item = JSON.parse(localStorage.getItem(key) || '{}')
            if (item.timestamp && this.isExpired(item.timestamp)) {
              localStorage.removeItem(key)
              clearedCount++
            }
          } catch {
            // 忽略解析错误
          }
        }
      })

      if (clearedCount > 0) {
        console.log(`清理了 ${clearedCount} 个过期缓存项`)
      }
    } catch (e) {
      console.warn('清理过期缓存失败:', e)
    }
  }
}

export const cache = new LocalStorageCache()
