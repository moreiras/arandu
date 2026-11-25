// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchFacility } from '../services/api'
import { LinhaProveniencia } from '../components/ui/Kpi'
import { Dica } from '../components/ui/Dica'
import type { SituacaoNoPtt } from '../types/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { idInstalacaoValido } from '../lib/identificadores'
import { AtribuicaoPeeringDb, PttRotulo, SeloCadastro, dataCurta, localDe, n } from '../features/instalacoes/comum'
import { MapaInstalacoes } from '../features/instalacoes/MapaInstalacoes'
import { useOrdenacao } from '../lib/ordenacao'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'

/** Rótulo de cada situação da rede no PTT do prédio: neutro, sem "ausente" nem "fora"; `so_origina` é inferido e o rótulo diz. */
const ROTULO_SITUACAO: Record<SituacaoNoPtt, string> = {
  sessao_rs: 'sessão com o route server', membro_sem_sessao_rs: 'no cadastro, sem sessão com o route server', so_origina: 'só origina prefixos (inferido)',
  sem_presenca: 'sem presença observada', sem_coleta: 'PTT sem coleta válida',
}
const ORDEM_SITUACAO: SituacaoNoPtt[] = ['sessao_rs', 'membro_sem_sessao_rs', 'so_origina', 'sem_presenca', 'sem_coleta']

/**
 * `/instalacao/:id` — uma instalação do PeeringDB: localização, PTTs, carriers, campus e as redes que declaram estar nela.
 * Vínculo é declaração no cadastro, não tráfego nem contrato; o selo de cadastro é inferido pelas datas.
 */
