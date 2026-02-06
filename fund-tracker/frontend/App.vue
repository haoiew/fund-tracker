<template>
  <IndexPage />
</template>

<script setup>
import IndexPage from './src/pages/index/index.vue'
</script>

<style>
/* 全局样式 */
page {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 颜色变量 */
:root {
  --primary-color: #1890ff;
  --success-color: #52c41a;
  --warning-color: #faad14;
  --error-color: #ff4d4f;
  --up-color: #ff4d4f;
  --down-color: #52c41a;
  --text-color: #262626;
  --text-secondary: #8c8c8c;
  --border-color: #d9d9d9;
  --bg-color: #f5f5f5;
}
</style>
