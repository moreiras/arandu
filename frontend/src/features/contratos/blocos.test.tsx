// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ContratosMunicipioBloco, ContratosOperadoraBloco } from './blocos'
import type { ContratosCabecalho, ContratosMunicipio, ContratosOperadora } from '../../types/api'

const cab: ContratosCabecalho = {
  snapshot_date: '2026-11-10', coletado_em: '2026-11-10T03:00:00+00:00', natureza: 'fato_publicado', licenca: 'dados abertos (Lei 12.527/2011, LAI; PNCP, Lei 14.133/2021, art. 174); sem licença nominal publicada',
  aviso: 'Cada linha é um resultado de item publicado no PNCP; não é, por si, contrato assinado nem pagamento.', limites: 'Só a Lei 14.133; só a matriz.',
  cobertura: { raizes_no_universo: 20900, raizes_faixa_a: 9000, raizes_com_leitura: 4200, raizes_sem_leitura: 16700, raizes_com_resultado: 800, raizes_incompletas: 0, leitura_mais_antiga: '2026-11-08', leitura_mais_recente: '2026-11-10', janela_inicio: '2021-04-01',
    itens: 5000, contratacoes: 1500, contratacoes_com_detalhe: 600, contratacoes_com_municipio: 1500, municipios_com_contratacao: 300 },
  fonte: { nome: 'Compras.gov.br (dados abertos), espelho do PNCP, Lei 14.133', url: 'https://dadosabertos.compras.gov.br', licenca: 'dados abertos (Lei 12.527/2011, LAI; PNCP, Lei 14.133/2021, art. 174); sem licença nominal publicada', consultado_em: '2026-11-10' },
}
const op = (o: Partial<ContratosOperadora>): ContratosOperadora => ({
  ...cab, raiz: '11222333', nome: 'FIBRA UM LTDA', cnpj_consultado: '11222333000181', faixa: 'A', lida_em: '2026-11-08', idade_dias: 2, desde: '2021-04-01', incompleto: false,
  resultado: 'com_resultado', itens: 3, contratacoes: 2, itens_cancelados: 1, orgaos: 2, valor_homologado: 255500.25, primeiro_resultado: '2025-11-20', ultimo_resultado: '2026-08-03', contratacoes_detalhadas: 1,
  por_ano: [{ ano: '2025', itens: 1, contratacoes: 1, valor: 250000 }, { ano: '2026', itens: 2, contratacoes: 1, valor: 5500.25 }],
  por_uf: [{ uf: 'DF', itens: 1, contratacoes: 1, valor: 250000 }, { uf: 'RJ', itens: 2, contratacoes: 1, valor: 5500.25 }],
  por_esfera: [{ esfera: 'federal', itens: 1, contratacoes: 1, valor: 250000 }, { esfera: 'nao_detalhada', itens: 2, contratacoes: 1, valor: 5500.25 }],
  recentes: [{ contratacao: 'c2', data: '2026-08-03', orgao: 'UNIDADE DE COMPRA X', orgao_detalhado: false, esfera: null, uf: 'RJ', municipio: 'Tupãnópolis', ibge: '9900002', modalidade: null, objeto: null, itens: 2, valor: 5500.25 },
             { contratacao: 'c1', data: '2025-11-20', orgao: 'ORGAO FEDERAL', orgao_detalhado: true, esfera: 'federal', uf: 'DF', municipio: 'Brasília', ibge: '5300108', modalidade: 'Pregão - Eletrônico', objeto: 'Rede de dados', itens: 1, valor: 250000 }],
  ...o,
})

