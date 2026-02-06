<template>
  <div class="loading-state" :class="{ 'fullscreen': fullscreen }">
    <div class="loading-content">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
        <div class="spinner-ring"></div>
      </div>
      <p v-if="text" class="loading-text">{{ text }}</p>
      <p v-if="subText" class="loading-subtext">{{ subText }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  text?: string
  subText?: string
  fullscreen?: boolean
}>(), {
  text: '加载中...',
  fullscreen: false
})
</script>

<style scoped lang="scss">
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;

  &.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--bg-page);
    z-index: 9999;
  }

  .loading-content {
    text-align: center;

    .loading-spinner {
      position: relative;
      width: 64px;
      height: 64px;
      margin: 0 auto 24px;

      .spinner-ring {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        border: 3px solid transparent;
        border-top-color: var(--primary-color);
        animation: spin 1s linear infinite;

        &:nth-child(2) {
          width: 80%;
          height: 80%;
          top: 10%;
          left: 10%;
          border-top-color: var(--primary-light);
          animation-duration: 1.5s;
          animation-direction: reverse;
        }

        &:nth-child(3) {
          width: 60%;
          height: 60%;
          top: 20%;
          left: 20%;
          border-top-color: var(--primary-lighter);
          animation-duration: 2s;
        }
      }
    }

    .loading-text {
      font-size: 16px;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .loading-subtext {
      font-size: 14px;
      color: var(--text-secondary);
    }
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
