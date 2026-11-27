// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ResumoUf } from '../../types/api'
import { posicaoNaMetrica } from '../estados/CartogramaUfs'
import { n0, n1 } from '../../lib/sintese'

/** O que o painel da UF mostra, cada um com a referência nacional e a posição entre as UFs (PT-22 / uf 5.5). */
export type IndicadorPainelUf = 'acessos' | 'fibra' | 'penetracao' | 'ptts' | 'asns'

const soma = (ufs: ResumoUf[], f: (u: ResumoUf) => number | null | undefined) => ufs.reduce((t, u) => t + (f(u) ?? 0), 0)

/** Valor do Brasil de cada indicador, calculado das mesmas linhas de `/ufs` (nada digitado à mão); nulo quando as linhas não permitem a conta. */
export function valorBrasil(ufs: ResumoUf[], id: IndicadorPainelUf): string | null {
  if (ufs.length === 0) return null
  switch (id) {
    case 'acessos': {
      const com = ufs.filter((u) => u.acessos != null)
      return com.length ? n0(soma(com, (u) => u.acessos)) : null
    }
    case 'fibra': {
      // percentual de fibra do país: média dos percentuais das UFs ponderada pelos acessos de cada uma
      const com = ufs.filter((u) => u.acessos != null && u.acessos > 0 && u.fibra_pct != null)
      const total = soma(com, (u) => u.acessos)
      return total > 0 ? `${n1(soma(com, (u) => (u.acessos as number) * (u.fibra_pct as number)) / total)}%` : null
    }
    case 'penetracao': {
      const com = ufs.filter((u) => u.acessos != null && u.domicilios != null && u.domicilios > 0)
      const dom = soma(com, (u) => u.domicilios)
      return dom > 0 ? n1((100 * soma(com, (u) => u.acessos)) / dom) : null
    }
    case 'ptts': return n0(soma(ufs, (u) => u.ptts))
    case 'asns': return n0(soma(ufs, (u) => u.asns))
  }
}

const VALOR: Record<IndicadorPainelUf, (u: ResumoUf) => number | null> = {
  acessos: (u) => u.acessos,
  fibra: (u) => u.fibra_pct,
  penetracao: (u) => (u.penetracao == null ? null : u.penetracao * 100),
  ptts: (u) => u.ptts,
  asns: (u) => u.asns,
}

/** "Brasil: X · posição N de 27 UFs": a referência nacional e o lugar da UF pelo valor (1 = maior valor, sem juízo de bom ou ruim). Vazio sem `/ufs`. */
export function referenciaUf(ufs: ResumoUf[] | undefined, uf: string, id: IndicadorPainelUf): string {
  if (!ufs || ufs.length === 0) return ''
  const brasil = valorBrasil(ufs, id)
  const p = posicaoNaMetrica(ufs, uf, VALOR[id])
  return [brasil != null ? `Brasil: ${brasil}` : null, p ? `posição ${p.posicao} de ${p.de} UFs (1 = maior valor)` : null].filter(Boolean).join(' · ')
}
