import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          whitespace: 'preserve',
        }
      }
    }),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    port: 5173,
    hmr: {
      overlay: true
    },
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        timeout: 60000,
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('代理错误:', err);
          });
        }
      },
      '/api/sandbox': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        // 可能需要调整路径重写规则
      }
    }
  },
  build: {
    minify: process.env.NODE_ENV === 'production' ? 'esbuild' : false,
    sourcemap: true,
  },
  css: {
    devSourcemap: true,
  }
})
