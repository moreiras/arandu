// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Cabeçalho da operadora: duas linhas de grupo com origens diferentes (OPERADORA-E10, D5). */
import { MemoryRouter } from 'react-router-dom'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { GrupoSocietarioResumo } from '../../types/api'
import { CabecalhoOperadora } from './CabecalhoOperadora'

vi.mock('../../components/ContactsReveal', () => ({ ContactsReveal: () => null }))
vi.mock('../../components/entidade/AcoesEntidade', () => ({ AcoesEntidade: () => null }))

const resumo = (o: Partial<GrupoSocietarioResumo> = {}): GrupoSocietarioResumo => ({
  grupo_id: 'grp_04601397', classificacao: 'parcial', tamanho: 2, nome: 'BRISANET', nome_regra: 'marca_curada', nome_regra_texto: 'marca curada que cobre as raízes de CNPJ do grupo', nome_base: 'b',
  integrantes: [{ cnpj: '44250088000101', empresa: '4J TELECOM', has_scm: true }], integrantes_total: 1, ...o,
})

const montar = (p: Partial<React.ComponentProps<typeof CabecalhoOperadora>> = {}) => render(
  <MemoryRouter>
    <CabecalhoOperadora nome="OI S.A." grupo="OI" hasScm hasSmp={false} hasStfc={false} hasSeac={false} cnpjFinal="76535764000143" grupoCnpjs={[{ cnpj: '53420564000101', empresa: 'CLIENT CO', has_scm: true }]}
      fetchContacts={async () => ({})} asns={[]} {...p} />
  </MemoryRouter>,
)

describe('cabeçalho da operadora: grupo no SICI e grupo societário', () => {
  it('duas linhas rotuladas, cada uma com a sua origem e os seus integrantes', () => {
    montar({ grupoSocietario: resumo() })
    const sici = screen.getByTestId('grupo-sici')
    expect(sici).toHaveTextContent('Grupo no SICI (declarado à Anatel):')
    expect(within(sici).getByRole('link', { name: 'CLIENT CO' })).toHaveAttribute('href', '/operadora/53420564000101')
    const soc = screen.getByTestId('grupo-societario')
    expect(soc).toHaveTextContent('Grupo societário (inferido do quadro societário da Receita):')
    expect(within(soc).getByRole('link', { name: /BRISANET \(2 empresas\)/ })).toHaveAttribute('href', '/grupo/grp_04601397')
    expect(within(soc).getByRole('link', { name: '4J TELECOM' })).toHaveAttribute('href', '/operadora/44250088000101')
  })

  it('empresa sozinha no quadro societário: diz isso e leva ao grupo de uma empresa só', () => {
    montar({ grupoSocietario: resumo({ grupo_id: 'ind_76535764', classificacao: 'individual', tamanho: 1, nome: 'OI S.A.', integrantes: [], integrantes_total: 0 }) })
    const soc = screen.getByTestId('grupo-societario')
    expect(soc).toHaveTextContent('só este CNPJ, sem ligação societária com outra operadora')
    expect(within(soc).getByRole('link', { name: 'ver o grupo' })).toHaveAttribute('href', '/grupo/ind_76535764')
    expect(within(screen.getByTestId('grupo-sici')).getByRole('link', { name: 'CLIENT CO' })).toBeInTheDocument()       // as duas origens divergem (Oi)
  })

  it('grupo OUTROS do SICI não gera integrantes; o societário continua aparecendo', () => {
    montar({ grupo: 'OUTROS', grupoCnpjs: [], grupoSocietario: resumo() })
    const sici = screen.getByTestId('grupo-sici')
    expect(sici).toHaveTextContent('nenhum grupo declarado')
    expect(within(sici).queryAllByRole('link')).toHaveLength(0)
    expect(within(screen.getByTestId('grupo-societario')).getByRole('link', { name: /BRISANET/ })).toBeInTheDocument()
  })

  it('mostra quantos integrantes ficaram de fora da lista e o estado de carga', () => {
    montar({ grupoSocietario: resumo({ integrantes_total: 15 }) })
    expect(screen.getByTestId('grupo-societario')).toHaveTextContent('e mais 14')
  })

  it('sem resposta ainda: carregando; sem quadro societário: diz que não há informação', () => {
    const { unmount } = montar({ grupoSocietarioCarregando: true })
    expect(screen.getByTestId('grupo-societario')).toHaveTextContent('carregando')
    unmount()
    montar({ grupoSocietario: null })
    expect(screen.getByTestId('grupo-societario')).toHaveTextContent('sem informação do quadro societário neste snapshot')
  })
})
