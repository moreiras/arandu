// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Link } from '../../components/layout/LinkDatado'
import { useQueries, useQuery } from '@tanstack/react-query'
import { fetchASNsLote, fetchBusca, fetchGrupoComparavel, fetchMunicipioPerfil, fetchOperadoraPerfil, type ItemBusca } from '../../services/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { manterData } from '../../lib/dataAtiva'
import { CitarDado } from '../../components/entidade/CitarDado'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../../components/ui/EstadoDados'
import { DESCRICAO_SELO, ROTULO_SELO } from '../../components/entidade'
import { compararAs, compararGrupos, compararMunicipios, compararOperadoras, idValido, MAX_ENTIDADES, MIN_ENTIDADES, TIPOS, urlComparar, type Comparacao, type TipoComparacao } from './entidades'

type TipoGenerico = Exclude<TipoComparacao, 'ixp'>
const COR_SELO = { fato: 'bg-fato-600', inferido: 'bg-inferido-600', estimado: 'bg-estimado-600' } as const
const FONTES: Record<TipoGenerico, string[]> = {
  asn: ['fulltable_routeviews', 'registro_br', 'apnic_pop'],
  operadora: ['anatel_sici', 'registro_br'],
  municipio: ['anatel_sici', 'ibge_censo_pnad', 'curada_pix'],
  grupo: ['anatel_sici', 'receita_socios', 'registro_br', 'anatel_multas'],
}

/** A pessoa escolhe as entidades pela busca (ou digitando o número/CNPJ/IBGE); a escolha mora na URL (`?tipo=…&ids=…`), então o link da comparação é o endereço da página. */
function Escolha({ tipo, ids, aoMudar }: { tipo: TipoGenerico; ids: string[]; aoMudar: (ids: string[]) => void }) {
  const [texto, setTexto] = useState('')
  const [sug, setSug] = useState<ItemBusca[]>([])
  useEffect(() => {
    const q = texto.trim()
    if (q.length < 2) { setSug([]); return }
    let vivo = true
    const t = setTimeout(() => { fetchBusca(q, { limite: 6 }).then((r) => { if (vivo) setSug(r.grupos.filter((g) => g.tipo === tipo).flatMap((g) => g.itens)) }).catch(() => { if (vivo) setSug([]) }) }, 250)
    return () => { vivo = false; clearTimeout(t) }
  }, [texto, tipo])
  const adicionar = (id: string | null) => { if (id && !ids.includes(id) && ids.length < MAX_ENTIDADES) aoMudar([...ids, id]); setTexto(''); setSug([]) }
  const idDoItem = (i: ItemBusca) => idValido(tipo, decodeURIComponent(i.url.split(/[/?=]/).filter(Boolean).pop() ?? ''))
  return (
    <div className="space-y-2">
      <form onSubmit={(e) => { e.preventDefault(); adicionar(idValido(tipo, texto)) }} className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-gray-600">Adicionar
          <input value={texto} onChange={(e) => setTexto(e.target.value)} disabled={ids.length >= MAX_ENTIDADES} placeholder={`nome ou ${TIPOS.find((t) => t.id === tipo)!.exemplo}`}
            className="ml-2 w-64 max-w-full rounded border border-gray-300 px-2 py-1 text-sm" />
        </label>
        <button type="submit" disabled={ids.length >= MAX_ENTIDADES} className="rounded border border-primario-300 px-2 py-1 text-sm text-primario-700 hover:bg-primario-50 disabled:opacity-50">Adicionar</button>
        <span className="text-xs text-gray-500">{ids.length} de {MAX_ENTIDADES} (mínimo {MIN_ENTIDADES})</span>
      </form>
      {sug.length > 0 && (
        <ul className="max-w-xl rounded border border-gray-200 bg-white text-sm" aria-label="Sugestões">
          {sug.map((i) => { const id = idDoItem(i); return id ? <li key={i.url}><button type="button" onClick={() => adicionar(id)} className="block w-full px-2 py-1 text-left hover:bg-gray-50">{i.titulo} <span className="text-xs text-gray-500">{i.detalhe}</span></button></li> : null })}
        </ul>
      )}
    </div>
  )
}

