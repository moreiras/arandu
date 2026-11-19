// Camadas de infraestrutura física (cabos, enlaces, linhas) endereçadas pelo hash do
// conteúdo: `/map/layers` informa a URL com `?v=<hash>`, que não depende da data e a API
// serve como `immutable`. Enquanto o arquivo não muda entre snapshots, o navegador não
// baixa de novo (só os cabos têm 1,8 MB). Passo 1.4.0.

const urls: Record<string, string> = {}

/** URL versionada da camada, ou a URL sem hash enquanto `/map/layers` não respondeu (ou falhou). */
export function urlCamada(layer: string, fallback: string): string {
  return urls[layer] ?? fallback
}

/** Busca os hashes uma vez no carregamento da aplicação; falha em silêncio (usa o fallback). */
export async function carregarCamadasEstaticas(fetcher: typeof fetch = fetch): Promise<void> {
  try {
    const res = await fetcher('/api/v1/map/layers', { credentials: 'include' })
    if (!res.ok) return
    const corpo = (await res.json()) as { camadas?: Record<string, { url?: string }> }
    for (const [layer, info] of Object.entries(corpo.camadas ?? {})) {
      if (info?.url) urls[layer] = info.url
    }
  } catch {
    // sem hash: as camadas continuam servidas pela URL sem versão
  }
}

/** Só para testes. */
export function limparCamadasEstaticas(): void {
  for (const k of Object.keys(urls)) delete urls[k]
}
