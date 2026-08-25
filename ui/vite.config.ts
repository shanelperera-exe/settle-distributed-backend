import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

const dockerLogsPlugin = () => ({
  name: 'docker-logs-plugin',
  configureServer(server: any) {
    server.middlewares.use(async (req: any, res: any, next: any) => {
      if (req.url?.startsWith('/api/dev/logs/')) {
        const containerName = req.url.split('/').pop()
        try {
          const { stdout, stderr } = await execAsync(`docker logs --tail 100 ${containerName}`)
          const logs = (stdout + stderr).split('\n').filter(Boolean)
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ logs }))
        } catch (e: any) {
          res.statusCode = 500
          res.end(JSON.stringify({ error: e.message }))
        }
        return
      }
      next()
    })
  }
})

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react(), dockerLogsPlugin()],
    server: {
      proxy: {
        '/api': {
          target: env.API_TARGET_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/prometheus': {
          target: env.PROMETHEUS_TARGET_URL || 'http://localhost:9090',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/prometheus/, '')
        },
        '/loki': {
          target: env.LOKI_TARGET_URL || 'http://localhost:3100',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/loki/, '')
        }
      }
    }
  }
})