function Quadro({ c, aoRemover }: { c: Comparacao; aoRemover: (id: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm" data-tabela="grade" data-testid="quadro-comparacao">
        <thead>
          <tr className="border-b border-gray-200 text-left align-bottom">
            <th className="py-2 pr-3 text-xs font-medium text-gray-500">Indicador</th>
            {c.colunas.map((col) => (
              <th key={col.id} className="py-2 pr-3 font-medium">
                <Link to={col.to} className="text-primario-700 hover:underline">{col.nome}</Link>
                {col.detalhe && <span className="block text-xs font-normal text-gray-500">{col.detalhe}</span>}
                <button type="button" onClick={() => aoRemover(col.id)} className="text-xs font-normal text-gray-500 hover:text-perigo-700" aria-label={`Tirar ${col.nome} da comparação`}>tirar</button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {c.linhas.map((l) => (
            <tr key={l.id} className="border-b border-gray-100">
              <th scope="row" className="py-1.5 pr-3 text-left font-normal text-gray-700">
                <span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${COR_SELO[l.selo]}`} title={`${ROTULO_SELO[l.selo]}: ${DESCRICAO_SELO[l.selo]}`} aria-hidden="true" />
                <span className="sr-only">{ROTULO_SELO[l.selo]}: </span>{l.rotulo}
                {l.nota && <span className="block text-xs text-gray-400">{l.nota}</span>}
              </th>
              {l.celulas.map((v, i) => <td key={i} className="py-1.5 pr-3 tabular-nums" data-label={c.colunas[i]?.nome}>{v ?? '—'}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Comparar de 2 a 4 ASes, operadoras ou municípios lado a lado. Cada linha leva o selo fato/inferido/estimado; linha sem dado em nenhuma entidade some. */
export function CompararEntidades({ tipo }: { tipo: TipoGenerico }) {
  const date = useActiveDate()
  const [params, setParams] = useSearchParams()
  const ids = useMemo(() => (params.get('ids') ?? params.get(tipo) ?? '').split(',').map((x) => idValido(tipo, x)).filter((x): x is string => !!x).slice(0, MAX_ENTIDADES), [params, tipo])
  // Troca só `tipo` e `ids`: a data do snapshot (`?date=`) fica, senão a coluna nova viria do snapshot mais recente.
  const mudar = (novos: string[]) => setParams((atuais) => manterData(atuais, novos.length ? { tipo, ids: novos.join(',') } : { tipo }), { replace: true })

  const asq = useQuery({ queryKey: ['comparar-as', ids, date], enabled: tipo === 'asn' && ids.length > 0, queryFn: () => fetchASNsLote(ids, { date: date ?? undefined }), staleTime: 10 * 60 * 1000 })
  const opq = useQueries({ queries: (tipo === 'operadora' ? ids : []).map((c) => ({ queryKey: ['comparar-op', c, date], queryFn: () => fetchOperadoraPerfil(c, date ?? undefined), staleTime: 10 * 60 * 1000 })) })
  const muq = useQueries({ queries: (tipo === 'municipio' ? ids : []).map((i) => ({ queryKey: ['comparar-mun', i, date], queryFn: () => fetchMunicipioPerfil(i, date ?? undefined), staleTime: 10 * 60 * 1000 })) })

  const grq = useQueries({ queries: (tipo === 'grupo' ? ids : []).map((i) => ({ queryKey: ['comparar-grupo', i, date], queryFn: () => fetchGrupoComparavel(i, date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })) })

  const carregando = tipo === 'asn' ? asq.isLoading : (tipo === 'operadora' ? opq : tipo === 'grupo' ? grq : muq).some((q) => q.isLoading)
  let comp: Comparacao | null = null
  let faltam: string[] = []
  if (tipo === 'asn' && asq.data) { comp = compararAs(asq.data.items as never); faltam = (asq.data.not_found ?? []).map(String) }
  if (tipo === 'operadora') { const ok = opq.map((q) => q.data).filter((d): d is NonNullable<typeof d> => !!d); comp = compararOperadoras(ok); faltam = ids.filter((c) => !ok.some((o) => o.cnpj === c)) }
  if (tipo === 'municipio') { const ok = muq.map((q) => q.data).filter((d): d is NonNullable<typeof d> => !!d); comp = compararMunicipios(ok); faltam = ids.filter((i) => !ok.some((o) => o.ibge === i)) }
  if (tipo === 'grupo') { const ok = grq.map((q) => q.data).filter((d): d is NonNullable<typeof d> => !!d); comp = compararGrupos(ok); faltam = ids.filter((i) => !ok.some((o) => o.grupo.grupo_id === i)) }
  // Erro de acesso, de taxa ou de rede não é "sem dado": a entidade sai de `faltam` e o quadro avisa por que não carregou.
  const porId: { isError: boolean; error: unknown }[] = tipo === 'operadora' ? opq : tipo === 'grupo' ? grq : tipo === 'municipio' ? muq : []
  const bloqueados = tipo === 'asn' ? (asq.isError && ehErroDeAcessoOuFalha(asq.error) ? ids : []) : ids.filter((_, i) => porId[i]?.isError && ehErroDeAcessoOuFalha(porId[i].error))
  const erroBloqueio = tipo === 'asn' ? (bloqueados.length ? asq.error : null) : porId.find((q) => q.isError && ehErroDeAcessoOuFalha(q.error))?.error
  faltam = faltam.filter((x) => !bloqueados.includes(x))
  const pronto = !!comp && comp.colunas.length >= MIN_ENTIDADES
  const rotuloTipo = TIPOS.find((t) => t.id === tipo)!.rotulo.toLowerCase()
  const snapshot = (asq.data?.snapshot_date ?? opq.find((q) => q.data)?.data?.snapshot_date ?? muq.find((q) => q.data)?.data?.snapshot_date ?? grq.find((q) => q.data)?.data?.grupo.snapshot_date) ?? date

  return (
    <div className="space-y-4" data-testid={`comparar-${tipo}`}>
      <Escolha tipo={tipo} ids={ids} aoMudar={mudar} />
      {faltam.length > 0 && <p className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" role="status">Sem dado neste snapshot para: {faltam.join(', ')}. {faltam.length > 0 && 'Elas ficam de fora do quadro.'}</p>}
      {erroBloqueio != null && <EstadoDados erro={erroBloqueio} oQue={`os dados de ${bloqueados.join(', ')}`} />}
      {erroBloqueio != null && bloqueados.length < ids.length && <p className="text-xs text-gray-600">Não carregados agora (ficam fora do quadro): {bloqueados.join(', ')}.</p>}
      {ids.length < MIN_ENTIDADES && <p className="text-sm text-gray-500">Escolha pelo menos {MIN_ENTIDADES} {rotuloTipo} para comparar (até {MAX_ENTIDADES}).</p>}
      {carregando && ids.length >= MIN_ENTIDADES && <div className="h-32 bg-gray-50 rounded animate-pulse" />}
      {pronto && !carregando && comp && (
        <>
          <Quadro c={comp} aoRemover={(id) => mudar(ids.filter((x) => x !== id))} />
          <details className="relative text-xs text-gray-500"><summary className="cursor-pointer select-none">Fonte, selos e citação</summary>
            <div className="mt-1 max-w-xl rounded border border-gray-200 bg-white p-2 shadow-sm">
              <p>Cada linha tem o selo de natureza do dado (fato, inferido ou estimado). Fontes: {FONTES[tipo].join(', ')}; snapshot {snapshot}. O endereço desta página guarda a comparação.</p>
              <CitarDado pedido={{ entidade: `Comparação de ${rotuloTipo}`, bloco: comp.colunas.map((c) => c.nome).join(' × ') }} fontes={FONTES[tipo]} snapshot={snapshot} />
            </div>
          </details>
        </>
      )}
    </div>
  )
}

export { urlComparar }
