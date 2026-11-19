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
import { FustMunicipioBloco, FustUfBloco } from './blocos'
import type { FustMeta, FustMunicipio, FustUf } from '../../types/api'

const meta: FustMeta = { natureza: 'cadastro_regulatorio', fonte: 'Anatel', data_arquivo: 'Mon, 02 Nov 2026 10:30:15 GMT', limites: 'Não identifica a empresa executora.', snapshot_date: '2026-11-02' }
const nomes = { '1.1': 'Conectividade para Escolas Públicas', '2.6': 'Conectividade para UBS' }
const resumoUf = { compromissos: 100, atendidos: 40, a_vencer: 30, em_apuracao: 30, investimento: 5_000_000, municipios: 10, municipios_com_compromisso: 9, programas: { '1.1': 80, '2.6': 20 } }
const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{el}</MemoryRouter></QueryClientProvider>,
)

describe('FUST', () => {
  it('município: situação, programas, valor previsto e aviso de que não há executora', () => {
    const fust: FustMunicipio = { ...meta, compromissos: 7, atendidos: 3, a_vencer: 2, em_apuracao: 2, investimento: 120_000, programas: { '1.1': 5, '2.6': 2 }, tipos: {}, por_10mil_hab: 3.5,
      uf: 'SP', comparacao_uf: resumoUf, programas_nomes: nomes }
    montar(<FustMunicipioBloco dados={{ ibge: '1', fust } as never} snapshot={null} />)
    expect(screen.getByText('compromissos')).toBeTruthy()
    expect(screen.getByText(/1\.1 · Conectividade para Escolas Públicas/)).toBeTruthy()
    expect(screen.getByText(/Não identifica a empresa executora/)).toBeTruthy()
    expect(screen.getByText(/9 de 10 municípios têm compromisso/)).toBeTruthy()
  })

  it('município sem compromisso mostra zero', () => {
    const fust: FustMunicipio = { ...meta, compromissos: 0, atendidos: 0, a_vencer: 0, em_apuracao: 0, investimento: 0, programas: {}, tipos: {}, uf: 'SP', comparacao_uf: null, programas_nomes: nomes }
    montar(<FustMunicipioBloco dados={{ ibge: '1', fust } as never} snapshot={null} />)
    expect(screen.getByText(/Nenhum compromisso do FUST registrado/)).toBeTruthy()
  })

  it('UF: lista os municípios e filtra por programa', async () => {
    let programaPedido: string | null = 'x'
    server.use(http.get('*/api/v1/fust/municipios', ({ request }) => {
      programaPedido = new URL(request.url).searchParams.get('programa')
      return HttpResponse.json({ ...meta, uf: 'SP', programa: programaPedido, ordem: 'compromissos', total: 1, limit: 10, offset: 0,
        items: [{ ibge: '3550308', nome: 'São Paulo', uf: 'SP', compromissos: 50, atendidos: 20, a_vencer: 15, em_apuracao: 15, investimento: 900_000, por_10mil_hab: 1.2, programas: ['1.1'] }] })
    }))
    const fust: FustUf = { ...meta, uf: 'SP', resumo: resumoUf, brasil: { ...resumoUf, programas: 2, editais: 3 }, programas_nomes: nomes }
    montar(<FustUfBloco dados={{ uf: 'SP', fust } as never} snapshot={null} />)
    await waitFor(() => expect(screen.getByText('São Paulo').getAttribute('href')).toBe('/municipio/3550308'))
    expect(programaPedido).toBeNull()
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '2.6' } })
    await waitFor(() => expect(programaPedido).toBe('2.6'))
  })

  it('sem o bloco não renderiza nada', () => {
    const { container } = montar(<FustMunicipioBloco dados={{} as never} snapshot={null} />)
    expect(container.innerHTML).toBe('')
  })
})
