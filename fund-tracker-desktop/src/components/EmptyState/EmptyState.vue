<template>
  <div class="empty-state">
    <div class="empty-icon">
      <el-icon :size="64" color="var(--text-placeholder)">
        <component :is="icon" />
      </el-icon>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FolderOpened, Search, Document, Warning } from '@element-plus/icons-vue'

type EmptyIconType = 'folder' | 'search' | 'document' | 'warning'

const props = withDefaults(defineProps<{
  icon?: EmptyIconType
  title?: string
  description?: string
}>(), {
  icon: 'folder',
  title: '暂无数据',
  description: ''
})

const iconMap = {
  folder: FolderOpened,
  search: Search,
  document: Document,
  warning: Warning
}

const icon = computed(() => iconMap[props.icon])
</script>

<style scoped lang="scss">
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;

  .empty-icon {
    margin-bottom: 24px;
    animation: float 3s ease-in-out infinite;
  }

  .empty-title {
    font-size: 18px;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 8px;
  }

  .empty-description {
    font-size: 14px;
    color: var(--text-secondary);
    margin-bottom: 24px;
    max-width: 400px;
  }

  .empty-action {
    margin-top: 8px;
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
</style>
