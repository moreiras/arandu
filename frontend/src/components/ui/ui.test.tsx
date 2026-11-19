// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ColumnDef } from '@tanstack/react-table'
import { Bloco, enquadramento, FichaEntidade, Kpi, MapaMoldura, ProvenienciaCompacta, TabelaPaginada } from '.'

const prov = { fontes: ['bgp_ixbr'], selo: 'fato' as const }
const fontes = [{ id: 'bgp_ixbr', as_of: '2026-11-01', coletado_em: '2026-11-02', frescor: 'ok' }] as never

describe('Kpi', () => {
  it('mostra valor, referência e variação; ausente vira traço, não zero', () => {
    const { rerender } = render(<Kpi rotulo="ASes" valor="1.234" referencia="mediana: 10" variacao={{ texto: '+3', bom: true }} fonte="x" dataRef="2026-11-01" />)
    expect(screen.getByText('1.234')).toHaveAttribute('title', 'Fonte: x · ref. 01/11/2026')
    expect(screen.getByText('+3')).toHaveClass('text-ok-700')
    rerender(<Kpi rotulo="ASes" valor={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})

describe('Bloco', () => {
  it('recolhe e expande por clique, mantém o título e o Como ler', () => {
    render(<Bloco id="b" titulo="Rotas" proveniencia={prov} fontes={fontes} comoLer={<p>ressalva</p>}><p>conteúdo</p></Bloco>)
    const botao = screen.getByRole('button', { name: /Rotas/ })
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Como ler')).toBeInTheDocument()
    fireEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText('conteúdo').closest('div[hidden]')).not.toBeNull()
  })
})

describe('ProvenienciaCompacta', () => {
  it('uma linha com selo, fonte e data; detalhe completo dentro do details', () => {
    render(<ProvenienciaCompacta bloco={prov} fontes={fontes} />)
    const d = screen.getByTestId('proveniencia-compacta')
    expect(within(d).getByText(/Fato · bgp_ixbr · ref\. 01\/11\/2026/)).toBeInTheDocument()
    expect(within(d).getByTestId('proveniencia')).toBeInTheDocument()
  })
})

interface L { nome: string; uf: string; n: number; extra: string }
const colunas: ColumnDef<L, any>[] = [
  { accessorKey: 'nome', header: 'Nome' }, { accessorKey: 'uf', header: 'UF' }, { accessorKey: 'n', header: 'Valor' }, { accessorKey: 'extra', header: 'Extra', meta: { cartao: false } },
]
const dados: L[] = Array.from({ length: 23 }, (_, i) => ({ nome: `Rede ${i + 1}`, uf: 'CE', n: i, extra: 'x' }))

describe('TabelaPaginada', () => {
  it('10 linhas por página e paginação', () => {
    render(<TabelaPaginada colunas={colunas} dados={dados} rotulo="Redes" />)
    expect(screen.getAllByRole('row')).toHaveLength(11)
    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }))
    expect(screen.getByText(/Página 2 de 3 · 23 linhas/)).toBeInTheDocument()
  })
  it('modo cartão: título, no máximo 4 campos e sem a coluna marcada', () => {
    render(<TabelaPaginada colunas={colunas} dados={dados} rotulo="Redes" forcarCartao />)
    expect(screen.getAllByTestId('cartao')).toHaveLength(10)
    expect(screen.queryByText('Extra')).toBeNull()
  })
  it('vazio mostra o estado vazio', () => {
    render(<TabelaPaginada colunas={colunas} dados={[]} rotulo="Redes" vazio="Sem redes" />)
    expect(screen.getByText(/Sem redes/)).toBeInTheDocument()
  })
})

describe('MapaMoldura e enquadramento', () => {
  it('legenda com rótulo e caixa que cobre os pontos', () => {
    render(<MapaMoldura titulo="Mapa" legenda={[{ rotulo: 'IPv6', cor: '#7e22ce' }]}><div /></MapaMoldura>)
    expect(screen.getByRole('list', { name: 'Legenda' })).toHaveTextContent('IPv6')
    expect(enquadramento([[-46, -23], [-43, -22]], 1)).toEqual([-47, -24, -42, -21])
    expect(enquadramento([])).toBeNull()
  })
})

describe('FichaEntidade', () => {
  it('cabeçalho, síntese com selo e KPIs', () => {
    render(<FichaEntidade nome="AS64500" sintese={{ texto: 'Rede com IPv6.', selo: 'inferido', regra: 'r1' }} kpis={[{ rotulo: 'Prefixos', valor: 12 }]} />)
    expect(screen.getByRole('heading', { name: 'AS64500' })).toBeInTheDocument()
    expect(screen.getByTestId('sintese')).toHaveTextContent('Inferido')
    expect(screen.getByTestId('kpi')).toHaveTextContent('12')
  })
})
