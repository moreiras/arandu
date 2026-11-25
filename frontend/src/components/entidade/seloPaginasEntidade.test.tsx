// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Selo, fonte e data nos indicadores das páginas de entidade (PT-14 / TRANSV-E3): AS, operadora, grupo, ficha genérica e os números grandes locais. */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FichaAsn } from '../../features/asn/FichaAsn'
import { FichaOperadora } from '../../features/operadora/FichaOperadora'
import { FichaEntidade } from '../ui'
import { LinhaProveniencia } from '../ui/Kpi'
import type { OperadoraCtx } from '../../features/operadora/contexto'
import type { ASNDocument } from '../../types/api'

const fontes = import.meta.glob(
  ['../../features/grupo/index.tsx', '../../features/grupo/blocks/*.tsx', '../../features/asn/FichaAsn.tsx', '../../features/operadora/FichaOperadora.tsx',
    '../../components/stats/StatsOverview.tsx', '../../pages/CDNCapPage.tsx'],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>

const fonteDe = (fim: string) => Object.entries(fontes).find(([a]) => a.endsWith(fim))![1]
const kpiDe = (rotulo: string) => screen.getAllByTestId('kpi').find((k) => k.getAttribute('data-kpi-rotulo') === rotulo)!
/** A linha de proveniência de um KPI, sem o texto só para leitor de tela. */
const prov = (rotulo: string) => kpiDe(rotulo).querySelector('[data-kpi-proveniencia]')!.textContent!.replace('Natureza, fonte e data de referência: ', '')

describe('selo nas páginas de entidade (PT-14)', () => {
  it('toda chamada de Kpi do grupo declara selo, e os números grandes locais de StatsOverview e CDNCapPage também', () => {
    for (const [arq, src] of Object.entries(fontes)) {
      const chamadas = src.match(/<Kpi\s[^>]*\/>/g) ?? []
      for (const c of chamadas) expect(c, `${arq}: ${c}`).toMatch(/selo=/)
      expect(src.match(/<Kpi[\s>]/g)?.length ?? 0, arq).toBe(chamadas.length)
    }
    const grupo = Object.entries(fontes).filter(([a]) => a.includes('/features/grupo/'))
    expect(grupo.reduce((n, [, s]) => n + (s.match(/<Kpi\s/g)?.length ?? 0), 0)).toBe(29)
    expect(fonteDe('/StatsOverview.tsx').match(/<Kpi\s/g)).toHaveLength(11)
    expect(fonteDe('/CDNCapPage.tsx').match(/<Kpi\s/g)).toHaveLength(6)
  })

  it('ficha do AS: prefixos e sessões são fato com a fonte; usuários são estimado do APNIC, todos com a data do snapshot', () => {
    const doc = { asn: 64496, name: 'X', snapshot_date: '2026-11-22', global_prefixes_v4_count: 3, global_prefixes_v6_count: 1, ixps_direct: ['sp'], ixps_origin: [], apnic_users: 3068, apnic_v6_pct_as: 20, alerts: [], rpki_validation: {} } as unknown as ASNDocument
    render(<FichaAsn doc={doc} />)
    const prox = prov
    expect(prox('Prefixos IPv6 anunciados')).toBe('Fato · tabela global (RouteViews) · ref. 2026-11-22')
    expect(prox('PTTs com sessão em route server')).toBe('Fato · looking glass do IX.br · ref. 2026-11-22')
    expect(prox('Usuários estimados (APNIC)')).toBe('Estimado · APNIC Labs · ref. 2026-11-22')
    expect(prox('Usuários IPv6')).toBe('Estimado · APNIC Labs · ref. 2026-11-22')
    for (const k of screen.getAllByTestId('kpi')) expect(k.querySelector('[data-kpi-selo]'), k.textContent ?? '').not.toBeNull()
  })

  it('ficha da operadora: SICI é fato no mês de referência; ASNs do mesmo CNPJ levam a data do snapshot', () => {
    const ctx = { cnpjFinal: '90000001000129', hasScm: true, hasSici: true, hasStfc: false, hasSeac: false, b2cPct: 0, servicos: [],
      data: { snapshot_date: '2026-11-22', municipios: 12, asns: [64500] } as any,
      indicadores: { mes_referencia: '2026-09', metodologia: 'm', acessos: 12345, share_br: 0.42, posicao_br: 31, var_aa: { abs: 500, pct: 4.2 } } as any } as unknown as OperadoraCtx
    render(<FichaOperadora nome="Provedor" ctx={ctx} />)
    const t = prov
    expect(t('Acessos fixos (2026-09)')).toBe('Fato · Anatel (SICI) · ref. 2026-09')
    expect(t('Municípios com acessos')).toBe('Fato · Anatel (SICI) · ref. 2026-09')
    expect(t('ASNs')).toBe('Fato · Registro.br (mesmo CNPJ) · ref. 2026-11-22')
    for (const k of screen.getAllByTestId('kpi')) expect(k.querySelector('[data-kpi-selo]'), k.textContent ?? '').not.toBeNull()
  })

  it('FichaEntidade repassa o selo ao Kpi', () => {
    render(<FichaEntidade nome="AS64500" kpis={[{ rotulo: 'Usuários', valor: 10, selo: 'estimado', fonte: 'APNIC Labs', dataRef: '2026-11-15' }]} />)
    expect(screen.getByText('Estimado · APNIC Labs · ref. 2026-11-15')).toBeInTheDocument()
  })

  it('LinhaProveniencia (números grandes locais) mostra a mesma linha em texto e não renderiza sem dado', () => {
    const { container, rerender } = render(<LinhaProveniencia selo="inferido" fonte="Anatel (SICI) e Registro.br" dataRef="2026-11-22T10:00:00Z" />)
    expect(container).toHaveTextContent('Inferido · Anatel (SICI) e Registro.br · ref. 2026-11-22')
    rerender(<LinhaProveniencia />)
    expect(container).toBeEmptyDOMElement()
  })
})
