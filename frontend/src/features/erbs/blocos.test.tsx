// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { ErbsMunicipioBloco, ErbsOperadoraBloco, ErbsUfBloco } from './blocos'
import type { ErbsMeta, ErbsMunicipio, ErbsOperadora, ErbsUf } from '../../types/api'

const meta: ErbsMeta = { natureza: 'cadastro_licenciamento', fonte: 'Anatel', data_arquivo: 'Sun, 01 Nov 2026 10:52:35 GMT', limites: 'Não é cobertura nem estação em operação.', snapshot_date: '2026-11-01' }
const g = { '2G': 1, '3G': 2, '4G': 5, '5G': 3 }
const brasil = { estacoes: 1000, municipios: 20, municipios_com_estacao: 18, municipios_com_5g: 9, geracoes: g, operadoras: 4 }
const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{el}</MemoryRouter></QueryClientProvider>,
)

describe('estações do SMP licenciadas', () => {
  it('município: mostra estações por geração e operadora e avisa que é cadastro, não cobertura', () => {
    const erbs: ErbsMunicipio = { ...meta, estacoes: 7, geracoes: g, por_10mil_hab: 3.5, operadoras: [{ cnpj: '02558157000162', marca: 'VIVO', estacoes: 4 }, { cnpj: null, marca: 'XYZ', estacoes: 3 }],
      uf: 'SP', comparacao_uf: { estacoes: 100, municipios: 10, municipios_com_estacao: 9, municipios_com_5g: 4, geracoes: g, operadoras: 3 }, brasil }
    montar(<ErbsMunicipioBloco dados={{ ibge: '1', erbs } as never} snapshot={null} />)
    expect(screen.getByText('estações licenciadas')).toBeTruthy()
    expect(screen.getByText('VIVO').getAttribute('href')).toBe('/operadora/02558157000162')
    expect(screen.getByText('XYZ').getAttribute('href')).toBeNull()
    expect(screen.getByText(/Não é cobertura nem estação em operação/)).toBeTruthy()
    expect(screen.getByText(/9 de 10 municípios têm estação/)).toBeTruthy()
  })

  it('município sem estação mostra zero e não afirma que não há serviço', () => {
    const erbs: ErbsMunicipio = { ...meta, estacoes: 0, geracoes: { '2G': 0, '3G': 0, '4G': 0, '5G': 0 }, por_10mil_hab: null, operadoras: [], uf: 'SP', comparacao_uf: null, brasil }
    montar(<ErbsMunicipioBloco dados={{ ibge: '1', erbs } as never} snapshot={null} />)
    expect(screen.getByText(/pode vir de estações de municípios vizinhos/)).toBeTruthy()
  })

  it('UF: lista os municípios e filtra por geração', async () => {
    let geracaoPedida: string | null = 'x'
    server.use(http.get('*/api/v1/erbs/municipios', ({ request }) => {
      geracaoPedida = new URL(request.url).searchParams.get('geracao')
      return HttpResponse.json({ ...meta, geracao: geracaoPedida, uf: 'SP', ordem: 'estacoes', total: 1, limit: 10, offset: 0,
        items: [{ ibge: '3550308', nome: 'São Paulo', uf: 'SP', estacoes: 50, estacoes_2g: 5, estacoes_3g: 6, estacoes_4g: 40, estacoes_5g: 30, por_10mil_hab: 4.2, operadoras: 3, operadora_principal: 'VIVO' }] })
    }))
    const erbs: ErbsUf = { ...meta, uf: 'SP', resumo: { estacoes: 100, municipios: 10, municipios_com_estacao: 9, municipios_com_5g: 4, geracoes: g, operadoras: 3 }, brasil }
    montar(<ErbsUfBloco dados={{ uf: 'SP', erbs } as never} snapshot={null} />)
    await waitFor(() => expect(screen.getByText('São Paulo').getAttribute('href')).toBe('/municipio/3550308'))
    expect(geracaoPedida).toBeNull()
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '5G' } })
    await waitFor(() => expect(geracaoPedida).toBe('5G'))
    await waitFor(() => expect(screen.getByText('Estações 5G')).toBeTruthy())
  })

  it('operadora: total, participação no país e tipo do 5G', () => {
    const erbs: ErbsOperadora = { ...meta, cnpj: '1', marca: 'VIVO', entidade: 'TELEFONICA', estacoes: 250, municipios: 8, ufs: 3, geracoes: g, tipo_5g: { SA: 10, NSA: 5 }, brasil: { estacoes: 1000, municipios_com_estacao: 18 } }
    montar(<ErbsOperadoraBloco dados={{ erbs } as never} snapshot={null} />)
    expect(screen.getByText(/25,0% das estações do SMP no país/)).toBeTruthy()
    expect(screen.getByText(/SA 10 · NSA 5/)).toBeTruthy()
  })

  it('sem o bloco não renderiza nada', () => {
    const { container } = montar(<ErbsOperadoraBloco dados={{} as never} snapshot={null} />)
    expect(container.innerHTML).toBe('')
  })
})
