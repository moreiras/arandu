// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { coletaDaFamilia, type IXPIndexEntry } from '../../types/api'

/** Uma medida do PTT comparada às dos demais PTTs do IX.br, na mesma lista (`/ixps`). */
export interface LinhaPosicao {
  id: 'membros' | 'diretos' | 'diretos-v6' | 'diretos-v4'
  rotulo: string
  /** Valor deste PTT; nulo sem o dado (família sem coleta não vira zero). */
  valor: number | null
  mediana: number | null
  maximo: number | null
  /** 1 = maior valor; empates dividem a posição. */
  posicao: number | null
  de: number
}

/** ASNs em sessão direta de uma família, só com a coleta feita e com rotas (família vazia ou ausente fica sem valor). */
const diretosDaFamilia = (afi: IXPIndexEntry['v4']): number | null => (coletaDaFamilia(afi) === 'ok' && 'asn_direct_count' in afi ? afi.asn_direct_count : null)

const medianaDe = (v: number[]): number | null => {
  if (v.length === 0) return null
  const s = [...v].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

/**
 * "Este PTT entre os PTTs do IX.br" (PT-22 / ixp 5.4): membros cadastrados, ASNs em sessão direta (união IPv6 e IPv4) e por família, com a mediana e a posição entre
 * os PTTs que têm a medida. IPv6 antes de IPv4. Posição 1 é o maior valor, sem juízo; PTT ou família sem coleta fica sem valor e fora da mediana (ausência não vira zero).
 */
export function posicaoEntrePttsDoIxbr(code: string, todos: IXPIndexEntry[] | undefined): LinhaPosicao[] {
  if (!todos || todos.length === 0) return []
  const medidas: Array<{ id: LinhaPosicao['id']; rotulo: string; valor: (i: IXPIndexEntry) => number | null | undefined }> = [
    { id: 'membros', rotulo: 'Participantes no cadastro do IX.br', valor: (i) => i.ixbr_members_count },
    { id: 'diretos', rotulo: 'ASNs em sessão direta (IPv6 ou IPv4)', valor: (i) => i.asn_direct_union_count },
    { id: 'diretos-v6', rotulo: 'ASNs em sessão direta, IPv6', valor: (i) => diretosDaFamilia(i.v6) },
    { id: 'diretos-v4', rotulo: 'ASNs em sessão direta, IPv4', valor: (i) => diretosDaFamilia(i.v4) },
  ]
  const eu = todos.find((i) => i.code === code)
  if (!eu) return []
  return medidas.map((m) => {
    const com = todos.map((i) => m.valor(i)).filter((v): v is number => v != null)
    const v = m.valor(eu) ?? null
    return {
      id: m.id, rotulo: m.rotulo, valor: v, mediana: medianaDe(com), maximo: com.length ? Math.max(...com) : null,
      posicao: v == null ? null : 1 + com.filter((x) => x > v).length, de: com.length,
    }
  })
}

/** Os outros PTTs do IX.br na mesma UF, em ordem alfabética de código. */
export function outrosPttsNaUf(code: string, uf: string | undefined, todos: IXPIndexEntry[] | undefined): IXPIndexEntry[] {
  if (!uf || !todos) return []
  return todos.filter((i) => i.uf === uf && i.code !== code).sort((a, b) => a.code.localeCompare(b.code))
}
