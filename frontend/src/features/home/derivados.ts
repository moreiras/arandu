// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { queryColecao } from '../../services/api'
import { maisProximos, type LonLat, type PontoNomeado } from '../../lib/geo'
import { useCentroides, usePtts } from '../../hooks/entidades'
import { useActiveDate } from '../../hooks/useSnapshot'
import { CARTOES, type Cartao } from './cartoes'

/** Resultado de um cartão: o mesmo formato da resposta de `/query` para o componente de apresentação. */
export interface Linhas { items: Array<Record<string, unknown>>; total: number }
export interface EstadoCartao { dados?: Linhas; carregando: boolean; erro: unknown }

const TOP = 5
export const LIMITE_KM = 100

function consultas(id: string): Array<{ colecao: string; corpo: Record<string, unknown> }> {
  const c = (CARTOES.find((x: Cartao) => x.id === id)?.consulta ?? { tipo: 'derivado', consultas: [] }) as { consultas?: Array<{ colecao: string; corpo: Record<string, unknown> }> }
  return c.consultas ?? []
}

interface GrupoMunicipio { key: { ibge: string; municipio: string; uf: string }; acessos: number }

/** Municípios (com acessos acima do corte da consulta) cujo PTT mais próximo, em linha reta até o centróide, passa de 100 km; os maiores primeiro. */
export function montarLongeDePtt(grupos: GrupoMunicipio[], centroides: Record<string, LonLat> | undefined, ptts: PontoNomeado[]): Linhas {
  if (!centroides || ptts.length === 0) return { items: [], total: 0 }
  const longe = grupos.flatMap((g) => {
    const p = maisProximos(centroides[g.key.ibge], ptts, 1)[0]
    return p && p.km > LIMITE_KM ? [{ ibge: g.key.ibge, municipio: g.key.municipio, uf: g.key.uf, acessos: g.acessos, km: Math.round(p.km) }] : []
  })
  longe.sort((a, b) => b.acessos - a.acessos)
  return { items: longe.slice(0, TOP), total: longe.length }
}

interface AsnComUsuarios { asn: number; cnpj: string; apnic_users: number }

/** ASes de CNPJs licenciados que não declaram ao SICI, do maior para o menor em usuários APNIC; um CNPJ aparece uma vez (o AS maior). */
export function montarSemSici(asns: AsnComUsuarios[], semSici: Array<{ cnpj: string; razao_social?: string }>): Linhas {
  const nome = new Map(semSici.map((o) => [o.cnpj, o.razao_social ?? o.cnpj]))
  const vistos = new Set<string>()
  const itens = asns
    .filter((a) => nome.has(a.cnpj))
    .sort((a, b) => b.apnic_users - a.apnic_users)
    .filter((a) => (vistos.has(a.cnpj) ? false : (vistos.add(a.cnpj), true)))
    .map((a) => ({ empresa: nome.get(a.cnpj), cnpj: a.cnpj, asn: a.asn, apnic_users: a.apnic_users }))
  return { items: itens.slice(0, TOP), total: itens.length }
}

/** Dados de um cartão derivado. Os hooks são chamados sempre (regra do React); cada cartão só liga o que usa. */
export function useCartaoDerivado(id: string): EstadoCartao {
  const date = useActiveDate()
  const [q1, q2] = consultas(id)
  const longe = id === 'longe-de-ptt'
  const centroides = useCentroides()
  const { ptts, carregando: carregandoPtts, erro: erroPtts } = usePtts()
  const grupos = useQuery({
    queryKey: ['cartao-derivado', id, 'a', date], enabled: !!date && !!q1, staleTime: Infinity, gcTime: Infinity, retry: false,
    queryFn: () => queryColecao<{ groups?: GrupoMunicipio[]; items?: AsnComUsuarios[] }>(q1.colecao, q1.corpo, date ?? undefined),
  })
  const cnpjs = useMemo(() => [...new Set((grupos.data?.items ?? []).map((a) => a.cnpj))], [grupos.data])
  const semSici = useQuery({
    queryKey: ['cartao-derivado', id, 'b', date, cnpjs.length], enabled: !longe && !!date && !!q2 && cnpjs.length > 0, staleTime: Infinity, gcTime: Infinity, retry: false,
    queryFn: () => queryColecao<{ items?: Array<{ cnpj: string; razao_social?: string }> }>(
      q2.colecao, JSON.parse(JSON.stringify(q2.corpo).replace('"$cnpjs"', JSON.stringify(cnpjs))), date ?? undefined),
  })
  const dados = useMemo(() => {
    if (longe) return grupos.data?.groups && centroides.data ? montarLongeDePtt(grupos.data.groups, centroides.data, ptts) : undefined
    return grupos.data?.items && semSici.data ? montarSemSici(grupos.data.items, semSici.data.items ?? []) : undefined
  }, [longe, grupos.data, semSici.data, centroides.data, ptts])
  const carregando = grupos.isLoading || (longe ? centroides.isLoading || carregandoPtts : semSici.isLoading)
  return { dados, carregando, erro: grupos.error ?? semSici.error ?? centroides.error ?? (longe ? erroPtts : null) }
}
