// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { EmpresasTelecomUfBloco, PresencaFisicaOperadoraBloco } from './blocos'
import type { CadastroMercadoUf, CadastroOperadora } from '../../types/api'

const meta = { snapshot_date: '2026-11-06', natureza: 'fato_cadastral', fonte: 'Receita Federal', dump_reference: '2026-10', limites: 'Duas fontes que medem coisas diferentes: não prova atendimento.' }
const presenca = (n: number) => Array.from({ length: n }, (_, i) => ({ ibge: String(3200000 + i), municipio: `Cidade ${i}`, uf: 'ES', estabelecimentos: 1, ativos: 1, tem_matriz: i === 0, acessos_fixo: 100 - i, acessos_movel: 0 }))
const operadora = (n = 3): CadastroOperadora => ({
  ...meta, raiz: '11111111', razao_social: 'FIBRA UM LTDA', nome_fantasia: 'FIBRA UM', natureza_juridica: { codigo: '2062', descricao: 'Sociedade Empresária Limitada' }, porte: 'pequeno', capital_social: 50000, simples: true, mei: false,
  matriz: { cnpj: '11111111000191', uf: 'ES', ibge: '3205309', municipio: 'Vitória', situacao: 'ativa', inicio: '2010-01-15', cnae: '6110803', cnae_descricao: 'Serviços de comunicação multimídia - SCM' },
  estabelecimentos: { total: n + 1, ativos: n, baixados: 1, filiais_ativas: n - 1 }, presenca: presenca(n),
  resumo_presenca: { municipios_com_estabelecimento_ativo: n, municipios_com_acessos: n, com_ambos: n - 1, so_acessos: 1, so_estabelecimento: 0 },
})
const montar = (el: JSX.Element) => render(<MemoryRouter>{el}</MemoryRouter>)

describe('presença física da operadora', () => {
  it('mostra a matriz, os estabelecimentos, o cruzamento e a ressalva da fonte', () => {
    montar(<PresencaFisicaOperadoraBloco dados={{ cadastro: operadora() } as never} snapshot={null} />)
    const d = screen.getByTestId('cadastro-dados')
    expect(d).toHaveTextContent('Vitória/ES')
    expect(d).toHaveTextContent('15/01/2010')
    expect(d).toHaveTextContent('empresa de pequeno porte (Simples)')
    expect(d).toHaveTextContent('3 ativos, 1 baixados')
    expect(screen.getByTestId('presenca-resumo')).toHaveTextContent('2 com os dois, 1 só com acessos e 0 só com estabelecimento')
    expect(screen.getByText(/não prova atendimento/)).toBeInTheDocument()
  })

  it('lista os municípios por acessos, com link para a página do município e a marca da matriz', () => {
    montar(<PresencaFisicaOperadoraBloco dados={{ cadastro: operadora() } as never} snapshot={null} />)
    const bloco = screen.getByTestId('presenca-fisica')
    const link = within(bloco).getByRole('link', { name: 'Cidade 0' })
    expect(link).toHaveAttribute('href', '/municipio/3200000')
    expect(link.closest('tr')).toHaveTextContent('(matriz)')
    expect(within(bloco).getAllByRole('row').slice(1)[0]).toHaveTextContent('Cidade 0')           // mais acessos primeiro
  })

  it('corta em 15 municípios e expande sob demanda', () => {
    montar(<PresencaFisicaOperadoraBloco dados={{ cadastro: operadora(20) } as never} snapshot={null} />)
    expect(screen.getAllByRole('row')).toHaveLength(16)                                              // cabeçalho + 15
    fireEvent.click(screen.getByText('mostrar os 20 municípios'))
    expect(screen.getAllByRole('row')).toHaveLength(21)
  })

  it('sem cadastro não renderiza nada', () => {
    const { container } = montar(<PresencaFisicaOperadoraBloco dados={{ cadastro: null } as never} snapshot={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('empresário individual: sem razão social nem nome fantasia na tela', () => {
    const c = { ...operadora(), razao_social: null, nome_fantasia: null, mei: true, simples: true }
    montar(<PresencaFisicaOperadoraBloco dados={{ cadastro: c } as never} snapshot={null} />)
    expect(screen.getByTestId('cadastro-dados')).toHaveTextContent('(MEI)')
    expect(screen.queryByText(/FIBRA UM/)).toBeNull()
  })
})

describe('empresas de telecom da UF', () => {
  const uf: CadastroMercadoUf = { ...meta, uf: 'ES', ativas: 321, entradas_por_ano: [{ ano: 2021, total: 12 }, { ano: 2022, total: 30 }], baixas_por_ano: [{ ano: 2022, total: 4 }, { ano: 2023, total: 9 }],
    resumo: { empresas_no_recorte: 400, operadoras_com_cadastro: 300, empresas_ativas: 321, estabelecimentos_sem_ibge: 0 } }

  it('mostra as ativas e uma linha por ano, do mais recente ao mais antigo, com abertas e baixadas', () => {
    montar(<EmpresasTelecomUfBloco dados={{ cadastro: uf } as never} snapshot={null} />)
    const bloco = screen.getByTestId('empresas-telecom-uf')
    expect(bloco).toHaveTextContent('321 empresas de telecom ativas em ES')
    const linhas = within(bloco).getAllByRole('row').slice(1).map((r) => r.textContent ?? '')
    expect(linhas).toHaveLength(3)
    expect(linhas[0]).toMatch(/^2023\s*0\s*9/)
    expect(linhas[1]).toMatch(/^2022\s*30\s*4/)
    expect(linhas[2]).toMatch(/^2021\s*12\s*0/)
  })

  it('sem cadastro não renderiza nada', () => {
    const { container } = montar(<EmpresasTelecomUfBloco dados={{} as never} snapshot={null} />)
    expect(container.innerHTML).toBe('')
  })
})
