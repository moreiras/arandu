/// <reference types="vite/client" />

declare module '*.png' {
  const src: string
  export default src
}

// Injetado pelo vite.config.ts a partir do arquivo VERSION.
declare const __APP_VERSION__: string
