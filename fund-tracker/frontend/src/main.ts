import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import VueECharts from 'vue-echarts'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { runtimeInfo } from './platform/runtime'

// 样式
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles/variables.scss'
import './styles/global.scss'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册 ECharts 组件
app.component('v-chart', VueECharts)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.use(i18n)

async function bootstrap(): Promise<void> {
  if (runtimeInfo.isAndroidShell) {
    const root = document.getElementById('app')!
    const status = document.createElement('div')
    status.className = 'native-startup'
    status.textContent = '正在打开基金跟踪器…首次启动需要解压本地组件，请稍候。'
    root.replaceChildren(status)
    try {
      const { startEmbeddedBackend } = await import('./platform/android')
      await startEmbeddedBackend()
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : String(error)
      const retry = document.createElement('button')
      retry.textContent = '重新打开'
      retry.onclick = () => window.location.reload()
      status.appendChild(retry)
      return
    }
  }
  app.mount('#app')
}

void bootstrap()
