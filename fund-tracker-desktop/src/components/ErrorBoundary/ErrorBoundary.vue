<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <div class="error-icon">
        <el-icon size="64" color="var(--danger-color)"><CircleClose /></el-icon>
      </div>
      <h2 class="error-title">{{ $t('error.title') }}</h2>
      <p class="error-message">{{ displayError }}</p>
      <div class="error-actions">
        <el-button type="primary" @click="handleRetry">
          <el-icon><Refresh /></el-icon>
          {{ $t('error.retry') }}
        </el-button>
        <el-button @click="handleReset">
          <el-icon><HomeFilled /></el-icon>
          {{ $t('error.backHome') }}
        </el-button>
      </div>
      <el-collapse v-if="showDetails" class="error-details">
        <el-collapse-item :title="$t('error.details')">
          <pre class="error-stack">{{ errorInfo }}</pre>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, computed, onErrorCaptured, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { CircleClose, Refresh, HomeFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = withDefaults(defineProps<{
  showDetails?: boolean
  fallback?: string
}>(), {
  showDetails: false,
  fallback: '/'
})

const router = useRouter()
const hasError = ref(false)
const errorMessage = ref('')
const errorInfo = ref('')
const errorComponent = ref<unknown>(null)

const displayError = computed(() => {
  if (errorMessage.value) {
    return errorMessage.value
  }
  return 'An unexpected error occurred'
})

// 捕获错误
onErrorCaptured((err, instance, info) => {
  hasError.value = true
  errorMessage.value = err instanceof Error ? err.message : String(err)
  errorInfo.value = info
  errorComponent.value = instance

  // 上报错误（可以接入错误监控服务）
  reportError(err, instance, info)

  return false // 阻止错误继续传播
})

// 上报错误
const reportError = (err: unknown, instance: unknown, info: string) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const componentName = (instance as any)?.$options?.name || 'Unknown'
  console.error('Error captured by boundary:', {
    error: err,
    component: componentName,
    info,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href
  })
}

// 重试
const handleRetry = () => {
  hasError.value = false
  errorMessage.value = ''
  errorInfo.value = ''
  errorComponent.value = null
}

// 返回首页
const handleReset = () => {
  handleRetry()
  router.push(props.fallback)
}

// 监听全局错误
onMounted(() => {
  const handleGlobalError = (event: ErrorEvent) => {
    console.error('Global error:', event.error)
    ElMessage.error('An error occurred, please refresh the page')
  }

  const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    console.error('Unhandled rejection:', event.reason)
    ElMessage.error('An async error occurred')
  }

  window.addEventListener('error', handleGlobalError)
  window.addEventListener('unhandledrejection', handleUnhandledRejection)

  return () => {
    window.removeEventListener('error', handleGlobalError)
    window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  }
})
</script>

<style scoped lang="scss">
.error-boundary {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background: var(--bg-page);

  .error-content {
    max-width: 600px;
    text-align: center;

    .error-icon {
      margin-bottom: 24px;
      animation: shake 0.5s ease-in-out;
    }

    .error-title {
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 12px;
    }

    .error-message {
      font-size: 16px;
      color: var(--text-secondary);
      margin-bottom: 32px;
      line-height: 1.6;
    }

    .error-actions {
      display: flex;
      gap: 16px;
      justify-content: center;
      margin-bottom: 32px;

      .el-button {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }

    .error-details {
      text-align: left;

      .error-stack {
        background: var(--bg-base);
        padding: 16px;
        border-radius: var(--radius-base);
        font-family: 'Courier New', monospace;
        font-size: 12px;
        color: var(--text-secondary);
        overflow-x: auto;
        white-space: pre-wrap;
        word-break: break-all;
      }
    }
  }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}
</style>
