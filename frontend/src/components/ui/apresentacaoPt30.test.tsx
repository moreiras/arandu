// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Apresentação do PT-30: legenda dos selos, bloco recolhido de fontes e datas, cartão só com o selo e resumo em texto. */
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DESCRICAO_SELO, nomeAcessivelSelo, ROTULO_SELO } from '../entidade/proveniencia'
import { ApresentacaoRecolhida, deduplicar, FontesEDatas, GrupoFontes } from './FontesEDatas'
import { Kpi } from './Kpi'
import { LegendaSelos } from './LegendaSelos'
import { ProvenienciaCompacta } from './ProvenienciaCompacta'
import { ResumoEmTexto } from './ResumoEmTexto'
import { SELOS, SeloMarca } from './SeloMarca'

describe('legenda dos selos', () => {
  it('lista todos os selos do vocabulário com o nome e a frase da mesma fonte do Sobre', () => {
    render(<LegendaSelos />)
    expect(SELOS).toEqual(Object.keys(ROTULO_SELO))
    for (const s of SELOS) {
      const li = document.querySelector(`[data-selo-legenda="${s}"]`)!
      expect(li.textContent).toContain(ROTULO_SELO[s])
      expect(li.textContent).toContain(DESCRICAO_SELO[s])
      expect(li.querySelector('svg')).not.toBeNull()
      expect(li.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')   // o nome está no texto ao lado
    }
  })

  it('mostra só os símbolos, sem sigla, e cada selo com uma forma diferente', () => {
    render(<LegendaSelos />)
    const formas = SELOS.map((s) => document.querySelector(`[data-selo-legenda="${s}"] svg`)!.getAttribute('data-forma'))
    expect(new Set(formas).size).toBe(SELOS.length)
    for (const s of SELOS) {
      const li = document.querySelector(`[data-selo-legenda="${s}"]`)!
      expect(li.textContent).toBe(`${ROTULO_SELO[s]}: ${DESCRICAO_SELO[s]}`)   // nenhuma letra solta antes do nome
    }
  })
})

describe('selo só com símbolo e cor', () => {
  it('não leva letra e tem o nome acessível com o significado', () => {
    for (const s of SELOS) {
      const { container, unmount } = render(<SeloMarca selo={s} />)
      const el = container.querySelector(`[data-selo="${s}"]`)!
      expect(el.textContent).toBe('')
      expect(el).toHaveAttribute('role', 'img')
      expect(el).toHaveAttribute('aria-label', nomeAcessivelSelo(s))
      unmount()
    }
    expect(nomeAcessivelSelo('fato')).toBe('Fato: dado declarado ou medido na fonte')
  })

  it('com o nome visível, a forma fica oculta para leitor de tela e o nome aparece uma vez', () => {
    render(<SeloMarca selo="estimado" legivel />)
    expect(screen.getByText('Estimado')).toBeInTheDocument()
    expect(document.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    expect(screen.queryByRole('img')).toBeNull()
  })
})

describe('dica do selo no cartão', () => {
  const cartao = () => (
    <GrupoFontes>
      <Kpi rotulo="Prefixos" valor="12" selo="fato" fonte="Registro.br" dataRef="2026-09-20" />
    </GrupoFontes>
  )

  it('o botão do selo tem nome acessível e aponta para a dica com natureza, fonte e data', () => {
    render(cartao())
    const botao = screen.getByRole('button', { name: 'Fato: dado declarado ou medido na fonte' })
    expect(botao).toHaveAttribute('type', 'button')
    const dica = document.getElementById(botao.getAttribute('aria-describedby')!)!
    expect(dica).toHaveAttribute('role', 'tooltip')
    expect(dica.textContent).toMatch(/Fato/)
    expect(dica.textContent).toContain('Fonte: Registro.br')
    expect(dica.textContent).toContain('Referência: 20/09/2026')
    expect(screen.getByTestId('kpi').textContent).not.toMatch(/\bF\b/)
  })

  it('abre por foco e por hover só com CSS: nenhuma classe de estado, nenhum atributo mudando com o foco', () => {
    render(cartao())
    const botao = screen.getByTestId('selo-dica-botao')
    const dica = screen.getByTestId('selo-dica')
    expect(dica.className).toMatch(/group-focus-within\/cartao:visible/)
    expect(dica.className).toMatch(/group-hover\/cartao:visible/)
    expect(dica.className).toMatch(/\binvisible\b/)
    const antes = screen.getByTestId('kpi').outerHTML
    botao.focus()
    expect(botao).toHaveFocus()
    expect(screen.getByTestId('kpi').outerHTML).toBe(antes)    // o foco não re-renderiza nem grava estado
  })

  it('o toque (clique) foca o botão, e Esc fecha sem mover o foco', () => {
    render(cartao())
    const botao = screen.getByTestId('selo-dica-botao')
    const kpi = screen.getByTestId('kpi')
    fireEvent.click(botao)
    expect(botao).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(kpi).toHaveAttribute('data-dica-fechada')
    expect(botao).toHaveFocus()
    botao.blur()
    expect(kpi).not.toHaveAttribute('data-dica-fechada')
  })

  it('a dica não depende de a fonte existir: sem fonte nem data, traz o significado do selo', () => {
    render(<GrupoFontes><Kpi rotulo="X" valor="1" selo="inferido" /></GrupoFontes>)
    expect(screen.getByTestId('selo-dica').textContent).toContain(DESCRICAO_SELO.inferido)
  })

  it('cartão com valor ausente não mostra selo', () => {
    render(<GrupoFontes><Kpi rotulo="X" valor={null} selo="fato" fonte="F" /></GrupoFontes>)
    expect(screen.queryByTestId('selo-dica-botao')).toBeNull()
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
    expect(a.querySelector('[role=tooltip]')!.textContent).toMatch(/LACNIC/)
    expect(within(a).getByRole('button', { name: /^Fato:/ })).toBeInTheDocument()
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

  it('ao vivo, a região é anunciada como status sem mudar o resto', () => {
    const { rerender } = render(<ResumoEmTexto frases={frases} regras="r-1" />)
    expect(screen.getByTestId('resumo-em-texto')).not.toHaveAttribute('role')
    rerender(<ResumoEmTexto frases={frases} regras="r-1" aoVivo />)
    expect(screen.getByTestId('resumo-em-texto')).toHaveAttribute('role', 'status')
    expect(screen.getByTestId('resumo-em-texto')).toHaveAttribute('aria-live', 'polite')
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
