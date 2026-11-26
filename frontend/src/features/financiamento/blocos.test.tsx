// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CreditoPublicoBloco, SancoesBloco } from './blocos'
import type { FinanciamentoOperadora, SancaoRegistro } from '../../types/api'

const san = (o: Partial<SancaoRegistro>): SancaoRegistro => ({
  cnpj: '11111111000191', cadastro: 'CEIS', codigo: '1', categoria: 'Impedimento/proibição de contratar com prazo determinado', inicio: '2024-01-10', fim: '2027-01-10', publicacao: '2024-01-10', abrangencia: 'x', orgao: 'Prefeitura Fictícia',
  uf_orgao: 'ES', esfera: 'MUNICIPAL', fundamento: 'LEI 8666 - ART. 87, III', processo: 'P-1', situacao: 'vigente', sem_prazo: false, ...o,
})
const base = (o: Partial<FinanciamentoOperadora>): FinanciamentoOperadora => ({
  snapshot_date: '2026-11-06', natureza: 'registro_de_fonte_oficial', limites: 'Duas fontes que não se ligam; ausência não é prova.', raiz: '11111111',
  fontes: { bndes: { fonte: 'BNDES', licenca: 'ODbL', dump_reference: '2026-10-24' }, cgu: { fonte: 'CGU', arquivos: { CEIS: '2026-11-06', CNEP: '2026-11-06' } } }, ...o,
})
const dados = (f: FinanciamentoOperadora) => ({ financiamento: f }) as never

describe('crédito público (BNDES)', () => {
  const f = base({ financiamento: { operacoes_total: 2, contratado_total: 2300000.5, desembolsado_total: 1200000, primeira: '2022-03-10', ultima: '2023-07-01',
    por_ano: [{ ano: '2022', operacoes: 1, contratado: 1500000.5, desembolsado: 1200000 }, { ano: '2023', operacoes: 1, contratado: 800000, desembolsado: 0 }], por_uf: [],
    operacoes: [{ cnpj: '11111111000191', contrato: '1', data: '2022-03-10', contratado: 1500000.5, desembolsado: 1200000, produto: 'BNDES FINAME', instrumento: 'CREDITO', forma: 'DIRETA', uf: 'ES', ibge: '3205309', cnae: 'J6110801', porte: 'PEQUENA', situacao: 'ATIVO', projeto: 'AMPLIACAO DA REDE' }],
    operacoes_omitidas: 0 } })
  it('resume totais nominais, a série por ano e a ressalva da fonte', () => {
    render(<CreditoPublicoBloco dados={dados(f)} snapshot={null} />)
    expect(screen.getByTestId('credito-resumo')).toHaveTextContent('2 operações diretas com o BNDES entre 10/03/2022 e 01/07/2023')
    expect(screen.getByTestId('credito-resumo')).toHaveTextContent('valores nominais, sem correção')
    expect(screen.getAllByRole('row')).toHaveLength(3)
    expect(screen.getByText(/ausência não é prova/)).toBeInTheDocument()
  })
  it('não renderiza sem financiamento', () => {
    const { container } = render(<CreditoPublicoBloco dados={dados(base({}))} snapshot={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('sanções (CEIS e CNEP)', () => {
  const f = base({ sancoes: { vigentes: [san({ sem_prazo: true, fim: null }), san({ cadastro: 'CNEP', codigo: '2', categoria: 'Multa', multa: 36680.49, cnpj: '11111111000272' })], futuras: [], encerradas: [san({ codigo: '3', situacao: 'encerrada', fim: '2021-02-01', inicio: '2019-02-01' })], total: 3 } })
  it('separa vigentes e encerradas, diz "sem prazo informado" e mostra a multa', () => {
    render(<SancoesBloco dados={dados(f)} snapshot={null} />)
    expect(screen.getByTestId('sancoes-resumo')).toHaveTextContent('3 registros no CEIS/CNEP para esta empresa: 2 constando sem fim ou com fim futuro, 1 encerrada')
    expect(screen.getAllByTestId('sancao-item')).toHaveLength(3)
    expect(screen.getByText(/desde 10\/01\/2024, sem data final informada/)).toBeInTheDocument()
    expect(screen.getByText(/R\$ 36\.680/)).toBeInTheDocument()
    expect(screen.getByText(/estabelecimento não matriz/)).toBeInTheDocument()
    expect(screen.getByText(/Constam no cadastro/)).toBeInTheDocument()
    expect(screen.getByText(/Encerradas/)).toBeInTheDocument()
  })
  it('não renderiza sem sanções', () => {
    const { container } = render(<SancoesBloco dados={dados(base({}))} snapshot={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
