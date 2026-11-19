// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link, Navigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { EntityPage } from '../features/entidade/EntityPage'
import { CabecalhoPrefixo } from '../features/prefixo/CabecalhoPrefixo'
import { FichaPrefixo } from '../features/prefixo/FichaPrefixo'
import type { PrefixoCtx } from '../features/prefixo/contexto'
import '../features/prefixo'
import { useAsn, useFontes } from '../hooks/entidades'
import { useActiveDate } from '../hooks/useSnapshot'
import { caminhoDoPrefixo, ehIp, ehPrefixo } from '../lib/prefixo'
import { fetchPrefix, fetchPrefixDoIp } from '../services/api'

/**
 * `/prefixo/:prefixo` (ex.: `/prefixo/177.75.0.0/16`): origem, RPKI, PTTs, Registro.br, geolocalização e MOAS (sob demanda).
 * Chamada principal: `GET /prefixes/{prefix}`; o documento do AS de origem (`useAsn`) completa RPKI, PTTs e Registro.br.
 */
export function PrefixoPage() {
  const prefix = (useParams()['*'] ?? '').trim()
  const [params] = useSearchParams()
  const ip = ehIp(prefix)
  const valido = ehPrefixo(prefix)
  const date = useActiveDate()
  const { fontes } = useFontes()
  const ipQ = useQuery({ queryKey: ['prefixo-do-ip', prefix, date], queryFn: () => fetchPrefixDoIp(prefix, date ?? undefined), enabled: ip && !!date, staleTime: Infinity, gcTime: Infinity, retry: false })
  const q = useQuery({ queryKey: ['prefixo', prefix, date], queryFn: () => fetchPrefix(prefix, date ?? undefined), enabled: valido && !!date, staleTime: Infinity, gcTime: Infinity, retry: false })
  const asnQ = useAsn(q.data?.origin_asn ?? undefined)

  if (ip) {
    if (ipQ.data) return <Navigate replace to={caminhoDoPrefixo(ipQ.data.prefix)} />
    if (ipQ.isError) {
      return (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h1 className="text-lg font-semibold text-gray-800 mb-1">Nenhum prefixo contém {prefix}</h1>
          <p className="text-sm text-gray-500">O endereço não está em nenhum dos prefixos geolocalizados do Registro.br neste snapshot (só os alocados a ASes brasileiros estão aqui).</p>
        </div>
      )
    }
    return <div className="text-sm text-gray-400">Procurando o prefixo que contém {prefix}…</div>
  }
  if (!valido) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Prefixo inválido</h1>
        <p className="text-sm text-gray-500">“{prefix || '—'}” não é um prefixo CIDR nem um endereço IP. Exemplos: <Link className="text-primario-600 hover:underline" to="/prefixo/177.75.0.0/16">177.75.0.0/16</Link> ou <Link className="text-primario-600 hover:underline" to="/prefixo/2804::/32">2804::/32</Link>, ou um IP como 177.75.0.1.</p>
      </div>
    )
  }
  if (q.isLoading) return <div className="text-sm text-gray-400">Carregando…</div>
  if (q.isError || !q.data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Prefixo não encontrado</h1>
        <p className="text-sm text-gray-500">{prefix} não consta dos prefixos geolocalizados do Registro.br neste snapshot (só os alocados a ASes brasileiros estão aqui).</p>
      </div>
    )
  }
  const ctx: PrefixoCtx = { prefix, info: q.data, asn: asnQ.data, carregandoAsn: asnQ.isLoading, date }
  return (
    <div className="space-y-5">
      <CabecalhoPrefixo info={q.data} />
      {params.get('versao') !== '1' && <FichaPrefixo info={q.data} asn={asnQ.data} />}
      <EntityPage entidade="prefixo" rotulo={`Prefixo ${prefix}`} dados={ctx} snapshot={q.data.snapshot_date} fontes={fontes} espacamento="space-y-5" />
    </div>
  )
}
