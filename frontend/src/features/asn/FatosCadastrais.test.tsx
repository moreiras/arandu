// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { AsnCadastro, AsnRecuperacao } from '../../types/api'
import { FatosCadastrais } from './CabecalhoAsn'

const cad: AsnCadastro = {
  cnpj: '01264994000116', razao_social: 'Unilink Redes de Informacoes Ltda', descricao_situacao_cadastral: 'BAIXADA',
  descricao_motivo_situacao_cadastral: 'EXTINÇÃO DE ME/EPP', cnae_fiscal_descricao: 'Desenvolvimento de programas de computador sob encomenda',
  municipio: 'Barueri', uf: 'SP', codigo_municipio_ibge: 3505708, lido_em: '2026-06-12T10:00:00+00:00', fonte: 'Receita Federal', selo: 'fato',
}
const rec: AsnRecuperacao = { asn: 22351, inicio: '2026-09-01', fim: '2026-11-30', primeira_vez_visto: '2026-06-28', fonte: 'Registro.br', selo: 'fato' }
const montar = (c?: AsnCadastro | null, r?: AsnRecuperacao | null) => render(<MemoryRouter><FatosCadastrais cadastro={c} recuperacao={r} /></MemoryRouter>)

describe('fatos cadastrais e de numeração do ASN (PT-26 / ASN 5.3)', () => {
  it('CNPJ baixado: situação, data da leitura, motivo da Receita e a ressalva; município como link; sem causa própria', () => {
    montar(cad)
    const sit = screen.getByTestId('asn-situacao-cadastral')
    expect(sit.textContent).toMatch(/Situação cadastral do CNPJ na Receita: baixada \(cadastro lido em 2026-06-12\) \(fato\)/)
    expect(sit.textContent).toMatch(/Motivo informado pela Receita: extinção de me\/epp/)
    expect(sit.textContent).toMatch(/não prova que o AS esteja sem uso/)
    expect(screen.getByRole('link', { name: 'Barueri (SP)' })).toHaveAttribute('href', '/municipio/3505708')
    expect(screen.getByText(/desenvolvimento de programas de computador/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/irregular|omi[s]s|infra[çc]|fraude/i)
  })

  it('CNPJ ativo: nenhum selo de situação', () => {
    montar({ ...cad, descricao_situacao_cadastral: 'ATIVA', descricao_motivo_situacao_cadastral: '' })
    expect(screen.queryByTestId('asn-situacao-cadastral')).toBeNull()
  })

  it('ASN em recuperação: janela e a frase de que a lista não informa o motivo', () => {
    montar(null, rec)
    expect(screen.getByTestId('asn-recuperacao').textContent).toMatch(/ASN em recuperação pelo Registro\.br \(janela 2026-09-01 a 2026-11-30\) \(fato\)\. A lista não informa o motivo\./)
  })

  it('sem cadastro nem recuperação não mostra nada', () => {
    expect(montar(null, null).container.firstChild).toBeNull()
  })
})
