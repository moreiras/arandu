// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PeeringDbBloco } from './PeeringDbBloco'

const montar = (doc: object) => render(<PeeringDbBloco {...({ dados: { doc } } as any)} />)

describe('bloco PeeringDB do ASN (ASN-E2)', () => {
  it('lê os campos que a API entrega (info_*, policy_general) e põe o declarado ao lado do observado', () => {
    montar({ asn: 13357, pdb_registered: true, global_prefixes_v4_count: 12, global_prefixes_v6_count: 1,
      pdb: { name: 'Rede Exemplo', info_type: 'NSP', info_traffic: '5-10Gbps', info_ratio: 'Balanced', policy_general: 'Selective', info_prefixes4: 2046, info_prefixes6: 102 } })
    const linhas = Array.from(screen.getByTestId('peeringdb-cadastro').querySelectorAll('tr')).map((tr) => tr.textContent)
    expect(linhas.length).toBeGreaterThan(0)
    expect(linhas).toEqual([
      'Tipo de redeNSP', 'Tráfego5-10Gbps', 'ProporçãoBalanced', 'Política de peeringSelective',
      'Prefixos IPv6102 declarados · 1 na tabela global', 'Prefixos IPv42.046 declarados · 12 na tabela global',
    ])
  })

  it('cadastro sem campo preenchido diz isso em vez de uma tabela vazia', () => {
    montar({ asn: 1, pdb_registered: true, pdb: { name: 'X' } })
    expect(screen.queryByTestId('peeringdb-cadastro')).toBeNull()
    expect(screen.getByText(/sem tipo, política nem prefixos preenchidos/)).toBeTruthy()
  })

  it('sem cadastro mostra o selo', () => {
    montar({ asn: 7890, pdb_registered: false, pdb: null })
    expect(screen.getByText('não cadastrado')).toBeTruthy()
  })
})
