// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Atribuição exigida pela licença do DB-IP Lite (https://db-ip.com/db/lite.php): numa aplicação web, link para db-ip.com em toda
 * página que exibe ou usa resultados da base, com o texto abaixo. Vale para qualquer bloco ou mapa com dado das fontes
 * `prefix_geo` e `global_prefix_geo` do catálogo.
 */
export const DBIP_URL = 'https://db-ip.com'
export const DBIP_TEXTO = 'IP Geolocation by DB-IP'

/** Para o `customAttribution` do AttributionControl do MapLibre (HTML). */
export const DBIP_ATRIBUICAO_HTML = `<a href="${DBIP_URL}" target="_blank" rel="noopener noreferrer">${DBIP_TEXTO}</a>`

/** Fontes do catálogo cujo dado vem do DB-IP. */
export const FONTES_DBIP: ReadonlySet<string> = new Set(['prefix_geo', 'global_prefix_geo'])

export function usaDbIp(fontes: readonly string[] | null | undefined): boolean {
  return (fontes ?? []).some((f) => FONTES_DBIP.has(f))
}
