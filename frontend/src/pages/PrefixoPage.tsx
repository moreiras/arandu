// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Navigate, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { EntityPage } from '../features/entidade/EntityPage'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'
import { CabecalhoPrefixo } from '../features/prefixo/CabecalhoPrefixo'
import { FichaPrefixo } from '../features/prefixo/FichaPrefixo'
import type { PrefixoCtx } from '../features/prefixo/contexto'
import '../features/prefixo'
import { useAsn, useFontes } from '../hooks/entidades'
import { useActiveDate } from '../hooks/useSnapshot'
import { canonizarPrefixo, caminhoDoPrefixo, ehIp, ehPrefixo } from '../lib/prefixo'
import { fetchPrefix, fetchPrefixDoIp } from '../services/api'

/** Exemplos conferidos no snapshot (alocações do Registro.br que abrem): IPv6 antes de IPv4. */
const EXEMPLOS = ['2804::/32', '177.75.0.0/20']

function Exemplos() {
  return <>Exemplos: {EXEMPLOS.map((e, i) => <span key={e}>{i > 0 && ' ou '}<Link className="text-primario-600 hover:underline" to={caminhoDoPrefixo(e)}>{e}</Link></span>)}, ou um IP como 177.75.0.1.</>
}

/**
 * `/prefixo/:prefixo` (ex.: `/prefixo/2804::/32`): detentor e origem observada, RPKI do anúncio, PTTs, Registro.br,
 * geolocalização, MOAS e ciclo de vida do bloco IPv4. Chamada principal: `GET /prefixes/{prefix}` (aceita alocações do Registro.br
 * e rotas observadas fora delas); o documento do AS da origem observada (`useAsn`) completa PTTs e ASPA. Grafia não canônica
 * (zeros à esquerda, bits de host) é redirecionada para a forma canônica, com aviso.
 */
export function PrefixoPage() {
  const prefix = (useParams()['*'] ?? '').trim()
  const [params] = useSearchParams()
  const informado = (useLocation().state as { informado?: string } | null)?.informado
  const ip = ehIp(prefix)
  const valido = ehPrefixo(prefix)
  const canon = valido ? canonizarPrefixo(prefix) : null
  const date = useActiveDate()
  const { fontes } = useFontes()
  const ipQ = useQuery({ queryKey: ['prefixo-do-ip', prefix, date], queryFn: () => fetchPrefixDoIp(prefix, date ?? undefined), enabled: ip && !!date, staleTime: Infinity, gcTime: Infinity, retry: false })
  const q = useQuery({ queryKey: ['prefixo', prefix, date], queryFn: () => fetchPrefix(prefix, date ?? undefined), enabled: valido && canon === prefix && !!date, staleTime: Infinity, gcTime: Infinity, retry: false })
  const asnQ = useAsn(q.data?.observed_origin_asn ?? undefined)

  if (ip) {
    if (ipQ.data) return <Navigate replace to={caminhoDoPrefixo(ipQ.data.prefix)} />
    if (ipQ.isError && ehErroDeAcessoOuFalha(ipQ.error)) {
      return <EstadoDados variante="pagina" erro={ipQ.error} oQue={`o prefixo que contém ${prefix}`} aoTentarDeNovo={() => void ipQ.refetch()} />
    }
    if (ipQ.isError) {
      return (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h1 className="text-lg font-semibold text-gray-800 mb-1">Nenhum prefixo contém {prefix}</h1>
          <p className="text-sm text-gray-500">O endereço não está em nenhuma das alocações geolocalizadas do Registro.br neste snapshot (a busca por IP só percorre essas alocações).</p>
        </div>
      )
    }
    return <div className="text-sm text-gray-400">Procurando o prefixo que contém {prefix}…</div>
  }
  if (!valido) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Prefixo inválido</h1>
        <p className="text-sm text-gray-500">“{prefix || '—'}” não é um prefixo CIDR nem um endereço IP. <Exemplos /></p>
      </div>
    )
  }
  if (canon && canon !== prefix) return <Navigate replace to={caminhoDoPrefixo(canon)} state={{ informado: prefix }} />
  if (q.isLoading) return <div className="text-sm text-gray-400">Carregando…</div>
  if (q.isError && ehErroDeAcessoOuFalha(q.error)) {
    return <EstadoDados variante="pagina" erro={q.error} oQue={`o prefixo ${prefix}`} aoTentarDeNovo={() => void q.refetch()} />
  }
  if (q.isError || !q.data) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Prefixo não encontrado</h1>
        <p className="text-sm text-gray-500">
          {prefix} não consta das alocações do Registro.br nem da tabela global ou dos route servers do IX.br coletados neste snapshot;
          isso não prova que não seja anunciado em outro ponto da Internet. <Exemplos />
        </p>
      </div>
    )
  }
  if (q.data.prefix !== prefix) return <Navigate replace to={caminhoDoPrefixo(q.data.prefix)} state={{ informado: prefix }} />
  const ctx: PrefixoCtx = { prefix, info: q.data, asn: asnQ.data, carregandoAsn: asnQ.isLoading, date }
  return (
    <div className="space-y-5">
      <CabecalhoPrefixo info={q.data} />
      {informado && informado !== prefix && (
        <p role="status" className="text-sm text-gray-600" data-testid="aviso-canonico">Mostrando {prefix}, a forma canônica de “{informado}”.</p>
      )}
      {params.get('versao') !== '1' && <FichaPrefixo info={q.data} />}
      <EntityPage entidade="prefixo" rotulo={`Prefixo ${prefix}`} dados={ctx} snapshot={q.data.snapshot_date} fontes={fontes} espacamento="space-y-5" />
    </div>
  )
}
