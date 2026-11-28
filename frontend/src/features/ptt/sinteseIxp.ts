// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { coletaDaFamilia, type IXPIndexEntry } from '../../types/api'
import { compacto, limitar, n0, palavra, plural, type FraseSintese } from '../../lib/sintese'
import type { PttCtx } from './contexto'

export const REGRAS_SINTESE_PTT = 'sintese-ptt-3'

/** Quantos PTTs têm mais ASNs em sessão direta que este, e quantos têm o mesmo número (empate); nulo sem o número deste PTT ou sem a lista. */
export function posicaoEntrePtts(code: string, todos: IXPIndexEntry[] | undefined): { mais: number; empate: number; de: number } | null {
  const medidos = (todos ?? []).filter((i) => i.asn_direct_union_count != null)
  const eu = medidos.find((i) => i.code === code)
  if (!eu) return null
  const v = eu.asn_direct_union_count!
  return { mais: medidos.filter((i) => i.asn_direct_union_count! > v).length, empate: medidos.filter((i) => i.code !== code && i.asn_direct_union_count === v).length, de: medidos.length }
}

/**
 * Síntese do PTT (PT-22, ixp 5.4): do que o cabeçalho e o destaque já mostram (`PttCtx`) e da linha do índice. A posição entre os PTTs do IX.br é uma
 * medida de tamanho com a regra na frase (ASNs em sessão direta, união IPv6 e IPv4), dita como "PTTs com mais", nunca "maior" nem "mais importante"; tamanho
 * não mede relevância regional. Família sem coleta gera a frase de coleta, nunca "0 participantes". Estimativa de usuários leva o selo próprio.
 */
export function sinteseIxp(c: PttCtx, nome: string, todos: IXPIndexEntry[] | undefined): FraseSintese[] {
  const snap = c.date ?? c.ixp?.snapshot_date ?? null
  const pos = posicaoEntrePtts(c.code, todos)
  const semColeta = ([['IPv6', coletaDaFamilia(c.ixp?.v6)], ['IPv4', coletaDaFamilia(c.ixp?.v4)]] as const).filter(([, s]) => s !== 'ok').map(([f]) => f)
  const usuarios = c.estUsers?.estimated_users
  return limitar([
    c.par != null && { id: 'cadastro', selo: 'fato', fonte: 'cadastro do IX.br e looking glass', dataRef: snap,
      texto: `O IX.br ${nome} tem ${plural(c.par, 'ASN', 'ASNs')} no cadastro de participantes${c.dir != null ? ` e ${n0(c.dir)} com sessão em route server (união IPv6 e IPv4)` : ''}.` },
    semColeta.length > 0 && { id: 'coleta', selo: 'fato', fonte: 'looking glass do IX.br', dataRef: snap,
      texto: `A coleta do looking glass não trouxe rotas ${semColeta.join(' nem ')} neste snapshot; os números que dependem das rotas ficam sem valor nessa família.` },
    pos && { id: 'posicao', selo: 'fato', fonte: 'looking glasses do IX.br (regra: ASNs em sessão direta, união IPv6 e IPv4)', dataRef: snap,
      texto: `Entre os ${n0(pos.de)} ${palavra(pos.de, 'PTT', 'PTTs')} do IX.br com coleta, ${pos.mais === 0 ? 'nenhum tem' : `${n0(pos.mais)} ${palavra(pos.mais, 'tem', 'têm')}`} mais ASNs em sessão direta que este${pos.empate > 0 ? `, e ${n0(pos.empate)} ${palavra(pos.empate, 'tem', 'têm')} o mesmo número` : ''}.` },
    usuarios != null && { id: 'usuarios', selo: 'estimado', fonte: 'APNIC Labs e looking glass do IX.br', dataRef: snap,
      texto: `Cerca de ${compacto(usuarios)} usuários estimados estão em redes alcançáveis por este PTT em IPv4. Somar vários PTTs contaria o mesmo usuário mais de uma vez.` },
    c.brOriginUnion != null && { id: 'origem', selo: 'fato', fonte: 'looking glass do IX.br', dataRef: snap,
      texto: `${plural(c.brOriginUnion, 'ASN brasileiro origina', 'ASNs brasileiros originam')} prefixos vistos no PTT, inclusive os levados por outro participante.` },
  ])
}
