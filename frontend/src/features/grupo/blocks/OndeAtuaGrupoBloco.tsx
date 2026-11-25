// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../../auth/AuthContext'
import { Link } from '../../../components/layout/LinkDatado'
import { EstadoDados } from '../../../components/ui/EstadoDados'
import { HhiLocal } from '../../../components/ui/HhiLocal'
import { LinhaProveniencia } from '../../../components/ui/Kpi'
import { PreviaLista } from '../../../components/ui/PreviaLista'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useActiveDate } from '../../../hooks/useSnapshot'
import { alternarOrdem, type Ordem } from '../../../lib/ordenacao'
import { NOTA_FAIXAS_HHI } from '../../../lib/referencias'
import { fetchGrupoMunicipios } from '../../../services/api'
import type { OrdemGrupoMunicipios } from '../../../types/api'
import type { BlocoProps } from '../../entidade/registry'
import type { GrupoCtx } from '../contexto'
import { SemInferenciaSA } from '../SemInferenciaSA'

const POR_PAGINA = 100
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
/** Primeiro clique de cada coluna: texto de A a Z, número do maior para o menor (a ordem padrão é acessos, decrescente). */
const PRIMEIRO: Record<OrdemGrupoMunicipios, 'asc' | 'desc'> = { acessos: 'desc', parcela: 'desc', hhi: 'desc', nome: 'asc', uf: 'asc' }

/**
 * "Onde o conjunto atua" do grupo (PT-23): município a município, os acessos do conjunto de CNPJs, a parcela nos acessos declarados do município, quantas empresas declararam
 * e o HHI local (por grupo, inferido, e por CNPJ, declarado). A lista de um grupo grande passa de 5 mil municípios: filtro por UF, busca, ordem e página vêm do servidor, com a
 * prévia de 100 linhas aberta e as demais com login. Nenhuma linha é suprimida; parcela alta num município pequeno não é "domínio": os declarantes ficam ao lado.
 */
