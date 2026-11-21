// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Identidade pública do site. Os valores vêm do `.env` na compilação (`VITE_SITE_*`, repassados pelo
 * `Dockerfile.frontend`); sem eles valem os padrões, os mesmos de `core/site.py`. Nomes internos (chaves de armazenamento) não dependem disto.
 */
const env = import.meta.env as Record<string, string | undefined>
const valor = (chave: string, padrao: string) => (env[chave] ?? '').trim() || padrao

export const SITE = {
  nome: valor('VITE_SITE_NOME', 'Arandurapé'),
  nomeExtenso: valor('VITE_SITE_NOME_EXTENSO', 'Mapa da Internet brasileira'),
  url: valor('VITE_SITE_URL', 'http://localhost').replace(/\/+$/, ''),
  prefixoArquivos: valor('VITE_SITE_PREFIXO_ARQUIVOS', 'arandurape'),
  software: valor('VITE_SITE_SOFTWARE', 'Arandurapé'),
  /** Endereço do código-fonte que esta instância roda (AGPL §13; o Sobre o oferece). */
  codigoFonte: valor('VITE_SITE_CODIGO_FONTE', 'https://github.com/moreiras/arandu').replace(/\/+$/, ''),
  /** Nome do servidor MCP na configuração do cliente e esquema das URIs dos recursos (`arandurape://…`). */
  mcp: valor('VITE_SITE_MCP_ESQUEMA', 'arandurape'),
  /** E-mail de contato para correções e dúvidas (aparece na página Sobre). */
  contato: valor('VITE_SITE_CONTATO', 'arandurape@internetbitabit.com.br'),
  /** E-mail do controlador para privacidade e direitos do titular (Privacidade, Uso aceitável). */
  contatoPrivacidade: valor('VITE_SITE_CONTATO_PRIVACIDADE', 'lgpd@internetbitabit.com.br'),
}

/** "Arandurapé — Mapa da Internet brasileira". */
export const TITULO_SITE = `${SITE.nome} — ${SITE.nomeExtenso}`

/** Nome de arquivo baixado: `nomeArquivo('comparar-ixps.csv')` → `arandurape-comparar-ixps.csv`. */
export const nomeArquivo = (resto: string) => `${SITE.prefixoArquivos}-${resto}`

// O mesmo marcador de `core/site.py` (`_NOME_ANTIGO`). O `\b` do JavaScript não reconhece "é" como letra: as fronteiras são por lookaround Unicode.
const NOME_DO_SOFTWARE = /(?<![\p{L}\p{N}_])(?:ARANDURAP[ÉE]|Arandurap[ée])(?![\p{L}\p{N}_])/gu

/**
 * Textos gerados com o nome do software ("Estimativa do Arandurapé", `arandurape://`) com o nome do site, como `core.site.com_identidade`
 * faz na API e no MCP. Para o que o front lê sem passar pela API (o `catalogo.json`). Só valores de texto mudam, nunca chaves.
 */
export function comIdentidade<T>(valor: T): T {
  if (typeof valor === 'string') {
    return valor.replace(/arandurape:\/\//g, `${SITE.mcp}://`).replace(NOME_DO_SOFTWARE, SITE.nome) as T
  }
  if (Array.isArray(valor)) return valor.map((v) => comIdentidade(v)) as T
  if (valor !== null && typeof valor === 'object') {
    return Object.fromEntries(Object.entries(valor).map(([k, v]) => [k, comIdentidade(v)])) as T
  }
  return valor
}
