// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** PT-15 / IXPS-E5, IXP-E6: os usuários por PTT são rotulados como alcançáveis e não aditivos (a soma por PTT não é o total). */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DestaqueBloco } from './blocks/DestaqueBloco'
import { rotuloDe } from '../../lib/universos'
import type { PttCtx } from './contexto'

const fontes = import.meta.glob(['../../components/tables/IXPTable.tsx', '../../pages/IXPs.tsx'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const fonte = (fim: string) => Object.entries(fontes).find(([a]) => a.endsWith(fim))![1]

describe('usuários por PTT não somam', () => {
  const dados = { estUsers: { estimated_users: 57933013 }, usuariosBrTotal: 161288456, par: 280, brOriginUnion: 250, cbrAsns: 80, v6: null, v6idx: null, v4: null, v4idx: null } as unknown as PttCtx

  it('o destaque do PTT rotula como alcançáveis (IPv4), diz que não somam entre PTTs e dá o total do país como referência', () => {
    render(<DestaqueBloco dados={dados} snapshot="2026-11-22" />)
    expect(screen.getByText(rotuloDe('usuariosPtt'))).toBeInTheDocument()
    expect(screen.getByText(/não some entre PTTs: o mesmo usuário conta em cada PTT onde o ASN aparece/)).toBeInTheDocument()
    expect(screen.getByText(/País: 161\.288\.456 usuários estimados \(APNIC\)/)).toBeInTheDocument()
    expect(screen.getByText('ASNs no cadastro do PTT')).toBeInTheDocument()
  })

  it('a coluna da tabela de PTTs e o KPI de /ixps dizem que não somam, sem depender de hover', () => {
    expect(fonte('/IXPTable.tsx')).toMatch(/label="Usuários alcançáveis \(est\., não somam\)"/)
    const ixps = fonte('/IXPs.tsx')
    expect(ixps).toMatch(/rotuloDe\('usuariosIx'\)/)
    expect(ixps).toMatch(/a soma por PTT, na tabela, não é este total/)
    expect(rotuloDe('usuariosIx')).toMatch(/sem dupla contagem/)
  })
})
