// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CeticUfBloco } from './CeticUfBloco'
import type { UfCtx } from '../contexto'
import type { CeticEstimativasUf, CeticGrupo } from '../../../types/api'

const grupo = (nome: string, tipo: CeticGrupo['tipo'], p: number, margem: number, extra: Partial<CeticGrupo['indicadores']['internet']> = {}): CeticGrupo => ({
  tipo, nome, n: tipo === 'uf' ? 1068 : 5000, domicilios: 1000000,
  indicadores: { internet: { proporcao: p, erro_padrao: margem / 1.96, margem, precisao: 'adequada', ...extra } },
})
const cetic: CeticEstimativasUf = {
  natureza: 'estimativa_arandurape', pesquisa: 'TIC Domicílios', edicao: 2025, fonte: 'Estimativa do Arandurapé a partir dos microdados da TIC Domicílios 2025 (Cetic.br|NIC.br)',
  licenca: 'CC BY 4.0', pagina: 'https://cetic.br/pt/pesquisa/domicilios/microdados/', coletado_em: null, snapshot_date: '2026-11-01',
  aviso: 'Estimativa do Arandurapé calculada dos microdados públicos da TIC Domicílios, não é número publicado pelo Cetic.br.',
  metodo: { replicas: 200, supressao_n_minimo: 30, precisao_baixa_cv: 0.3 }, validacao: null,
  indicadores: { internet: { rotulo: 'Domicílios com acesso à Internet', definicao: 'A4 = Sim' } },
  uf: 'SP', regiao: 'Sudeste', estimativas: grupo('SP', 'uf', 88.5, 3.9),
  comparacao: { regiao: grupo('Sudeste', 'regiao', 86.8, 1.6), brasil: grupo('BR', 'brasil', 86.3, 0.7) },
}

describe('bloco TIC Domicílios da UF', () => {
  it('mostra a UF, a região e o Brasil com a margem e deixa claro que é estimativa do Arandurapé', () => {
    render(<MemoryRouter><CeticUfBloco dados={{ uf: 'SP', cetic } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(screen.getByText('88,5%')).toBeTruthy()
    expect(screen.getByText('Região Sudeste')).toBeTruthy()
    expect(screen.getByText('Brasil')).toBeTruthy()
    expect(screen.getByText(/não é número publicado pelo Cetic.br/)).toBeTruthy()
    expect(screen.getByText(/licença CC BY 4.0/)).toBeTruthy()
  })

  it('mostra "suprimido" quando o grupo tem amostra pequena e "precisão baixa" quando o CV é alto', () => {
    const c2 = { ...cetic, estimativas: grupo('AP', 'uf', 0, 0, { suprimido: 'menos de 30 domicílios entrevistados' }), comparacao: { regiao: grupo('Norte', 'regiao', 80, 2, { precisao: 'baixa' }), brasil: null } }
    render(<MemoryRouter><CeticUfBloco dados={{ uf: 'AP', cetic: c2 } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(screen.getByText('suprimido')).toBeTruthy()
    expect(screen.getByText(/precisão baixa/)).toBeTruthy()
  })

  it('não renderiza nada sem as estimativas', () => {
    const { container } = render(<MemoryRouter><CeticUfBloco dados={{ uf: 'SP' } as UfCtx} snapshot={null} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })
})