export function OndeAtuaGrupoBloco({ dados }: BlocoProps<GrupoCtx>) {
  const g = dados.grupo
  const date = useActiveDate()
  const { user, requireLogin } = useAuth()
  const [uf, setUf] = useState('')
  const [busca, setBusca] = useState('')
  const [ordem, setOrdem] = useState<Ordem<OrdemGrupoMunicipios>>({ campo: 'acessos', dir: 'desc' })
  const [pagina, setPagina] = useState(1)
  const ufs = useMemo(() => [...new Set(g.municipios.map((m) => m.uf).filter(Boolean))].sort(), [g.municipios])
  const q = busca.trim()
  const { data, isLoading, error } = useQuery({
    queryKey: ['grupo-municipios', g.grupo_id, date, uf, q, ordem.campo, ordem.dir, pagina],
    queryFn: () => fetchGrupoMunicipios(g.grupo_id, { date: date ?? undefined, uf: uf || undefined, q: q || undefined, ordem: ordem.campo, desc: ordem.dir === 'desc', limit: POR_PAGINA, page: pagina }),
    enabled: !!date && g.municipios.length > 0, staleTime: 10 * 60 * 1000, retry: false, placeholderData: (anterior) => anterior,
  })
  if (g.municipios.length === 0) return <p className="text-sm text-gray-500">Nenhuma empresa do grupo declarou acessos fixos ao SICI no mês de referência.</p>
  if (error && !data) return <EstadoDados erro={error} oQue="a tabela de municípios do grupo" />
  if (isLoading && !data) return <EstadoDados estado="carregando" mensagem="Carregando os municípios…" />
  if (!data) return null

  const agrupado = data.tamanho >= 2 && data.grupo_inferivel !== false
  const paginas = Math.max(1, Math.ceil(data.total / POR_PAGINA))
  const ini = (data.page - 1) * POR_PAGINA
  const r = data.resumo
  const mudar = (fn: () => void) => { fn(); setPagina(1) }
  const ordenar = (c: string) => mudar(() => setOrdem((o) => alternarOrdem(o, c as OrdemGrupoMunicipios, PRIMEIRO[c as OrdemGrupoMunicipios])))
  const th = (c: OrdemGrupoMunicipios) => ({ campo: c, ordem, onOrdenar: ordenar })
  const irPara = (p: number) => { if (p > 1 && !user && !requireLogin('lista-expandida')) return; setPagina(p) }

  return (
    <div className="space-y-3" data-testid="grupo-onde-atua">
      {data.grupo_inferivel === false && <SemInferenciaSA />}
      <p className="text-sm text-gray-700">
        O conjunto declara acessos em <strong>{n(r.municipios)}</strong> municípios de <strong>{n(r.ufs)}</strong> {r.ufs === 1 ? 'UF' : 'UFs'}. Em <strong>{n(r.com_mais_da_metade)}</strong> deles tem mais da metade
        dos acessos declarados no município e em <strong>{n(r.com_um_so_declarante)}</strong> é a única empresa declarante (SICI {data.mes_referencia ?? 'sem mês de referência'}).
      </p>
      <LinhaProveniencia selo={agrupado ? 'inferido' : 'fato'} fonte={agrupado ? 'Anatel (SICI), acessos somados por grupo inferido do quadro societário' : 'Anatel (SICI), acessos declarados por município'} dataRef={data.mes_referencia} />

      <div className="flex flex-wrap items-end gap-3 text-xs text-gray-600">
        <label className="flex flex-col">UF
          <select value={uf} onChange={(e) => mudar(() => setUf(e.target.value))} className="border border-gray-300 rounded px-2 py-1 text-sm min-h-[24px]">
            <option value="">todas</option>{ufs.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </label>
        <label className="flex flex-col">Buscar município
          <input type="search" value={busca} onChange={(e) => mudar(() => setBusca(e.target.value))} className="border border-gray-300 rounded px-2 py-1 text-sm w-56 min-h-[24px]" placeholder="parte do nome" />
        </label>
      </div>
      <p className="text-xs text-gray-600" role="status" aria-live="polite">
        {data.total === 0 ? 'Nenhum município com estes filtros.' : `Mostrando ${n(ini + 1)} a ${n(Math.min(ini + POR_PAGINA, data.total))} de ${n(data.total)} municípios. Ordem: ${data.ordem}.`}
      </p>

      <div className="max-h-[32rem] overflow-auto border border-gray-100 rounded">
        <table className="min-w-full text-sm" data-testid="grupo-onde-atua-tabela">
          <caption className="sr-only">Municípios em que o conjunto de CNPJs do grupo declarou acessos fixos, com a parcela do conjunto nos acessos do município, o número de empresas declarantes e o HHI local. Ordem inicial: acessos do conjunto, do maior para o menor.</caption>
          <thead className="sticky top-0 bg-gray-50">
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <ThOrdenavel {...th('nome')} className="px-3 py-1.5 font-medium">Município</ThOrdenavel>
              <ThOrdenavel {...th('uf')} className="px-3 py-1.5 font-medium w-14">UF</ThOrdenavel>
              <ThOrdenavel {...th('acessos')} alinhar="right" className="px-3 py-1.5 font-medium text-right">Acessos do conjunto</ThOrdenavel>
              <ThOrdenavel {...th('parcela')} alinhar="right" className="px-3 py-1.5 font-medium text-right">Parcela no município</ThOrdenavel>
              <th scope="col" className="px-3 py-1.5 font-medium text-right">Declarantes</th>
              {agrupado && <ThOrdenavel {...th('hhi')} alinhar="right" className="px-3 py-1.5 font-medium text-right">HHI local por grupo (inferido)</ThOrdenavel>}
              {agrupado ? <th scope="col" className="px-3 py-1.5 font-medium text-right">HHI local por CNPJ</th> : <ThOrdenavel {...th('hhi')} alinhar="right" className="px-3 py-1.5 font-medium text-right">HHI local</ThOrdenavel>}
            </tr>
          </thead>
          <tbody>
            {data.items.map((l) => (
              <tr key={l.ibge} className="border-b border-gray-100 hover:bg-gray-50 align-top">
                <th scope="row" className="px-3 py-1 text-left font-normal"><Link to={`/municipio/${l.ibge}`} className="text-primario-700 underline">{l.nome}</Link></th>
                <td className="px-3 py-1 text-gray-600">{l.uf}</td>
                <td className="px-3 py-1 text-right tabular-nums">{n(l.acessos)}{agrupado && l.cnpjs_do_conjunto > 1 && <span className="block text-xs text-gray-600">{n(l.cnpjs_do_conjunto)} CNPJs</span>}</td>
                <td className="px-3 py-1 text-right tabular-nums">{pct(l.parcela)}</td>
                <td className="px-3 py-1 text-right tabular-nums">{l.declarantes === 1 ? '1 (uma só empresa declarante)' : n(l.declarantes)}</td>
                {agrupado && <td className="px-3 py-1 text-right"><HhiLocal valor={l.hhi_grupo} faixa={l.faixa_grupo} avisos={l.avisos_grupo} /></td>}
                <td className="px-3 py-1 text-right"><HhiLocal valor={agrupado ? l.hhi_cnpj : (l.hhi_grupo ?? l.hhi_cnpj)} faixa={agrupado ? l.faixa_cnpj : (l.faixa_grupo ?? l.faixa_cnpj)} avisos={agrupado ? undefined : l.avisos_grupo} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!user && <PreviaLista mostradas={data.items.length} total={data.total} aoEntrar={() => requireLogin('lista-expandida')} className="text-xs text-gray-600" />}
      {paginas > 1 && (
        <nav aria-label="Páginas da tabela de municípios do grupo" className="flex items-center gap-3 text-sm">
          <button type="button" disabled={data.page <= 1} onClick={() => irPara(data.page - 1)} className="min-h-[24px] min-w-[24px] px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Anterior</button>
          <span className="text-xs text-gray-600">página {n(data.page)} de {n(paginas)}</span>
          <button type="button" disabled={data.page >= paginas} onClick={() => irPara(data.page + 1)} className="min-h-[24px] min-w-[24px] px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Próxima</button>
        </nav>
      )}

      <div className="space-y-1 text-xs text-gray-600">
        <p><b>Como ler.</b> {data.limites}</p>
        <p>{NOTA_FAIXAS_HHI}</p>
      </div>
    </div>
  )
}
