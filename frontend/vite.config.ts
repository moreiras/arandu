import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// Versão do sistema: arquivo VERSION na raiz do repositório (./VERSION no build em Docker).
function appVersion(): string {
  for (const p of ['./VERSION', '../VERSION']) {
    try {
      const v = readFileSync(p, 'utf8').trim()
      if (v) return v
    } catch {
      /* tenta o próximo */
    }
  }
  return 'dev'
}

// Identidade do site: vem do .env na compilação (Dockerfile.frontend repassa os SITE_* como VITE_SITE_*).
// Padrões iguais aos de core/site.py e src/lib/site.ts. Definidos aqui para o index.html poder usar %VITE_SITE_TITULO% etc.
const PADROES_SITE: Record<string, string> = {
  VITE_SITE_NOME: 'Arandurapé',
  VITE_SITE_NOME_EXTENSO: 'Mapa da Internet brasileira',
  VITE_SITE_URL: 'http://localhost',
}
for (const [k, v] of Object.entries(PADROES_SITE)) if (!process.env[k]?.trim()) process.env[k] = v
process.env.VITE_SITE_TITULO = `${process.env.VITE_SITE_NOME} — ${process.env.VITE_SITE_NOME_EXTENSO}`

// Componentes e utilitários pequenos usados por muitas páginas (Dica, ComoLer, VerDados, CitarDado, proveniência,
// TabelaDados, EntityPage…). Sem agrupar, o Rollup gera um
// arquivo para cada combinação de páginas que os usa: medido com tests/e2e/smoke.js, cada página
// baixaria de 7 a 16 scripts de poucos KB a mais. Juntos, viram uma requisição. Diretórios, não uma lista
// de arquivos: componente novo nessas pastas entra sozinho.
const PASTAS_COMPARTILHADAS = ['src/components/ui', 'src/components/entidade', 'src/features/entidade', 'src/lib', 'src/hooks', 'src/utils']
function modulosCompartilhados(): string[] {
  return PASTAS_COMPARTILHADAS.flatMap((pasta) =>
    existsSync(pasta)
      ? (readdirSync(pasta, { recursive: true }) as string[])
          .filter((f) => /\.tsx?$/.test(f) && !/\.test\.tsx?$/.test(f))
          .map((f) => `./${join(pasta, f)}`)
      : [],
  )
}

export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(appVersion()) },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
  server: {
    proxy: {
      '/api': process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
      '/health': process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
      '/auth': process.env.API_PROXY_TARGET ?? 'http://localhost:8000',
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'query': ['@tanstack/react-query', 'zustand'],
          'd3': ['d3'],
          'table': ['@tanstack/react-table'],
          'recharts': ['recharts'],
          'compartilhado': modulosCompartilhados(),
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
