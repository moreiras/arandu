// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable, EmptyState, EntityHeader, Provenance, Section, formatarReferencia, rotuloFrescor } from '.'
import type { FonteEntrada } from '.'

const fontes: FonteEntrada[] = [
  { id: 'anatel_sici', as_of: '2026-08', coletado_em: '2026-10-11', frescor: 'defasada', origem: 'armazem' },
  { id: 'apnic_pop', as_of: '2026-10-11', coletado_em: '2026-10-11', frescor: 'ok' },
]

describe('proveniência', () => {
  it('formata referência diária e mensal; texto estranho passa intacto', () => {
    expect(formatarReferencia('2026-10-11')).toBe('11/10/2026')
    expect(formatarReferencia('2026-08')).toBe('08/2026')
    expect(formatarReferencia(null)).toBe('—')
    expect(formatarReferencia('hoje')).toBe('hoje')
  })

  it('rotula o frescor e a fonte ausente', () => {
    expect(rotuloFrescor(fontes[0])).toBe('defasada')
    expect(rotuloFrescor(undefined)).toMatch(/sem coleta registrada/)
  })

  it('mostra selo, as duas datas e o frescor quando não está em dia', () => {
    render(<Provenance bloco={{ fontes: ['anatel_sici'], selo: 'estimado' }} fontes={fontes} snapshot="2026-10-11" />)
    const p = screen.getByTestId('proveniencia')
    expect(within(p).getByText('Estimado')).toBeInTheDocument()
    expect(p).toHaveTextContent('anatel_sici · ref. 08/2026 · coletado em 11/10/2026 · defasada')
    expect(p).toHaveTextContent('snapshot 11/10/2026')
  })

  it('fonte em dia não repete "em dia"; selo padrão é fato', () => {
    render(<Provenance bloco={{ fontes: ['apnic_pop'] }} fontes={fontes} />)
    const p = screen.getByTestId('proveniencia')
    expect(p).toHaveTextContent('Fato')
    expect(p).not.toHaveTextContent('em dia')
  })

  it('sem sources[] mostra só o id; com sources[] sem a fonte, avisa — nunca inventa data', () => {
    const { rerender } = render(<Provenance bloco={{ fontes: ['x'] }} />)
    expect(screen.getByTestId('proveniencia')).not.toHaveTextContent('ref.')
    rerender(<Provenance bloco={{ fontes: ['x'] }} fontes={fontes} />)
    expect(screen.getByTestId('proveniencia')).toHaveTextContent('sem coleta registrada no manifesto')
  })
})

describe('Section, EntityHeader e EmptyState', () => {
  it('Section sempre traz o rodapé de proveniência e o título como landmark', () => {
    render(<Section id="rpki" titulo="RPKI" proveniencia={{ fontes: ['apnic_pop'] }} fontes={fontes}><p>conteúdo</p></Section>)
    expect(screen.getByRole('region', { name: 'RPKI' })).toBeInTheDocument()
    expect(screen.getByText('conteúdo')).toBeInTheDocument()
    expect(screen.getByTestId('proveniencia')).toBeInTheDocument()
  })

  it('semTitulo não duplica o h2 (o título vira aria-label) e plana tira o cartão', () => {
    render(<Section id="x" titulo="Prefixos" semTitulo plana proveniencia={{ fontes: ['apnic_pop'] }}><h2>Meu próprio título</h2></Section>)
    const r = screen.getByRole('region', { name: 'Prefixos' })
    expect(screen.getAllByRole('heading')).toHaveLength(1)
    expect(r.className).not.toContain('border')
  })

  it('EntityHeader mostra tipo, nome, identificadores, selos e snapshot', () => {
    render(<EntityHeader tipo="Operadora" nome="Provedor X" identificadores={[{ rotulo: 'CNPJ', valor: '00.000.000/0001-00' }]}
      selos={[{ rotulo: 'SCM', tom: 'azul' }]} snapshot="2026-10-11" />)
    expect(screen.getByRole('heading', { level: 1, name: /Provedor X/ })).toHaveTextContent('Provedor XSCM')
    expect(screen.getByText('SCM')).toBeInTheDocument()
    expect(screen.getByText('11/10/2026')).toBeInTheDocument()
    expect(screen.getByText('CNPJ', { exact: false })).toBeInTheDocument()
  })

  it('EmptyState diz a data do snapshot', () => {
    render(<EmptyState snapshot="2026-10-11" />)
    expect(screen.getByRole('status')).toHaveTextContent('Sem dado neste snapshot (11/10/2026).')
  })
})

interface Linha { nome: string; n: number }
const colunas: ColumnDef<Linha, any>[] = [
  { accessorKey: 'nome', header: 'Nome' },
  { accessorKey: 'n', header: 'Total' },
]
const dados: Linha[] = [{ nome: 'b', n: 2 }, { nome: 'a', n: 3 }, { nome: 'c', n: 1 }]
const primeiraColuna = () => screen.getAllByRole('row').slice(1).map((r) => within(r).getAllByRole('cell')[0].textContent)

describe('DataTable', () => {
  it('ordena ao clicar no cabeçalho, alternando o sentido', () => {
    render(<DataTable rotulo="teste" colunas={colunas} dados={dados} />)
    fireEvent.click(screen.getByRole('button', { name: 'Nome' }))
    expect(primeiraColuna()).toEqual(['a', 'b', 'c'])
    expect(screen.getByRole('columnheader', { name: /Nome/ })).toHaveAttribute('aria-sort', 'ascending')
    fireEvent.click(screen.getByRole('button', { name: /Nome/ }))
    expect(primeiraColuna()).toEqual(['c', 'b', 'a'])
  })

  it('pagina localmente', () => {
    render(<DataTable rotulo="teste" colunas={colunas} dados={dados} tamanhoPagina={2} />)
    expect(primeiraColuna()).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }))
    expect(primeiraColuna()).toHaveLength(1)
    expect(screen.getByText(/Página 2 de 2/)).toBeInTheDocument()
  })

  it('expande a linha com o conteúdo da página', () => {
    render(<DataTable rotulo="teste" colunas={colunas} dados={dados} linhaExpandida={(l) => <span>detalhe de {l.original.nome}</span>} />)
    fireEvent.click(screen.getAllByRole('button', { name: 'Expandir linha' })[0])
    expect(screen.getByText('detalhe de b')).toBeInTheDocument()
  })

  it('sem dados mostra o estado vazio com a data', () => {
    render(<DataTable rotulo="teste" colunas={colunas} dados={[]} snapshot="2026-10-11" vazio="Sem outorgas" />)
    expect(screen.getByRole('status')).toHaveTextContent('Sem outorgas (11/10/2026).')
  })
})