export function FacilityPage() {
  const { id = '' } = useParams<{ id: string }>()
  const date = useActiveDate()
  const [soBr, setSoBr] = useState(false)
  const [situacao, setSituacao] = useState<'' | SituacaoNoPtt>('')
  const [pttSel, setPttSel] = useState('')
  const { data: f, isLoading, isError, error, refetch } = useQuery({ queryKey: ['facility', id, date, 'redes_perfil'], queryFn: () => fetchFacility(id, date ?? undefined, 'redes_perfil'), enabled: idInstalacaoValido(id), staleTime: Infinity, gcTime: Infinity, retry: false })
  const resumoPtts = f?.redes_perfil?.resumo ?? []
  const pttAtivo = resumoPtts.find((p) => p.ixp === pttSel)?.ixp ?? resumoPtts[0]?.ixp
  const redesFiltradas = useMemo(() => (f?.redes ?? []).filter((r) => (!soBr || r.is_br) && (!situacao || !pttAtivo || r.situacao?.[pttAtivo] === situacao)), [f, soBr, situacao, pttAtivo])
  // Ordena todas as redes e só depois corta nas 500 exibidas.
  const { ordenados, props } = useOrdenacao(redesFiltradas, {
    asn: { valor: (r) => r.asn, primeiro: 'asc' },
    nome: (r) => r.nome,
    desde: { valor: (r) => r.no_vinculo_desde, primeiro: 'asc' },
  })

  if (isLoading) return <div className="text-sm text-gray-400">Carregando…</div>
  if (isError && ehErroDeAcessoOuFalha(error)) {
    return <EstadoDados variante="pagina" erro={error} oQue={`a instalação ${id}`} aoTentarDeNovo={() => void refetch()} />
  }
  if (isError || !f) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Instalação não encontrada</h1>
        <p className="text-sm text-gray-500">Não há a instalação {id} no snapshot. <Link to="/instalacoes" className="text-primario-600 hover:underline">Ver instalações</Link>.</p>
      </div>
    )
  }
  const redes = redesFiltradas
  return (
    <div className="space-y-4" data-testid="pagina-instalacao">
      <div className="space-y-1">
        <p className="text-xs"><Link to="/instalacoes" className="text-primario-600 hover:underline">Instalações</Link></p>
        <h1 className="text-titulo-1 text-gray-900">{f.nome ?? `Instalação ${f.id}`}</h1>
        <p className="text-sm text-gray-600">
          {f.org_nome ?? '—'} · {localDe(f)}{f.escopo === 'ptt_externo' ? ' (fora do Brasil, listada por abrigar um PTT externo)' : ''}
        </p>
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <SeloCadastro c={f.cadastro} />
          <span>registro criado em {dataCurta(f.criado)}, atualizado em {dataCurta(f.atualizado)}</span>
          {f.site && /^https?:\/\//i.test(f.site) ? <a href={f.site} target="_blank" rel="noreferrer nofollow" className="text-primario-600 hover:underline">site</a> : null}
          <a href={`https://www.peeringdb.com/fac/${f.id}`} target="_blank" rel="noreferrer" className="text-primario-600 hover:underline">ver no PeeringDB</a>
        </div>
      </div>

      {f.lat != null && f.lon != null && <MapaInstalacoes altura={260} itens={[{ id: f.id, nome: f.nome, org_nome: f.org_nome, cidade: f.cidade, uf: f.uf, pais: f.pais, lat: f.lat, lon: f.lon, n_redes: f.n_redes, n_ptts: f.ixps.length, n_carriers: f.carriers.length, cadastro: f.cadastro }]} />}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        {[
          ['Redes (coletadas)', f.escopo === 'brasil' ? n(f.n_redes) : '—'], ['Redes do Brasil', f.escopo === 'brasil' ? n(f.n_redes_br) : '—'],
          ['Redes (cadastro informa)', n(f.redes_declaradas)], ['PTTs', n(f.ixps.length)],
        ].map(([rotulo, valor]) => (
          <div key={rotulo} className="bg-white rounded-lg border border-gray-200 px-3 py-2"><div className="text-xs text-gray-500">{rotulo}</div><div className="text-lg font-semibold tabular-nums">{valor}</div></div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 space-y-1" data-testid="ptts-instalacao">
        <h2 className="text-base font-semibold text-gray-800">PTTs na instalação</h2>
        {f.ixps.length === 0 ? <p className="text-sm text-gray-500">Nenhum PTT cadastrado.</p> : <ul className="text-sm list-disc pl-5">{f.ixps.map((p) => <li key={p.ix_id}><PttRotulo p={p} /></li>)}</ul>}
        {f.campus && <p className="text-xs text-gray-500 pt-1">Campus: {f.campus.nome} ({[f.campus.cidade, f.campus.uf ?? f.campus.pais].filter(Boolean).join(' / ')})</p>}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 space-y-1" data-testid="carriers-instalacao">
        <h2 className="text-base font-semibold text-gray-800">Carriers ({n(f.carriers.length)})</h2>
        {f.carriers.length === 0 ? <p className="text-sm text-gray-500">Nenhum carrier cadastrado.</p> : (
          <ul className="text-sm columns-1 sm:columns-2">{f.carriers.map((c) => <li key={c.id}>{c.nome ?? `Carrier ${c.id}`}{c.org_nome && c.org_nome !== c.nome ? <span className="text-xs text-gray-500"> · {c.org_nome}</span> : null}</li>)}</ul>
        )}
      </div>

      {f.redes_perfil && (resumoPtts.length > 0 || f.redes_perfil.ptts_sem_dado_de_sessao.length > 0) && (
        <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 space-y-2" data-testid="interligacao-predio">
          <h2 className="text-base font-semibold text-gray-800">Interligação no prédio</h2>
          {resumoPtts.map((p) => (
            <p key={p.ixp} className="text-sm text-gray-800">
              <Link to={`/ixp/${p.ixp}`} className="text-primario-600 hover:underline">{p.nome} ({p.ixp.toUpperCase()})</Link>: {n(p.redes_do_brasil)} redes do Brasil deste prédio ·{' '}
              {ORDEM_SITUACAO.filter((k) => p[k] > 0).map((k) => `${n(p[k])} ${ROTULO_SITUACAO[k]}`).join(' · ') || 'nenhuma rede do Brasil neste prédio'}
              {Object.values(p.coleta).some((c) => c !== 'ok') ? ` (família sem coleta válida: ${Object.entries(p.coleta).filter(([, c]) => c !== 'ok').map(([a]) => (a === 'v6' ? 'IPv6' : 'IPv4')).join(' e ')})` : ''}
            </p>
          ))}
          {f.redes_perfil.ptts_sem_dado_de_sessao.map((p) => (
            <p key={p.ix_id ?? p.code ?? p.nome} className="text-sm text-gray-600">{p.nome ?? p.code ?? `PTT ${p.ix_id}`}: sem dado de sessão neste site.</p>
          ))}
          <p className="text-xs text-gray-600"><b>Como ler.</b> {f.redes_perfil.nota}</p>
          <LinhaProveniencia selo="fato" fonte="looking glass e cadastro do IX.br (sessão e cadastro); vínculo rede-instalação do PeeringDB" dataRef={f.snapshot_date} />
          <LinhaProveniencia selo="inferido" fonte="regra 'só origina prefixos': prefixo visto no PTT, sem cadastro nem sessão" dataRef={f.snapshot_date} />
          <LinhaProveniencia selo="estimado" fonte="APNIC Labs: usuários estimados por ASN (coluna da tabela de redes)" dataRef={f.snapshot_date} />
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 space-y-2" data-testid="redes-instalacao">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 className="text-base font-semibold text-gray-800">Redes ({n(redes.length)})</h2>
          {f.escopo === 'brasil' && <label className="flex items-center gap-1.5 text-xs text-gray-600"><input type="checkbox" checked={soBr} onChange={(e) => setSoBr(e.target.checked)} /> só ASNs do Brasil</label>}
          {resumoPtts.length > 1 && (
            <label className="flex items-center gap-1.5 text-xs text-gray-600">PTT
              <select value={pttAtivo} onChange={(e) => setPttSel(e.target.value)} className="border border-gray-200 rounded px-1 py-0.5">{resumoPtts.map((p) => <option key={p.ixp} value={p.ixp}>{p.nome}</option>)}</select>
            </label>
          )}
          {resumoPtts.length > 0 && (
            <label className="flex items-center gap-1.5 text-xs text-gray-600">Situação no PTT
              <select value={situacao} onChange={(e) => setSituacao(e.target.value as '' | SituacaoNoPtt)} className="border border-gray-200 rounded px-1 py-0.5">
                <option value="">todas</option>{ORDEM_SITUACAO.map((k) => <option key={k} value={k}>{ROTULO_SITUACAO[k]}</option>)}
              </select>
            </label>
          )}
        </div>
        <p className="text-xs text-gray-500">{f.redes_nota}</p>
        {redes.length > 0 && (
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-xs">
              <caption className="sr-only">Redes que declaram estar nesta instalação no PeeringDB, com a situação em cada PTT do IX.br do prédio quando há dado. A ordem padrão é por ASN.</caption>
              <thead><tr className="text-left text-gray-500 border-b border-gray-100">
                <ThOrdenavel {...props('asn')} className="py-1 pr-3 font-medium">ASN</ThOrdenavel><ThOrdenavel {...props('nome')} className="py-1 pr-3 font-medium">Nome</ThOrdenavel>
                {resumoPtts.length > 0 && <th scope="col" className="py-1 pr-3 font-medium text-right">Usuários (estimado, APNIC)<Dica rotulo="Usuários estimados" texto="Estimativa do APNIC Labs por ASN, não é contagem de clientes; vazio quando não há estimativa. Esta coluna não ordena a tabela." /></th>}
                {resumoPtts.length > 0 && <th scope="col" className="py-1 pr-3 font-medium">IPv6<Dica rotulo="IPv6" texto="O ASN tem IPv6 alocado, anunciado ou visto em um PTT; não mede uso." /></th>}
                {resumoPtts.map((p) => <th key={p.ixp} scope="col" className="py-1 pr-3 font-medium">Em {p.ixp.toUpperCase()}</th>)}
                <ThOrdenavel {...props('desde')} className="py-1 font-medium">Vínculo desde</ThOrdenavel></tr></thead>
              <tbody className="divide-y divide-gray-50">
                {ordenados.slice(0, 500).map((r) => (
                  <tr key={r.asn}><td className="py-1 pr-3"><Link to={`/asn/${r.asn}`} className="text-primario-600 hover:underline">AS{r.asn}</Link></td><td className="py-1 pr-3 text-gray-700">{r.nome ?? '—'}</td>
                    {resumoPtts.length > 0 && <td className="py-1 pr-3 text-right tabular-nums">{r.is_br ? (r.usuarios_apnic != null ? n(r.usuarios_apnic) : 'sem estimativa') : ''}</td>}
                    {resumoPtts.length > 0 && <td className="py-1 pr-3">{r.is_br ? (r.ipv6 == null ? '—' : r.ipv6 ? 'sim' : 'não') : ''}</td>}
                    {resumoPtts.map((p) => <td key={p.ixp} className="py-1 pr-3">{r.situacao ? ROTULO_SITUACAO[r.situacao[p.ixp]] : 'fora do Brasil: sem dado'}</td>)}
                    <td className="py-1 tabular-nums">{dataCurta(r.no_vinculo_desde)}</td></tr>
                ))}
              </tbody>
            </table>
            {redes.length > 500 && <p className="text-xs text-gray-400 pt-1">Mostrando 500 de {n(redes.length)}.</p>}
          </div>
        )}
      </div>
      <AtribuicaoPeeringDb meta={f} />
    </div>
  )
}
