// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { SerieComparavel, SeriesNacionais, textoVariacao } from './SerieComparavel'
import type { MetricaSerie, SerieNacional } from '../../services/api'

const regra: SerieNacional['regra'] = {
  versao: 1, min_pontos_linha: 4, limiar_cobertura: 0.25,
  motivos: { metodo_mudou: 'o método ou a regra de cálculo mudou entre os pontos', ausente: 'falta a medida em um dos pontos' },
  texto: ['Variação só entre pontos comparáveis.', 'A linha só é desenhada com pelo menos 4 pontos comparáveis seguidos.'],
}

const ponto = (date: string, valor: number | null, comparavel: boolean | null = true, motivos: string[] = []) =>
  ({ date, valor, comparavel_com_anterior: comparavel, motivos, avisos: [], detalhes: motivos.map((m) => ({ codigo: m, texto: regra.motivos[m] })) })

const cortada: MetricaSerie = {
  id: 'rpki_valido_pct_v6', rotulo: 'Rotas IPv6 com origem RPKI válida', unidade: '%', selo: 'fato', fonte: 'RouteViews e VRPs do RPKI', desenhar_linha: false,
  segmentos: [[0, 1], [2, 3]],
  pontos: [ponto('2026-11-01', 50, null), ponto('2026-11-08', 52), ponto('2026-11-15', 60, false, ['metodo_mudou']), ponto('2026-11-22', 62)],
  variacao: { de: '2026-11-15', para: '2026-11-22', calculada: true, absoluta: 2, unidade: 'pp', motivos: [] },
  nota: 'Série cortada onde os pontos não são comparáveis: 2026-11-15 (o método ou a regra de cálculo mudou entre os pontos).',
}

describe('SerieComparavel', () => {
  it('não desenha linha com menos de 4 pontos comparáveis seguidos, marca o corte e mostra o motivo na tabela', () => {
    const { container } = render(<SerieComparavel metrica={cortada} regra={regra} />)
    expect(container.querySelectorAll('polyline')).toHaveLength(0)
    expect(container.querySelectorAll('circle')).toHaveLength(4)
    expect(container.querySelectorAll('line')).toHaveLength(1)
    expect(screen.getByTestId('serie-nota').textContent).toContain('2026-11-15')
    expect(screen.getByTestId('serie-variacao').textContent).toBe('+2 p.p. entre 2026-11-15 e 2026-11-22')
    expect(screen.getByRole('img').getAttribute('aria-label')).toMatch(/1 corte/)
    const tabela = within(screen.getByTestId('ver-dados')).getByRole('table')
    expect(tabela.textContent).toContain('Não: o método ou a regra de cálculo mudou entre os pontos')
    expect(screen.getByTestId('serie-comparavel').textContent).toMatch(/Fato · RouteViews e VRPs do RPKI · ref\. 2026-11-22/)
  })

  it('desenha a linha quando o trecho tem 4 pontos comparáveis', () => {
    const m: MetricaSerie = { ...cortada, desenhar_linha: true, segmentos: [[0, 1, 2, 3]], nota: undefined, pontos: [ponto('2026-11-01', 50, null), ponto('2026-11-08', 52), ponto('2026-11-15', 53), ponto('2026-11-22', 55)] }
    const { container } = render(<SerieComparavel metrica={m} regra={regra} />)
    expect(container.querySelectorAll('polyline')).toHaveLength(1)
    expect(container.querySelectorAll('line')).toHaveLength(0)
  })

  it('ponto sem valor não vira zero: não é desenhado e aparece como traço na tabela', () => {
    const m: MetricaSerie = { ...cortada, segmentos: [[0], [2]], pontos: [ponto('2026-11-01', 50, null), ponto('2026-11-08', null, false, ['ausente']), ponto('2026-11-15', 60, false, ['ausente'])] }
    const { container } = render(<SerieComparavel metrica={m} regra={regra} />)
    expect(container.querySelectorAll('circle')).toHaveLength(2)
    expect(screen.getByTestId('ver-dados').textContent).toContain('—')
  })
})

describe('textoVariacao', () => {
  it('só dá o número quando a variação foi calculada; senão diz por quê, sem número', () => {
    expect(textoVariacao({ de: 'a', para: 'b', calculada: true, absoluta: -1.5, unidade: 'pp', motivos: [] }, regra)).toBe('-1,5 p.p. entre a e b')
    const t = textoVariacao({ de: 'a', para: 'b', calculada: false, absoluta: null, unidade: null, motivos: ['metodo_mudou'] }, regra)
    expect(t).toBe('Variação não calculada entre a e b: o método ou a regra de cálculo mudou entre os pontos')
    expect(textoVariacao(undefined, regra)).toBeNull()
  })
})

describe('SeriesNacionais', () => {
  it('traz o "Como ler" com o texto da regra vindo da API e o aviso de acesso', () => {
    render(<SeriesNacionais serie={{ familia: 'roteamento', total: 4, snapshots: [], metricas: [cortada], regra }} titulo="Evolução" aviso="Sem login, 2 snapshots." />)
    expect(screen.getByText('Variação só entre pontos comparáveis.')).toBeTruthy()
    expect(screen.getByText('Sem login, 2 snapshots.')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Evolução' })).toBeTruthy()
  })
})
