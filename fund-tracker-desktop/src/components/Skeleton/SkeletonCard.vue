<template>
  <div class="skeleton-card" :style="{ height: props.height + 'px' }">
    <div class="skeleton-header" v-if="props.showHeader">
      <div class="skeleton-title"></div>
      <div class="skeleton-action"></div>
    </div>
    <div class="skeleton-content">
      <div
        v-for="i in props.rows"
        :key="i"
        class="skeleton-row"
        :style="{ width: getRowWidth(i) }"
      ></div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  rows?: number
  height?: number
  showHeader?: boolean
}>(), {
  rows: 4,
  height: 200,
  showHeader: true
})

const getRowWidth = (index: number) => {
  // 随机宽度，让骨架屏看起来更自然
  const widths = ['100%', '95%', '90%', '85%', '80%', '75%']
  return widths[(index - 1) % widths.length]
}
</script>

<style scoped lang="scss">
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-base);

  .skeleton-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .skeleton-title {
      width: 120px;
      height: 20px;
      background: linear-gradient(90deg, var(--bg-hover) 25%, var(--bg-page) 50%, var(--bg-hover) 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: var(--radius-sm);
    }

    .skeleton-action {
      width: 80px;
      height: 32px;
      background: linear-gradient(90deg, var(--bg-hover) 25%, var(--bg-page) 50%, var(--bg-hover) 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: var(--radius-base);
    }
  }

  .skeleton-content {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .skeleton-row {
      height: 16px;
      background: linear-gradient(90deg, var(--bg-hover) 25%, var(--bg-page) 50%, var(--bg-hover) 75%);
      background-size: 200% 100%;
      animation: skeleton-loading 1.5s infinite;
      border-radius: var(--radius-sm);
    }
  }
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
