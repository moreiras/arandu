import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { server } from './server'

// jsdom não implementa canvas (o fingerprint tenta usá-lo): devolve null, como um navegador que bloqueia
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as HTMLCanvasElement['getContext']

// maplibre-gl (importado pelos blocos de mapa) chama isto ao carregar; jsdom não implementa
if (!window.URL.createObjectURL) window.URL.createObjectURL = () => ''

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => { cleanup(); server.resetHandlers() })
afterAll(() => server.close())
