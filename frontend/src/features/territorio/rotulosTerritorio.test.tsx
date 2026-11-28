// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** PT-15: usuários por UF da sede (UF-E3), os dois "não vistos" (UF-E4), denominador da banda larga fixa (USO-E5) e penetração acima de 1 (MUNS-E3). */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { DemandaOfertaUfBloco } from '../uf/blocks/DemandaOfertaUfBloco'
import { PenetracaoBloco } from './PenetracaoBloco'

const fontes = import.meta.glob(['../uf/blocks/UsuariosSedeUfBloco.tsx', '../estados/CartogramaUfs.tsx', '../../pages/UsoInternetPage.tsx', '../../pages/MunicipiosPage.tsx'],
  { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const fonte = (fim: string) => Object.entries(fontes).find(([a]) => a.endsWith(fim))![1]

describe('usuários por UF dizem "sede" (UF-E3)', () => {
  it('o rótulo diz que é a UF da sede do ASN e que não é a população conectada', () => {
    expect(fonte('/UsuariosSedeUfBloco.tsx')).toMatch(/Usuários estimados em ASNs sediados na UF/)
    expect(fonte('/UsuariosSedeUfBloco.tsx')).toMatch(/não é a população conectada/)
    expect(fonte('/CartogramaUfs.tsx')).toMatch(/Usuários \(sede da rede\)/)
    expect(fonte('/CartogramaUfs.tsx')).toMatch(/Não é a população conectada nem o uso de Internet na UF/)
  })
})

describe('os dois "não vistos" têm nomes distintos pela base (UF-E4)', () => {
  it('a penetração fala em taxa de Internet da PNAD e a demanda × oferta, em TIC; "não visto" deixa de ser nome', () => {
    render(<PenetracaoBloco t={{ penetracao: 0.9, nao_visto: 506095, nao_visto_pct: 0.406, mes_referencia_sici: '2026-09', censo_ano: 2022 } as never} rotuloTerritorio="o Amazonas" />)
    expect(screen.getByText(/Domicílios sem acesso fixo de pessoa física \(estimativa, taxa de Internet da PNAD\)/)).toBeInTheDocument()
    expect(screen.getByText(/506\.095/)).toBeInTheDocument()
    expect(screen.queryByText(/Mercado não visto/)).toBeNull()
    const linha = { classe: 'oferta_abaixo_da_demanda', domicilios_projetados: 1, oferta_acessos_pf: 1, demanda_domicilios: 10, razao: 0.9, nao_visto: 77353 }
    const d = { demanda_oferta: linha, comparacao: { regiao: null, brasil: linha }, regiao: 'Norte', tic_edicao: 2025, mes_referencia_sici: '2026-09', limites: '' }
    render(<MemoryRouter><DemandaOfertaUfBloco dados={{ demandaOferta: d, uf: 'AM' } as never} snapshot="2026-11-22" /></MemoryRouter>)
    expect(screen.getByText('Domicílios sem acesso fixo de PF (estimativa, TIC)')).toBeInTheDocument()
    expect(screen.getAllByText(/77\.353/).length).toBeGreaterThan(0)
    expect(screen.getByTestId('como-ler')).toHaveTextContent('duas estimativas de domicílios sem acesso fixo de pessoa física, com bases diferentes')
  })
})

describe('denominador escrito e penetração acima de 1 (USO-E5, MUNS-E3)', () => {
  it('a página de uso mostra a definição do indicador e diz que a banda larga fixa não tem o denominador da tabela A5', () => {
    const uso = fonte('/UsoInternetPage.tsx')
    expect(uso).toMatch(/data-testid="definicao-indicador"/)
    expect(uso).toMatch(/Não é o mesmo denominador da tabela A5 do Cetic\.br/)
  })

  it('a lente de penetração traz o "Como ler": acima de 1 é acesso, não domicílio, e a causa não é apurada', () => {
    const mun = fonte('/MunicipiosPage.tsx')
    expect(mun).toMatch(/<FontesEDatas[^]*lente === 'penetracao' && \(/)
    expect(mun).not.toMatch(/<ComoLer/)
    expect(mun).toMatch(/Acesso não é domicílio/)
    expect(mun).toMatch(/a causa não é apurada aqui/)
  })
})
