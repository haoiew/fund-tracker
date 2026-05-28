<template>
  <div class="about-view">
    <!-- 简介区域 -->
    <div class="about-intro">
      <h2 class="intro-title">基金跟踪器</h2>
      <p class="intro-desc">
        一款专业的基金投资管理工具，帮助您实时追踪基金动态、管理投资组合、分析收益表现。
        支持基金筛选、对比分析、持仓管理等功能，让投资更简单、更高效。
      </p>
    </div>

    <!-- 功能特性 - 简洁列表 -->
    <div class="features-section">
      <h3 class="section-title">功能特性</h3>
      <div class="features-list">
        <div class="feature-item">
          <el-icon class="feature-icon" :size="20" color="#3b82f6"><DataLine /></el-icon>
          <span>实时估值追踪</span>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon" :size="20" color="#10b981"><Wallet /></el-icon>
          <span>持仓收益管理</span>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon" :size="20" color="#f59e0b"><Filter /></el-icon>
          <span>智能基金筛选</span>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon" :size="20" color="#8b5cf6"><TrendCharts /></el-icon>
          <span>多基金对比</span>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon" :size="20" color="#ec4899"><Download /></el-icon>
          <span>数据导出</span>
        </div>
        <div class="feature-item">
          <el-icon class="feature-icon" :size="20" color="#06b6d4"><Moon /></el-icon>
          <span>深色模式</span>
        </div>
      </div>
    </div>

    <!-- 技术栈 - 简化展示 -->
    <div class="tech-section">
      <h3 class="section-title">技术栈</h3>
      <div class="tech-list">
        <span class="tech-item">Vue 3</span>
        <span class="tech-item">TypeScript</span>
        <span class="tech-item">FastAPI</span>
        <span class="tech-item">Python</span>
        <span class="tech-item">SQLite</span>
      </div>
    </div>

    <!-- 版权信息 -->
    <div class="copyright">
      <p>© 2024 Fund Tracker · 智能基金投资助手</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'AboutView'
})

import {
  DataLine,
  Wallet,
  Filter,
  TrendCharts,
  Download,
  Moon
} from '@element-plus/icons-vue'
</script>

<style scoped lang="scss">
.about-view {
  padding: 40px 32px;
  max-width: 800px;
  margin: 0 auto;
}

.about-intro {
  text-align: center;
  margin-bottom: 48px;

  .intro-title {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
  }

  .intro-desc {
    font-size: 15px;
    color: var(--text-secondary);
    line-height: 1.8;
    max-width: 600px;
    margin: 0 auto;
  }
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.features-section {
  margin-bottom: 40px;
}

.features-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;

  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-base);
  border-radius: var(--radius-base);
  border: 1px solid var(--border-light);
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--primary-color);
    background: var(--bg-hover);
  }

  span {
    font-size: 14px;
    color: var(--text-primary);
  }
}

.tech-section {
  margin-bottom: 48px;
}

.tech-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tech-item {
  padding: 8px 16px;
  background: var(--bg-page);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  font-size: 13px;
  color: var(--text-secondary);
}

.copyright {
  text-align: center;
  padding-top: 32px;
  border-top: 1px solid var(--border-light);

  p {
    font-size: 13px;
    color: var(--text-placeholder);
  }
}
</style>
