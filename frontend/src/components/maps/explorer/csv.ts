// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Exportação CSV das camadas do mapa: `linhasCsv`/`textoCsv` são puras (testadas); `baixarCsv` só cuida do download no navegador. */
import type { DataLayerId } from './tipos'
import { nomeArquivo } from '../../../lib/site'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const props = (f: GeoJSON.Feature) => (f.properties ?? {}) as Record<string, any>

/** Cabeçalho e linhas da camada, ou `null` se a camada não tem exportação. */
export function linhasCsv(features: GeoJSON.Feature[], layer: DataLayerId): { headers: string[]; rows: string[][] } | null {
  if (layer === 'asns_geo') {
    // Colunas do ROV só quando a consulta foi feita com "Colorir por ROV" (o servidor só então traz `rov_faixa`); sem isso ficariam vazias e sugeririam ausência de medição.
    const comRov = features.some(f => props(f).rov_faixa !== undefined)
    return {
      headers: ['asn', 'nome', 'municipio', 'uf', 'pais', 'confianca_geo', 'tem_roa', 'tem_aspa', 'porte', 'pct_v6', 'ptts_direto', ...(comRov ? ['rov_faixa', 'rov_pct'] : [])],
      rows: features.map(f => {
        const p = props(f)
        return [
          String(p.asn ?? ''),
          p.name ?? '',
          p.city ?? '',
          p.uf ?? '',
          p.country ?? '',
          p.geo_confidence ?? '',
          p.has_rpki == null ? '' : p.has_rpki ? 'sim' : 'não',
          p.has_aspa == null ? '' : p.has_aspa ? 'sim' : 'não',
          p.porte ?? '',
          p.pct_v6 != null ? String(p.pct_v6) : '',
          p.ixps_direct ?? '',
          ...(comRov ? [p.rov_faixa ?? '', p.rov_pct != null ? String(p.rov_pct) : ''] : []),
        ]
      }),
    }
  }
  if (layer === 'outorgas_scm') {
    return {
      headers: ['cnpj', 'razao_social', 'nome_fantasia', 'municipio', 'uf', 'asns', 'sici_ativo', 'sici_mes_referencia', 'sici_acessos', 'sici_pf', 'sici_pj', 'sici_municipios', 'sici_tecnologia'],
      rows: features.map(f => {
        const p = props(f)
        // Campos do SICI como no balão: sem o campo (snapshot antigo) a célula fica vazia, sem afirmar nada; "sim" e "não" só quando a camada traz `sici_ativo`.
        const ativo = p.sici_ativo === undefined || p.sici_ativo === null ? '' : p.sici_ativo === true || p.sici_ativo === 'true' ? 'sim' : 'não'
        const n = (v: unknown) => (v == null || v === '' ? '' : String(v))
        return [
          p.cnpj ?? '', p.razao_social ?? '', p.nome_fantasia ?? '', p.municipio ?? '', p.uf ?? '', (p.asns ?? []).join(' '),
          ativo, p.sici_mes_referencia ?? '', n(p.sici_acessos), n(p.sici_pf), n(p.sici_pj), n(p.sici_municipios), p.sici_tecnologia ?? '',
        ]
      }),
    }
  }
  if (layer === 'prefixes_v4' || layer === 'prefixes_v6') {
    return {
      headers: ['as_origem', 'ip_versao', 'municipio', 'uf', 'pais', 'prefixos'],
      rows: features.map(f => {
        const p = props(f)
        return [String(p.origin_asn ?? ''), String(p.ip_version ?? ''), p.city ?? '', p.uf ?? '', p.country ?? '', String(p.prefix_count ?? '')]
      }),
    }
  }
  if (layer === 'prefixos_ix_v4' || layer === 'prefixos_ix_v6') {
    return {
      headers: ['blocos', 'unidade', 'as_origem', 'peers_ptt', 'municipio', 'uf', 'pais'],
      rows: features.map(f => {
        const p = props(f)
        return [String(p.block_count ?? ''), p.block_unit ?? '', (p.origin_asns ?? []).join(' '), (p.peer_asns ?? []).join(' '), p.city ?? '', p.uf ?? '', p.country ?? '']
      }),
    }
  }
  return null
}

/** CSV com aspas duplicadas e BOM (o Excel precisa dele para acentos). */
export function textoCsv(headers: string[], rows: string[][]): string {
  const escape = (v: string) => `"${String(v).replace(/"/g, '""')}"`
  return '﻿' + [headers, ...rows].map(r => r.map(escape).join(',')).join('\n')
}

export function baixarCsv(features: GeoJSON.Feature[], layer: DataLayerId, snapshotDate: string) {
  if (features.length === 0) return
  const dados = linhasCsv(features, layer)
  if (!dados) return
  const blob = new Blob([textoCsv(dados.headers, dados.rows)], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nomeArquivo(`${layer}-${snapshotDate}.csv`)
  a.click()
  URL.revokeObjectURL(url)
}
