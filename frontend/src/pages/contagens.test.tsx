// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** PT-15: rótulo por universo e nota "Por que há vários totais" (TRANSV-E4, TRANSV-E5). */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { montarKpis } from '../features/home/kpisBrasilEmNumeros'
import { NotaVariosTotais } from '../components/ui/NotaVariosTotais'
import { LISTA_UNIVERSOS, rotuloDe } from '../lib/universos'
import { Sobre } from './Sobre'

const fontes = import.meta.glob(['../**/*.{ts,tsx}', '!../types/openapi.gen.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const fonte = (fim: string) => Object.entries(fontes).find(([a]) => a.endsWith(fim))![1]
const naoTeste = Object.entries(fontes).filter(([a]) => !/\.test\.tsx?$/.test(a) && !a.includes('/test/') && !a.includes('openapi.gen'))

describe('nota "Por que há vários totais" (PT-15)', () => {
  it('as páginas com totais que diferem trazem a nota, ligada à explicação em /sobre#contagens', () => {
    for (const arq of ['/features/home/BrasilEmNumeros.tsx', '/features/panorama/ResumoTecnico.tsx', '/Snapshots.tsx', '/IXPs.tsx', '/BGP.tsx',
      '/components/stats/StatsOverview.tsx', '/OperadorasPage.tsx']) expect(fonte(arq), arq).toMatch(/<NotaVariosTotais/)
    render(<MemoryRouter><NotaVariosTotais /></MemoryRouter>)
    expect(screen.getByTestId('nota-varios-totais')).toHaveTextContent('Por que há vários totais')
    expect(screen.getByRole('link', { name: 'Como cada total é contado' })).toHaveAttribute('href', '/sobre#contagens')
  })

  it('a explicação em /sobre#contagens lista todos os universos, com o rótulo e a definição da mesma tabela das telas', () => {
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><Sobre /></MemoryRouter></QueryClientProvider>)
    const secao = screen.getByTestId('sobre-contagens')
    expect(secao).toHaveTextContent('Por que há vários totais')
    expect(secao.querySelectorAll('[data-universo]')).toHaveLength(LISTA_UNIVERSOS.length)
    expect(secao).toHaveTextContent(rotuloDe('sessaoRs'))
    expect(secao).toHaveTextContent('Não aditivos')
  })
})

describe('rótulo por universo (PT-15)', () => {
  it('nenhuma tela diz "alocados pelo Registro.br", "peering direto" ou "participantes diretos" para um número que não é isso', () => {
    const proibido = /ASes brasileiros alocados|ASNs? alocados pelo Registro\.br|ASNs BR alocados|ASNs em peering direto|[Pp]eering direto|[Pp]eers? diretos?|[Pp]ar direto|Participantes diretos|Direto em PTT|usuários brasileiros visíveis via este IXP|Mercado não visto \(estimativa\)/
    const achados = naoTeste.filter(([, s]) => proibido.test(s)).map(([a]) => a)
    expect(achados).toEqual([])
  })

  it('home: o total de ASNs, o de IPv6, o de usuários e o de declarantes usam o rótulo do universo e não repetem nome', () => {
    const { rede, mercado } = montarKpis({ total_asns_br: 9129, br_asns_ft_v6: 7573, br_apnic_users_total: 161288456 } as never, null,
      { total_acessos: 1, operadoras_ativas: 9928, municipios_atendidos: 5571, mes_referencia: '2026-09', serie_total: [] } as never, '2026-11-22')
    const rotulos = Object.fromEntries([...rede, ...mercado].map((k) => [k.id, k.rotulo]))
    expect(rotulos.ases).toBe(rotuloDe('asnsLacnic'))
    expect(rotulos.ipv6).toBe(rotuloDe('asnsAnunciamV6'))
    expect(rotulos.usuarios).toBe(rotuloDe('usuariosPais'))
    expect(rotulos.operadoras).toBe(rotuloDe('declarantesFixo'))
    expect(rotulos.municipios).toContain('tabela do IBGE')
    const todos = [...rede, ...mercado].map((k) => k.rotulo)
    expect(new Set(todos).size).toBe(todos.length)
    expect([...rede, ...mercado].find((k) => k.id === 'ases')!.fonte).toBe('LACNIC (delegated-extended)')
  })

  it('o resumo do panorama técnico e o painel de estatísticas rotulam o total de ASNs pela delegação da LACNIC', () => {
    expect(fonte('/features/panorama/ResumoTecnico.tsx')).toMatch(/rotuloDe\('asnsLacnic'\)/)
    expect(fonte('/features/panorama/ResumoTecnico.tsx')).toMatch(/rotuloDe\('sessaoRs'\)/)
    expect(fonte('/components/stats/StatsOverview.tsx')).toMatch(/delegados pela LACNIC ao Brasil/)
  })
})
