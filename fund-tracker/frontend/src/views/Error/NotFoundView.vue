<template>
  <div class="not-found-view">
    <div class="error-content">
      <div class="error-illustration">
        <div class="number">4</div>
        <div class="planet">
          <div class="planet-ring"></div>
          <div class="planet-body"></div>
        </div>
        <div class="number">4</div>
      </div>
      <h1 class="error-title">{{ $t('error.notFound') }}</h1>
      <p class="error-description">{{ $t('error.notFoundDesc') }}</p>
      <div class="error-actions">
        <el-button type="primary" size="large" @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          {{ $t('error.backHome') }}
        </el-button>
        <el-button size="large" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          {{ $t('error.goBack') }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { HomeFilled, ArrowLeft } from '@element-plus/icons-vue'

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
  padding: 40px 20px;
  background: var(--bg-page);

  .error-content {
    text-align: center;
    max-width: 600px;

    .error-illustration {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      margin-bottom: 40px;

      .number {
        font-size: 120px;
        font-weight: 700;
        color: var(--primary-color);
        line-height: 1;
        animation: float 3s ease-in-out infinite;

        &:first-child {
          animation-delay: 0s;
        }

        &:last-child {
          animation-delay: 0.5s;
        }
      }

      .planet {
        position: relative;
        width: 100px;
        height: 100px;
        animation: float 3s ease-in-out infinite;
        animation-delay: 0.25s;

        .planet-body {
          width: 80px;
          height: 80px;
          background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
          border-radius: 50%;
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          box-shadow: 0 0 40px rgba(59, 130, 246, 0.3);
        }

        .planet-ring {
          width: 120px;
          height: 30px;
          border: 3px solid var(--primary-lighter);
          border-radius: 50%;
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%) rotate(-20deg);
        }
      }
    }

    .error-title {
      font-size: 32px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 16px;
    }

    .error-description {
      font-size: 16px;
      color: var(--text-secondary);
      margin-bottom: 32px;
      line-height: 1.6;
    }

    .error-actions {
      display: flex;
      gap: 16px;
      justify-content: center;

      .el-button {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-15px);
  }
}
</style>