describe('contratos públicos da operadora', () => {
  it('resume com a data da leitura, sem adjetivo, e diz que o item cancelado fica fora da soma', () => {
    render(<ContratosOperadoraBloco dados={{ contratos: op({}) } as never} snapshot={null} />)
    const r = screen.getByTestId('contratos-resumo')
    expect(r).toHaveTextContent('lidos em 08/11/2026 (há 2 dias)')
    expect(r).toHaveTextContent('3 itens em 2 contratações de 2 órgãos, entre 20/11/2025 e 03/08/2026')
    expect(r).toHaveTextContent('1 item cancelado fica fora da soma')
    expect(screen.getByTestId('contratos-aviso')).toHaveTextContent('não é, por si, contrato assinado nem pagamento')
  })
  it('esfera sem detalhe aparece como "ainda não detalhada" e a unidade de compra é rotulada como tal', () => {
    render(<ContratosOperadoraBloco dados={{ contratos: op({}) } as never} snapshot={null} />)
    expect(screen.getByTestId('contratos-por-esfera')).toHaveTextContent('Ainda não detalhada')
    expect(screen.getByTestId('contratos-recentes')).toHaveTextContent('UNIDADE DE COMPRA X (unidade de compra)')
  })
  it('declara cobertura do rodízio e a licença dos dados abertos', () => {
    render(<ContratosOperadoraBloco dados={{ contratos: op({}) } as never} snapshot={null} />)
    expect(screen.getByTestId('contratos-cobertura')).toHaveTextContent('4.200 de 20.900 empresas do universo de telecom já lidas')
    expect(screen.getByTestId('contratos-cobertura')).toHaveTextContent('600 de 1.500 contratações lidas com detalhe')
    expect(screen.getByTestId('contratos-fonte')).toHaveTextContent('licença dos dados: dados abertos (Lei 12.527/2011, LAI;')
  })
  it('raiz lida sem resultado diz isso com a data (ausência não é zero) e não mostra tabelas', () => {
    render(<ContratosOperadoraBloco dados={{ contratos: op({ resultado: 'sem_resultado_na_consulta', itens: 0, contratacoes: 0, por_ano: undefined, por_uf: undefined, por_esfera: undefined, recentes: undefined }) } as never} snapshot={null} />)
    expect(screen.getByTestId('contratos-vazio')).toHaveTextContent('Lido em 08/11/2026')
    expect(screen.getByTestId('contratos-vazio')).toHaveTextContent('Isso não exclui contratos em nome de filial')
    expect(screen.queryByTestId('contratos-por-ano')).toBeNull()
  })
  it('avisa quando a leitura foi cortada pelo limite de páginas', () => {
    render(<ContratosOperadoraBloco dados={{ contratos: op({ incompleto: true }) } as never} snapshot={null} />)
    expect(screen.getByTestId('contratos-resumo')).toHaveTextContent('o total pode ser maior')
  })
  it('não renderiza sem a resposta (204)', () => {
    const { container } = render(<ContratosOperadoraBloco dados={{ contratos: null } as never} snapshot={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('contratos públicos no município', () => {
  const m: ContratosMunicipio = {
    ...cab, ibge: '9900001', criterio_municipio: 'município do órgão comprador (detalhe da contratação ou unidade de compra), não o local de entrega', municipio: 'Arandurápolis', uf: 'SP', itens: 2, contratacoes: 2, valor: 251500,
    fornecedores: [{ raiz: '11222333', cnpj: '11222333000181', nome: 'FIBRA UM LTDA', itens: 2, contratacoes: 2, valor: 251500 }, { raiz: '44555666', cnpj: null, nome: null, itens: 0, contratacoes: 0, valor: 0 }],
  }
  it('diz que o município é o do órgão e que a ordem não é ranking, e liga a operadora pelo CNPJ de matriz', () => {
    render(<MemoryRouter><ContratosMunicipioBloco dados={{ contratos: m } as never} snapshot={null} /></MemoryRouter>)
    expect(screen.getByTestId('contratos-aviso')).toHaveTextContent('Município do órgão comprador')
    expect(screen.getByTestId('contratos-aviso')).toHaveTextContent('não é ranking de mercado nem prova de que a operadora atende o município')
    expect(screen.getByTestId('contratos-municipio-resumo')).toHaveTextContent('Órgãos sediados em Arandurápolis/SP: 2 itens em 2 contratações')
    expect(screen.getByText('FIBRA UM LTDA').getAttribute('href')).toBe('/operadora/11222333000181')
    expect(screen.getByTestId('contratos-cobertura')).toHaveTextContent('Quem não aparece pode ainda não ter sido lido')
  })
  it('não renderiza sem a resposta (204)', () => {
    const { container } = render(<MemoryRouter><ContratosMunicipioBloco dados={{ contratos: null } as never} snapshot={null} /></MemoryRouter>)
    expect(container).toBeEmptyDOMElement()
  })
})
