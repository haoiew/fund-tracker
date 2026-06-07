<template>
  <div class="not-found-view">
    <section class="error-panel surface-panel">
      <div class="error-code">404</div>
      <div class="error-copy">
        <span class="workbench-eyebrow">Route unavailable</span>
        <h1 class="error-title">{{ $t('error.notFound') }}</h1>
        <p class="error-description">{{ $t('error.notFoundDesc') }}</p>
      </div>
      <div class="error-actions">
        <el-button type="primary" @click="goHome">
          <el-icon><House /></el-icon>
          {{ $t('error.backHome') }}
        </el-button>
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          {{ $t('error.goBack') }}
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'NotFoundView'
})

import { useRouter } from 'vue-router'
import { House, ArrowLeft } from '@element-plus/icons-vue'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped lang="scss">
.not-found-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background: var(--bg-page);
}

.error-panel {
  width: min(720px, 100%);
  padding: 34px;
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 28px;
  align-items: center;
}

.error-code {
  min-height: 150px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-base);
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(20, 184, 166, 0.08)),
    var(--bg-base);
  border: 1px solid var(--border-light);
  color: var(--primary-color);
  font-family: var(--font-mono);
  font-size: 42px;
  font-weight: 800;
}

.error-copy {
  min-width: 0;
}

.error-title {
  margin-top: 12px;
  color: var(--text-primary);
  font-size: 28px;
  font-weight: 800;
  line-height: 1.15;
}

.error-description {
  margin-top: 10px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.error-actions {
  grid-column: 2;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;

  .el-button {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

@media (max-width: 720px) {
  .error-panel {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .error-actions {
    grid-column: auto;
  }

  .error-code {
    min-height: 110px;
  }
}
</style>
