<template>
  <article class="fund-record-card">
    <header class="fund-record-card__header">
      <slot name="selection" />
      <div class="fund-record-card__identity">
        <h3>{{ name }}</h3>
        <div class="fund-record-card__code">
          <span v-if="code">{{ code }}</span>
          <slot name="badges" />
        </div>
      </div>
    </header>

    <dl class="fund-record-card__metrics">
      <div v-for="metric in metrics" :key="metric.key" :class="{ 'is-wide': metric.wide }">
        <dt>{{ metric.label }}</dt>
        <dd :class="metric.className === 'text-muted-change' ? 'text-muted' : metric.className">{{ metric.value }}</dd>
      </div>
    </dl>

    <div v-if="$slots.meta" class="fund-record-card__meta"><slot name="meta" /></div>
    <footer v-if="$slots.actions" class="fund-record-card__actions"><slot name="actions" /></footer>
    <div v-if="$slots.default" class="fund-record-card__detail"><slot /></div>
  </article>
</template>

<script setup lang="ts">
export interface FundRecordMetric {
  key: string
  label: string
  value: string
  className?: string
  wide?: boolean
}

defineProps<{
  name: string
  code?: string
  metrics: FundRecordMetric[]
}>()
</script>

<style scoped lang="scss">
.fund-record-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-base);
  background: var(--bg-card);
}

.fund-record-card__header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}

.fund-record-card__identity {
  min-width: 0;
  flex: 1;

  h3 {
    font-size: 14px;
    font-weight: 700;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
}

.fund-record-card__code {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 12px;

  > span {
    font-family: var(--font-mono);
  }
}

.fund-record-card__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;

  > div {
    min-width: 0;
  }

  .is-wide {
    grid-column: 1 / -1;
  }

  dt {
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.4;
  }

  dd {
    margin-top: 2px;
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    line-height: 1.5;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }
}

.fund-record-card__meta {
  margin-top: 10px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.fund-record-card__actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);

  :deep(.el-button) {
    margin: 0;
    min-height: 36px;
  }
}

.fund-record-card__detail {
  min-width: 0;
  margin-top: 10px;
}

@media (min-width: 600px) {
  .fund-record-card__metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
