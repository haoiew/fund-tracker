<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑筛选条件' : '添加筛选条件'"
    width="420px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form :model="form" label-width="100px" label-position="right">
      <el-form-item label="筛选类型">
        <el-select v-model="form.type" style="width: 100%" @change="handleTypeChange">
          <el-option label="连续涨跌" value="consecutive" />
          <el-option label="N天内累计" value="period" />
        </el-select>
      </el-form-item>

      <el-form-item label="方向">
        <el-radio-group v-model="form.direction">
          <el-radio-button value="up">
            <el-icon><ArrowUp /></el-icon>
            上涨
          </el-radio-button>
          <el-radio-button value="down">
            <el-icon><ArrowDown /></el-icon>
            下跌
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <template v-if="form.type === 'consecutive'">
        <el-form-item label="最少天数">
          <el-input-number
            v-model="form.minDays"
            :min="1"
            :max="30"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="form.direction === 'up' ? '累计涨幅(%)' : '累计跌幅(%)'">
          <el-input-number
            v-model="form.minPct"
            :min="0.1"
            :max="50"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item label="统计天数">
          <el-input-number
            v-model="form.periodDays"
            :min="1"
            :max="90"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="form.direction === 'up' ? '最小涨幅(%)' : '最小跌幅(%)'">
          <el-input-number
            v-model="form.minPct"
            :min="0.1"
            :max="50"
            :step="0.1"
            :precision="1"
            style="width: 100%"
          />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import type { ScreenCondition, ScreenType } from '@/api/fund'

interface Props {
  modelValue: boolean
  editCondition?: ScreenCondition | null
}

const props = withDefaults(defineProps<Props>(), {
  editCondition: null
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm', condition: Omit<ScreenCondition, 'id'>): void
}>()

const visible = ref(false)
const isEdit = ref(false)

const defaultForm = () => ({
  type: 'consecutive' as ScreenType,
  direction: 'up' as 'up' | 'down',
  minDays: 2,
  minPct: 3,
  periodDays: 7
})

const form = reactive(defaultForm())

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.editCondition) {
    isEdit.value = true
    form.type = props.editCondition.type
    form.direction = props.editCondition.direction
    form.minDays = props.editCondition.minDays ?? 2
    form.minPct = props.editCondition.minPct
    form.periodDays = props.editCondition.periodDays ?? 7
  } else if (val) {
    isEdit.value = false
    Object.assign(form, defaultForm())
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const handleTypeChange = () => {
  if (form.type === 'consecutive') {
    form.minDays = 2
    form.minPct = 3
  } else {
    form.periodDays = 7
    form.minPct = 3
  }
}

const handleClose = () => {
  visible.value = false
}

const handleConfirm = () => {
  const condition: Omit<ScreenCondition, 'id'> = {
    type: form.type,
    direction: form.direction,
    minPct: form.minPct / 100
  }

  if (form.type === 'consecutive') {
    condition.minDays = form.minDays
  } else {
    condition.periodDays = form.periodDays
  }

  emit('confirm', condition)
  visible.value = false
}
</script>
