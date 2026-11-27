// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { IndicadoresBloco } from './IndicadoresBloco'

const base = { mes_referencia: '2026-09', metodologia: '/fontes', acessos: 100, n_operadoras: 3, hhi: 4000 }
const montar = (i: any) => render(<MemoryRouter><IndicadoresBloco dados={{ ibge: '1', proximos: [], carregandoPtts: false, indicadores: i }} {...({} as any)} /></MemoryRouter>)

describe('ganho e perda com mudança de CNPJ provável (PT-26 / MUN 5.1 d)', () => {
  it('diz que é inferido, mostra os dois CNPJs e que a conta soma a marca', () => {
    montar({ ...base, ganho_aa: { cnpj: '2', empresa: 'LIGGA', acessos: 5, cnpjs: ['1', '2'] },
      mudancas_cnpj: [{ marca: 'Ligga', de_cnpj: '04368865000166', para_cnpj: '65649511000184', acessos_de: -120008, acessos_para: 125717 }] })
    const t = screen.getByTestId('mudanca-cnpj').textContent!
    expect(t).toMatch(/Ligga: mudança de CNPJ provável \(inferido\): 04\.368\.865\/0001-66/)
    expect(t).toMatch(/→ 65\.649\.511\/0001-84/)
    expect(t).toMatch(/não prova sucessão/)
    expect(document.body.textContent).toMatch(/soma de 2 CNPJs da mesma marca \(inferido\)/)
  })
  it('sem mudança, nada extra', () => {
    montar({ ...base, perda_aa: { cnpj: '1', empresa: 'X', acessos: -10 } })
    expect(screen.queryByTestId('mudanca-cnpj')).toBeNull()
    expect(document.body.textContent).not.toMatch(/soma de/)
  })
})
