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
    return {
      headers: ['asn', 'nome', 'municipio', 'uf', 'pais', 'confianca_geo', 'tem_rpki', 'tem_aspa', 'porte', 'pct_v6', 'ptts_direto'],
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
        ]
      }),
    }
  }
  if (layer === 'outorgas_scm') {
    return {
      headers: ['cnpj', 'razao_social', 'nome_fantasia', 'municipio', 'uf', 'situacao', 'asns'],
      rows: features.map(f => {
        const p = props(f)
        return [p.cnpj ?? '', p.razao_social ?? '', p.nome_fantasia ?? '', p.municipio ?? '', p.uf ?? '', p.situacao ?? '', (p.asns ?? []).join(' ')]
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
