// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Apresentação do PT-30: legenda dos selos, bloco recolhido de fontes e datas, cartão só com o selo e resumo em texto. */
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DESCRICAO_SELO, ROTULO_SELO } from '../entidade/proveniencia'
import { ApresentacaoRecolhida, deduplicar, FontesEDatas, GrupoFontes } from './FontesEDatas'
import { Kpi } from './Kpi'
import { LegendaSelos } from './LegendaSelos'
import { ProvenienciaCompacta } from './ProvenienciaCompacta'
import { ResumoEmTexto } from './ResumoEmTexto'
import { SELOS } from './SeloMarca'

describe('legenda dos selos', () => {
  it('lista todos os selos do vocabulário com o nome e a frase da mesma fonte do Sobre', () => {
    render(<LegendaSelos />)
    expect(SELOS).toEqual(Object.keys(ROTULO_SELO))
    for (const s of SELOS) {
      const li = document.querySelector(`[data-selo-legenda="${s}"]`)!
      expect(li.textContent).toContain(ROTULO_SELO[s])
      expect(li.textContent).toContain(DESCRICAO_SELO[s])
      expect(li.querySelector('svg')).not.toBeNull()
    }
  })
})

describe('fontes e datas recolhidas', () => {
  it('Kpi dentro do grupo mostra só o selo e entrega fonte e data ao bloco recolhido, sem repetição', () => {
    render(
      <GrupoFontes>
        <Kpi rotulo="A" valor="1" selo="fato" fonte="LACNIC" dataRef="2026-09-20" />
        <Kpi rotulo="B" valor="2" selo="fato" fonte="LACNIC" dataRef="2026-09-20" />
        <Kpi rotulo="C" valor="3" selo="estimado" fonte="APNIC Labs" dataRef="2026-09" />
        <Kpi rotulo="D" valor={null} selo="fato" fonte="Fonte sem valor" dataRef="2026-01-01" />
      </GrupoFontes>,
    )
    const [a] = screen.getAllByTestId('kpi')
    expect(a.textContent).not.toMatch(/LACNIC/)
    expect(within(a).getByText('Fato', { selector: '.sr-only' })).toBeInTheDocument()
    const bloco = screen.getByTestId('fontes-e-datas')
    expect(bloco.tagName).toBe('DETAILS')
    expect(bloco).not.toHaveAttribute('open')
    const itens = bloco.querySelectorAll('[data-fonte-item]')
    expect(itens).toHaveLength(2)
    expect(bloco.textContent).toMatch(/LACNIC.*referência: 20\/09\/2026/)
    expect(bloco.textContent).toMatch(/APNIC Labs.*referência: 09\/2026/)
    expect(bloco.textContent).not.toMatch(/Fonte sem valor/)
  })

  it('Kpi fora de um grupo mantém a linha visível de antes', () => {
    render(<Kpi rotulo="A" valor="1" selo="fato" fonte="LACNIC" dataRef="2026-09-20" />)
    expect(screen.getByTestId('kpi').textContent).toMatch(/Fato · LACNIC · ref\. 2026-09-20/)
  })

  it('deduplica e ignora item sem fonte nem data', () => {
    expect(deduplicar([{ selo: 'fato', fonte: 'X', dataRef: '2026-01' }, { selo: 'fato', fonte: 'X', dataRef: '2026-01' }, { selo: 'fato' }])).toHaveLength(1)
    const { container } = render(<FontesEDatas itens={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('resumo em texto', () => {
  const frases = [
    { id: 'a', texto: 'Primeira frase inteira, sem corte.', selo: 'fato' as const, fonte: 'Fonte A', dataRef: '2026-09-20' },
    { id: 'b', texto: 'Segunda frase.', selo: 'estimado' as const, fonte: 'Fonte B', dataRef: '2026-08' },
  ]
  it('mostra as frases em sequência sem selo nem fonte, e agrega as fontes num bloco recolhido', () => {
    render(<ResumoEmTexto frases={frases} regras="r-1" />)
    const r = screen.getByTestId('resumo-em-texto')
    expect(within(r).getByText(/Primeira frase inteira, sem corte\./)).toBeInTheDocument()
    expect(r.querySelector('[data-selo]')).toBeInTheDocument()    // só dentro do bloco recolhido
    const bloco = within(r).getByTestId('fontes-e-datas')
    expect(bloco.textContent).toMatch(/Fonte A.*20\/09\/2026/)
    expect(r.querySelector('p')!.textContent).toBe('Primeira frase inteira, sem corte. Segunda frase.')
  })

  it('dentro de um grupo, entrega as fontes ao bloco da seção e não cria outro', () => {
    render(<GrupoFontes><ResumoEmTexto frases={frases} regras="r-1" /></GrupoFontes>)
    expect(screen.getAllByTestId('fontes-e-datas')).toHaveLength(1)
  })
})

describe('proveniência do bloco no modo recolhido', () => {
  it('o resumo da linha vira "Fonte e data" e o detalhe continua no DOM', () => {
    render(<ApresentacaoRecolhida><ProvenienciaCompacta bloco={{ fontes: ['anatel_sici'], selo: 'fato' }} fontes={[{ id: 'anatel_sici', as_of: '2026-08' }]} /></ApresentacaoRecolhida>)
    const d = screen.getByTestId('proveniencia-compacta')
    expect(d.querySelector('summary')!.textContent).toContain('Fonte e data')
    expect(d.querySelector('summary')!.textContent).not.toMatch(/anatel_sici/)
    expect(d.textContent).toMatch(/anatel_sici.*ref\. 08\/2026/)
  })
})

describe('singular e plural pelo número (PT-30)', () => {
  it('palavra() escolhe pelo número e trata ausente como plural', async () => {
    const { palavra } = await import('../../lib/sintese')
    expect(palavra(1, 'bloco', 'blocos')).toBe('bloco')
    expect(palavra(0, 'bloco', 'blocos')).toBe('blocos')
    expect(palavra(2, 'bloco', 'blocos')).toBe('blocos')
    expect(palavra(undefined, 'bloco', 'blocos')).toBe('blocos')
  })
})
