import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import electron from 'vite-plugin-electron'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const isElectron = mode === 'electron'
  const isNativeShell = mode === 'electron' || mode === 'tauri'

  return {
    plugins: [
      vue(),
      isElectron && electron({
        entry: 'electron/main.js',
        onstart: (options) => {
          if (process.env.VITE_ELECTRON_STARTUP === '0') return
          options.startup()
        },
        vite: {
          build: {
            sourcemap: true,
            minify: false,
            outDir: 'dist-electron',
            rollupOptions: {
              external: ['electron']
            }
          }
        }
      })
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    css: {
      preprocessorOptions: {
        scss: {}
      }
    },
    server: {
      host: '127.0.0.1',
      port: 3000,
      proxy: {
        '^/api/.*': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
          ws: true,
          rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
          configure: (proxy, _options) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            proxy.on('error', (err: Error, _req: any, _res: any) => {
              console.log('proxy error', err)
            })
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            proxy.on('proxyReq', (proxyReq: any, req: any, _res: any) => {
              console.log('proxy request:', req.method, req.url, '->', proxyReq.path)
            })
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            proxy.on('proxyRes', (proxyRes: any, req: any, _res: any) => {
              console.log('proxy response:', proxyRes.statusCode, req.url)
            })
          }
        }
      }
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      target: isNativeShell ? 'es2021' : 'baseline-widely-available',
      sourcemap: 'hidden',
      rollupOptions: {
        output: {
          manualChunks: {
            'element-plus': ['element-plus'],
            'echarts': ['echarts', 'vue-echarts']
          }
        }
      }
    }
  }
})
