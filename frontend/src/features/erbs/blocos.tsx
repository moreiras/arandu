// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '../../components/layout/LinkDatado'
import { fetchErbsMunicipios } from '../../services/api'
import { formatarCnpj, rotulosRepetidos } from '../../lib/marca'
import type { BlocoProps } from '../entidade/registry'
import type { MunicipioCtx } from '../municipio/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { ErbsGeracoes, ErbsMeta, Geracao } from '../../types/api'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'

const GERACOES: Geracao[] = ['2G', '3G', '4G', '5G']
const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const dec = (v?: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }))

function Geracoes({ g }: { g: ErbsGeracoes }) {
  return (
    <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      {GERACOES.map((k) => <div key={k}><dt className="inline text-gray-500">{k} </dt><dd className="inline font-medium tabular-nums">{inteiro(g[k])}</dd></div>)}
    </dl>
  )
}

/** O que o dado é e não é, sempre junto do número: cadastro de licenciamento da Anatel, não cobertura. */
function Nota({ m }: { m: ErbsMeta }) {
  return (
    <p className="text-xs text-gray-500">
      Estações do SMP <strong>licenciadas</strong> na Anatel (cadastro; arquivo de {m.data_arquivo ? new Date(m.data_arquivo).toLocaleDateString('pt-BR') : 'data não informada'}). {m.limites}
    </p>
  )
}

/** Estações licenciadas no município por geração e por operadora. Município sem estação mostra zero: é informação, mas não prova ausência de serviço. */
export function ErbsMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const e = dados.erbs
  if (!e) return null
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{inteiro(e.estacoes)}</span> <span className="text-sm text-gray-500">estações licenciadas</span></div>
        {e.por_10mil_hab != null && <div className="text-sm text-gray-600"><span className="font-medium tabular-nums">{dec(e.por_10mil_hab)}</span> por 10 mil habitantes</div>}
        {e.comparacao_uf && <div className="text-sm text-gray-500">Na UF {e.uf}: {inteiro(e.comparacao_uf.municipios_com_estacao)} de {inteiro(e.comparacao_uf.municipios)} municípios têm estação</div>}
      </div>
      <Geracoes g={e.geracoes} />
      {e.operadoras.length > 0 && (
        <ul className="text-sm divide-y divide-gray-50">
          {e.operadoras.map((o, _i, todas) => {
            const repetida = rotulosRepetidos(todas.map((x) => x.marca)).has(o.marca)
            return (
            <li key={`${o.cnpj ?? o.marca}`} className="py-1 flex justify-between">
              <span>
                {o.cnpj ? <Link to={`/operadora/${o.cnpj}`} className="text-primario-600 hover:underline">{o.marca}</Link> : <span>{o.marca}</span>}
                {repetida && o.cnpj && <span className="ml-1 text-xs text-gray-400">· CNPJ {formatarCnpj(o.cnpj)}</span>}
              </span>
              <span className="tabular-nums text-gray-600">{inteiro(o.estacoes)}</span>
            </li>
            )
          })}
        </ul>
      )}
      {e.estacoes === 0 && <p className="text-sm text-gray-600">Nenhuma estação do SMP licenciada neste município; o serviço pode vir de estações de municípios vizinhos.</p>}
      <Nota m={e} />
    </div>
  )
}

/** Estações da UF por geração e os municípios com mais estações, com filtro por geração. */
export function ErbsUfBloco({ dados }: BlocoProps<UfCtx>) {
  const e = dados.erbs
  const [geracao, setGeracao] = useState('')
  // A tabela traz só os 10 primeiros: a ordem vai ao servidor (`ordem`), que só ordena do maior para o menor nestas duas colunas.
  const [campo, setCampo] = useState<'estacoes' | 'por_10mil_hab'>('estacoes')
  const q = useQuery({
    queryKey: ['erbs-municipios', dados.uf, geracao, campo], enabled: !!e,
    queryFn: () => fetchErbsMunicipios({ uf: dados.uf, geracao: geracao || undefined, limit: 10, ...(campo === 'estacoes' ? {} : { ordem: campo }) }), staleTime: 10 * 60 * 1000, retry: false,
  })
  const th = (c: typeof campo) => ({ campo: c, ordem: { campo, dir: 'desc' as const }, onOrdenar: () => setCampo(c) })
  if (!e) return null
  const r = e.resumo
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{inteiro(r.estacoes)}</span> <span className="text-sm text-gray-500">estações licenciadas · {r.operadoras} operadoras</span></div>
        <div className="text-sm text-gray-600">{inteiro(r.municipios_com_estacao)} de {inteiro(r.municipios)} municípios têm estação · {inteiro(r.municipios_com_5g)} com 5G</div>
      </div>
      <Geracoes g={r.geracoes} />
      <label className="text-sm text-gray-600 flex flex-col w-fit">Municípios com mais estações em
        <select value={geracao} onChange={(ev) => setGeracao(ev.target.value)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
          <option value="">qualquer geração</option>
          {GERACOES.map((g) => <option key={g} value={g}>{g}</option>)}
        </select>
      </label>
      {q.data && (
        <table className="text-xs min-w-full">
          <thead className="text-gray-500"><tr><th scope="col" className="text-left px-2 py-1">Município</th><ThOrdenavel {...th('estacoes')} alinhar="right" className="text-right px-2 py-1">{geracao ? `Estações ${geracao}` : 'Estações'}</ThOrdenavel><ThOrdenavel {...th('por_10mil_hab')} alinhar="right" className="text-right px-2 py-1">Por 10 mil hab.</ThOrdenavel><th scope="col" className="text-left px-2 py-1">Mais estações</th></tr></thead>
          <tbody>
            {q.data.items.map((m) => (
              <tr key={m.ibge} className="border-t border-gray-100">
                <td className="px-2 py-1"><Link to={`/municipio/${m.ibge}`} className="text-primario-600 hover:underline">{m.nome ?? m.ibge}</Link></td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(geracao ? m[`estacoes_${geracao.toLowerCase()}` as keyof typeof m] as number : m.estacoes)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{dec(m.por_10mil_hab)}</td>
                <td className="px-2 py-1">{m.operadora_principal ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Nota m={e} />
    </div>
  )
}

/** Estações licenciadas da operadora: total, municípios, UFs, gerações e tipo do 5G. */
export function ErbsOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const e = dados.erbs
  if (!e) return null
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{inteiro(e.estacoes)}</span> <span className="text-sm text-gray-500">estações licenciadas em {inteiro(e.municipios)} municípios, {e.ufs} UFs</span></div>
        <div className="text-sm text-gray-600">{dec(100 * e.estacoes / e.brasil.estacoes)}% das estações do SMP no país</div>
      </div>
      <Geracoes g={e.geracoes} />
      {Object.keys(e.tipo_5g).length > 0 && (
        <p className="text-sm text-gray-600">5G: {Object.entries(e.tipo_5g).map(([k, v]) => `${k} ${inteiro(v)}`).join(' · ')} <span className="text-gray-400">(SA = núcleo 5G próprio; NSA = apoiado no 4G)</span></p>
      )}
      <Nota m={e} />
    </div>
  )
}
