import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import electron from 'vite-plugin-electron'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const isElectron = mode === 'electron'

  return {
    plugins: [
      vue(),
      isElectron && electron({
        entry: 'electron/main.js',
        onstart: (options) => {
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
      port: 5173,
      proxy: {
        '^/api/.*': {
          target: 'http://localhost:8001',
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
      sourcemap: true,
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
