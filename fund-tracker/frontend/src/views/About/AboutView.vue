<template>
  <div class="about-view workbench-page">
    <section class="page-toolbar">
      <div class="page-toolbar__main">
        <span class="page-toolbar__icon">
          <el-icon><DataAnalysis /></el-icon>
        </span>
        <div class="page-toolbar__copy">
          <h2 class="page-toolbar__title">基金跟踪器</h2>
          <p class="page-toolbar__meta">轻量跨端金融工作台 · 实时估值 · 筛选对比 · 持仓收益管理</p>
        </div>
      </div>
    </section>

    <section class="architecture-panel surface-panel">
      <div class="architecture-copy">
        <span class="architecture-kicker">Architecture</span>
        <h3>轻量跨端壳，本地优先的数据链路</h3>
        <p>前端保持纯 Web 能力与低耦合运行时，后端负责数据源编排、缓存与持仓计算，为 Tauri 桌面和未来 Android 容器保留迁移空间。</p>
      </div>

      <div class="architecture-flow" aria-label="技术架构">
        <div
          v-for="(node, index) in architectureNodes"
          :key="node.title"
          class="architecture-node"
        >
          <span class="architecture-icon">
            <el-icon><component :is="node.icon" /></el-icon>
          </span>
          <div>
            <strong>{{ node.title }}</strong>
            <small>{{ node.description }}</small>
          </div>
          <span v-if="index < architectureNodes.length - 1" class="architecture-connector"></span>
        </div>
      </div>
    </section>

    <section class="about-panel workbench-panel surface-panel">
      <div class="workbench-panel__header">
        <div>
          <div class="workbench-panel__title">核心能力</div>
          <div class="workbench-panel__meta">围绕基金跟踪的一体化工作流</div>
        </div>
      </div>
      <div class="features-list">
        <div v-for="feature in features" :key="feature.title" class="feature-item">
          <span class="feature-icon">
            <el-icon :size="20"><component :is="feature.icon" /></el-icon>
          </span>
          <div>
            <span>{{ feature.title }}</span>
            <small>{{ feature.description }}</small>
          </div>
        </div>
      </div>
    </section>

    <section class="about-panel workbench-panel surface-panel">
      <div class="workbench-panel__header">
        <div>
          <div class="workbench-panel__title">技术栈</div>
          <div class="workbench-panel__meta">Web 优先，Tauri-ready，保留安卓跨端潜力</div>
        </div>
      </div>
      <div class="tech-grid">
        <div v-for="item in techStack" :key="item.name" class="tech-item">
          <strong>{{ item.name }}</strong>
          <span>{{ item.role }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'AboutView'
})

import {
  Connection,
  Cpu,
  DataAnalysis,
  DataLine,
  Download,
  Files,
  Filter,
  Monitor,
  Moon,
  TrendCharts,
  Wallet
} from '@element-plus/icons-vue'

const architectureNodes = [
  {
    title: 'Vue Web UI',
    description: '高密度工作台与纯 Web 交互',
    icon: Monitor
  },
  {
    title: 'API Client',
    description: '统一请求、错误和响应解包',
    icon: Connection
  },
  {
    title: 'FastAPI Service',
    description: '筛选、对比、持仓业务层',
    icon: Cpu
  },
  {
    title: 'Data Sources',
    description: '多源行情与自动 fallback',
    icon: DataLine
  },
  {
    title: 'SQLite / Cache',
    description: '本地持久化与内存缓存',
    icon: Files
  }
]

const features = [
  { title: '实时估值追踪', description: '关注列表、状态与数据源可见', icon: DataLine },
  { title: '持仓收益管理', description: '成本、份额、市值和收益集中维护', icon: Wallet },
  { title: '基金筛选', description: '连续涨跌与区间累计组合查询', icon: Filter },
  { title: '多基金对比', description: '走势、基准和多周期收益矩阵', icon: TrendCharts },
  { title: '数据导出', description: '关注数据可快速落地 CSV', icon: Download },
  { title: '主题系统', description: '浅色、深色和系统自动模式', icon: Moon }
]

const techStack = [
  { name: 'Vue 3 + TypeScript', role: '前端交互与类型约束' },
  { name: 'Element Plus', role: '表单、表格和桌面控件' },
  { name: 'ECharts', role: '基金走势与收益可视化' },
  { name: 'FastAPI + SQLAlchemy', role: '后端 API 与业务模型' },
  { name: 'SQLite + LRU Cache', role: '本地数据和轻量缓存' },
  { name: 'Tauri-ready Shell', role: '轻量桌面与安卓跨端潜力' }
]
</script>

<style scoped lang="scss">
.about-view {
  max-width: 1180px;
  width: 100%;
  margin-inline: auto;
}

.about-panel {
  padding: 16px;
}

.architecture-panel {
  display: grid;
  grid-template-columns: minmax(260px, 0.42fr) minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
}

.architecture-copy {
  padding: 8px 6px;

  h3 {
    margin: 8px 0 0;
    color: var(--text-primary);
    font-size: 22px;
    font-weight: 850;
    line-height: 1.2;
  }

  p {
    margin-top: 10px;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.8;
  }
}

.architecture-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: var(--radius-full);
  background: var(--icon-surface);
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 800;
}

.architecture-flow {
  display: grid;
  grid-template-columns: repeat(5, minmax(168px, 1fr));
  align-items: stretch;
  gap: 10px;
  min-width: 0;
  overflow-x: auto;
  padding-bottom: 2px;
}

.architecture-node {
  position: relative;
  min-width: 168px;
  padding: 14px 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  background: var(--bg-card);
  box-shadow: var(--shadow-light);

  strong {
    display: block;
    margin-top: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-primary);
    font-size: 12px;
    font-weight: 850;
    line-height: 1.25;
  }

  small {
    display: block;
    margin-top: 6px;
    word-break: keep-all;
    overflow-wrap: normal;
    white-space: normal;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.5;
  }
}

.architecture-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-base);
  background: var(--icon-surface);
  color: var(--primary-color);
}

.architecture-connector {
  position: absolute;
  top: 32px;
  right: -11px;
  z-index: 1;
  width: 12px;
  height: 1px;
  background: var(--border-base);
}

.features-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 82px;
  padding: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  transition: transform var(--transition-fast), border-color var(--transition-fast), background-color var(--transition-fast);

  &:hover {
    transform: translateY(-1px);
    border-color: rgba(37, 99, 235, 0.24);
    background: var(--bg-hover);
  }

  span {
    white-space: nowrap;
    word-break: keep-all;
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 800;
  }

  small {
    display: block;
    margin-top: 4px;
    word-break: keep-all;
    overflow-wrap: normal;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.5;
  }
}

.feature-icon {
  margin-top: 1px;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(220px, 1fr));
  gap: 12px;
  min-width: 0;
}

.tech-item {
  padding: 14px;
  background: var(--bg-hover);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);

  strong {
    display: block;
    white-space: nowrap;
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 850;
  }

  span {
    display: block;
    margin-top: 6px;
    word-break: keep-all;
    overflow-wrap: normal;
    white-space: nowrap;
    color: var(--text-secondary);
    font-size: 12px;
  }
}

@media (max-width: 1080px) {
  .architecture-panel {
    grid-template-columns: 1fr;
  }

  .architecture-flow {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .architecture-connector {
    display: none;
  }
}

@media (max-width: 720px) {
  .architecture-flow,
  .features-list,
  .tech-grid {
    grid-template-columns: 1fr;
  }
}
</style>
