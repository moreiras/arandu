// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { UfCtx } from '../contexto'
import { DeclaracaoSiciUfBloco } from './DeclaracaoSiciUfBloco'

const ctx = (indicadores: UfCtx['indicadores']) => ({ uf: 'AM', indicadores } as unknown as UfCtx)
const ind = {
  mes_referencia: '2026-09', metodologia: '/fontes', acessos: 1000, n_operadoras: 211, hhi: 3000, var_mm_pct: 1.25, var_aa_pct: 14.47,
  sem_declaracao: { cnpjs_sem_declaracao: 307, com_usuarios_apnic: 32, sem_usuarios: 12, nao_comparavel: 263, usuarios_apnic: 177439 },
}

describe('declaração de acessos na UF (PT-26 / UF 5.2)', () => {
  it('AM: contagens que fecham em 307 (32 + 12 + 263), sem nomes, com link para a lista da UF e a regra vigente', () => {
    render(<MemoryRouter><DeclaracaoSiciUfBloco dados={ctx(ind)} snapshot="2026-11-22" /></MemoryRouter>)
    const bloco = screen.getByTestId('declaracao-sici-uf')
    expect(bloco.textContent).toContain('211 CNPJs declararam acessos na UF em 2026-09')
    expect(bloco.textContent).toContain('+1,25% no mês')
    expect(bloco.textContent).toContain('+14,47% em 12 meses')
    expect(bloco.textContent).toContain('307 CNPJs com outorga SCM e sede na UF sem declaração em 2026-09')
    expect(bloco.textContent).toContain('32 com ASN ligado ao CNPJ e 100 ou mais usuários estimados (APNIC), somando 177.439')
    expect(bloco.textContent).toContain('12 com ASN ligado ao CNPJ e menos de 100')
    expect(bloco.textContent).toContain('263 sem ASN ligado ao CNPJ')
    expect(32 + 12 + 263).toBe(307)
    expect(screen.getByRole('link', { name: /Ver a lista/ })).toHaveAttribute('href', '/operadoras?visao=sem-declaracao&uf=AM')
    expect(bloco.textContent).toMatch(/Resolução Anatel nº 774\/2025/)
    expect(bloco.textContent).toMatch(/não indica causa nem intenção/)
    expect(bloco.textContent).not.toMatch(/omi[s]s|irregular|infra[çc]/i)
  })

  it('sem o agregado de sem declaração só mostra o que foi declarado', () => {
    render(<MemoryRouter><DeclaracaoSiciUfBloco dados={ctx({ ...ind, sem_declaracao: undefined })} snapshot={null} /></MemoryRouter>)
    expect(screen.queryByText(/sem declaração em 2026-09:/)).toBeNull()
    expect(screen.queryByRole('link', { name: /Ver a lista/ })).toBeNull()
  })
})
