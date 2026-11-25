// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchRankingMunicipios, fetchTerritorioRanking, fetchTerritorioResumo } from '../services/api'
import { useAuth } from '../auth/AuthContext'
import { MapaSobDemanda } from '../features/estados/MapaSobDemanda'
import { UFS, nomeUf } from '../lib/ufs'
import { BarraDeAbas } from '../features/entidade/EntityPage'
import { Dica } from '../components/ui/Dica'
import { ComoLer } from '../components/ui/ComoLer'
import { EstadoDados } from '../components/ui/EstadoDados'
import { rotuloPix } from '../lib/geo'
import { AvisosRecorte } from '../components/ui/AvisoRecorte'
import { useActiveDate } from '../hooks/useSnapshot'
import { SinteseTopo } from '../components/ui/SinteseTopo'
import { REGRAS_SINTESE_MUNICIPIOS, sinteseMunicipios } from '../features/territorio/sinteseMunicipios'

const POR_PAGINA = 25
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`)
const razao = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

// Explicação por coluna (Dica); definições do catálogo da consulta (`municipios`, `sici_municipios`).
// Terceiro item: a chave de ordenação aceita pela API (`ordem` de /sici/municipios ou `campo` de /territorio/ranking); sem chave, a coluna não ordena.
const CAB_MERCADO: [string, string | undefined, string?][] = [
  ['Acessos', 'Acessos fixos declarados ao SICI (Anatel) no mês de referência.', 'acessos'],
  ['HHI', 'Índice de Herfindahl-Hirschman: soma dos quadrados das participações (%) das operadoras nos acessos do município, de 0 a 10.000. Quanto maior, mais concentrado.', 'hhi'],
  ['Operadoras', 'Operadoras (CNPJ) que declararam acessos fixos no município.', 'n_operadoras'],
  ['12 meses', 'Variação dos acessos contra o mesmo mês do ano anterior.', 'var_aa_pct'],
  ['Líder', 'Operadora com mais acessos no município e a sua participação.'],
]
const CAB_TERRITORIO: [string, string | undefined, string?][] = [
  ['População est.', 'População estimada pelo IBGE (1º de julho do ano mais recente).', 'populacao_estimada'],
  ['Domicílios (proj.)', 'Estimativa: domicílios do Censo 2022 × crescimento de domicílios da UF na PNAD. É a base da penetração.', 'domicilios_projetados'],
  ['Acessos fixos', 'Acessos fixos declarados ao SICI (Anatel) no mês de referência.', 'acessos'],
  ['Por domicílio', 'Acessos fixos ÷ domicílios projetados. Pode passar de 1: acesso não é domicílio, e há acessos de empresas.', 'penetracao'],
  ['Sem acesso fixo PF (est.)', 'Estimativa de domicílios com Internet sem acesso fixo de pessoa física (taxa da PNAD, não a da TIC): domicílios projetados × taxa de Internet da UF (PNAD) − acessos de pessoa física. Inclui quem usa só o celular.', 'nao_visto'],
  ['Fibra', 'Parcela dos acessos fixos em fibra óptica.', 'fibra_pct'],
  ['Reclam. /100 mil', 'Reclamações na Anatel no último ano completo ÷ população × 100 mil; só municípios com 30 ou mais reclamações.', 'reclam_100mil'],
  ['Redes com sede (inferido)', 'ASNs brasileiros cuja organização tem sede no município (pelo CNPJ), quantos têm sessão direta em PTT do IX.br e quantos têm rotas vistas num PTT (que podem chegar por trânsito de outro AS). Sede não é área de operação; a contagem não é ranking de cidades.'],
  ['Ponto de interconexão mais próximo', 'Distância do centróide do município ao PIX (local de interconexão) mais próximo de qualquer PTT do IX.br, em linha reta (inferido). Não mede o caminho da fibra nem o custo; ordena pela distância.', 'km_ptt'],
]
/** Cabeçalho; com `aoOrdenar`, o rótulo vira botão de ordenação (teclado; NBR 17225 5.1.13) e a ordem fica na URL. */
const Th = ({ r, dica, esq, ativa, crescente, aoOrdenar }: { r: string; dica?: string; esq?: boolean; ativa?: boolean; crescente?: boolean; aoOrdenar?: () => void }) => (
  <th scope="col" aria-sort={aoOrdenar ? (ativa ? (crescente ? 'ascending' : 'descending') : 'none') : undefined}
    className={`px-2 py-1.5 font-medium ${esq ? 'text-left' : 'text-right'} ${ativa ? 'bg-primario-50 text-primario-700' : ''}`}>
    <span className={`inline-flex flex-wrap items-center ${esq ? '' : 'justify-end'}`}>
      {aoOrdenar ? (
        <button type="button" onClick={aoOrdenar} className="min-h-6 hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
          {r}<span aria-hidden="true" className={ativa ? 'text-primario-700' : 'text-gray-300'}>{ativa ? (crescente ? ' ▲' : ' ▼') : ' ↕'}</span>
        </button>
      ) : r}
      {dica && <Dica texto={dica} rotulo={r} />}
    </span>
  </th>
)

const LENTES = [
  { id: 'mercado', rotulo: 'Mercado', descricao: 'Acessos declarados, concentração (HHI), operadoras e líder do município.' },
  { id: 'penetracao', rotulo: 'Penetração', descricao: 'Acessos fixos por domicílio e mercado não visto (estimativas).' },
  { id: 'sem-ptt', rotulo: 'Sem PTT a 100 km', descricao: 'Municípios a mais de 100 km em linha reta de um PTT do IX.br.' },
] as const
type Lente = (typeof LENTES)[number]['id']

const ORDENS_MERCADO: Record<string, string> = { acessos: 'Acessos declarados', hhi: 'Concentração (HHI)', n_operadoras: 'Operadoras declarantes', var_aa_pct: 'Variação em 12 meses (%)' }
const CAMPOS_TERRITORIO: Record<string, string> = {
  acessos: 'Acessos fixos declarados', penetracao: 'Acessos fixos por domicílio', penetracao_pf: 'Acessos de pessoa física por domicílio', nao_visto: 'Domicílios sem acesso fixo de pessoa física (estimativa, PNAD)',
  nao_visto_pct: 'Domicílios sem acesso fixo de pessoa física, % dos domicílios (estimativa, PNAD)', domicilios_projetados: 'Domicílios (projeção)', populacao_estimada: 'População estimada',
  fibra_pct: 'Fibra nos acessos fixos (%)', km_ptt: 'Distância ao PTT mais próximo (km)',
  reclam_100mil: 'Reclamações na Anatel por 100 mil hab. (30 ou mais no ano)',
}

/**
 * `/municipios` — a lista de municípios, com três lentes (mercado, penetração, sem PTT a 100 km); os links
 * `/rankings?aba=municipios|penetracao|sem-ptt` redirecionam para cá. Filtro por UF e por porte (domicílios), mapa dos municípios sob demanda e o estado todo na URL.
 * Só dado declarado ou estimado, com o critério à vista; sem login valem os 25 primeiros (a lista inteira exige login, como nos rankings).
 */
export function MunicipiosPage() {
  const [sp, setSp] = useSearchParams()
  const { anon } = useAuth()
  const date = useActiveDate() ?? undefined
  const lente = (LENTES.find((l) => l.id === sp.get('lente'))?.id ?? 'mercado') as Lente
  const uf = sp.get('uf') ?? ''
  const ordem = sp.get('ordem') ?? ''
  const campo = sp.get('campo') ?? (lente === 'sem-ptt' ? 'populacao' : 'penetracao')
  const asc = sp.get('asc') === '1'
  const minDom = Number(sp.get('dom') ?? 1000) || 0
  const pagina = Math.max(1, Number(sp.get('p') ?? 1) || 1)
  // Clique no título: mesma coluna inverte o sentido; coluna nova começa do maior para o menor.
  const ordenar = (chave: string) => {
    const q = new URLSearchParams(sp); const param = lente === 'mercado' ? 'ordem' : 'campo'
    const atual = lente === 'mercado' ? (ordem || 'acessos') : campo
    if (atual === chave) { if (asc) q.delete('asc'); else q.set('asc', '1') } else { q.set(param, chave); q.delete('asc') }
    q.delete('p'); setSp(q, { replace: true })
  }
  const ativaT = (chave: string) => chave === campo || (chave === 'populacao_estimada' && campo === 'populacao')
  const muda = (k: string, v: string) => { const q = new URLSearchParams(sp); if (v) q.set(k, v); else q.delete(k); if (k !== 'p') q.delete('p'); setSp(q, { replace: true }) }
  // Lente nova: ordem, sentido e página são da lente anterior; UF, porte e data do snapshot continuam.
  const trocaLente = (id: string) => {
    const q = new URLSearchParams({ lente: id })
    for (const k of ['uf', 'dom', 'date']) { const v = sp.get(k); if (v) q.set(k, v) }
    setSp(q, { replace: true })
  }
  const base = { retry: false, staleTime: 5 * 60 * 1000 }

  const mercado = useQuery({ queryKey: ['mun-mercado', date, uf, ordem, asc, pagina], enabled: lente === 'mercado', ...base,
    queryFn: () => fetchRankingMunicipios({ date, uf: uf || undefined, ordem: ordem || undefined, asc: asc || undefined, limit: POR_PAGINA, page: pagina }) })
  const terr = useQuery({ queryKey: ['mun-terr', date, lente, uf, campo, asc, minDom, pagina], enabled: lente !== 'mercado', ...base,
    queryFn: () => fetchTerritorioRanking(lente === 'sem-ptt'
      ? { date, uf: uf || undefined, campo, asc: asc || undefined, sem_ptt_proximo: true, min_domicilios: minDom, limit: POR_PAGINA, page: pagina }
      : { date, uf: uf || undefined, campo, asc: asc || undefined, min_domicilios: minDom, limit: POR_PAGINA, page: pagina }) })
  // agregados do país (ou da UF filtrada) para a síntese do topo; a mesma consulta em todas as lentes
  const resumo = useQuery({ queryKey: ['mun-resumo', date, uf], ...base, queryFn: () => fetchTerritorioResumo({ date, uf: uf || undefined }) })
  const ativa = lente === 'mercado' ? mercado : terr
  const total = ativa.data?.total ?? 0
  const descricao = LENTES.find((l) => l.id === lente)!.descricao

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Municípios</h1>
        <p className="text-sm text-gray-500 mt-1">Os municípios do Brasil ordenados por um critério de dado <strong>declarado</strong> à Anatel (SICI, banda larga fixa) ou <strong>estimado</strong> sobre o Censo 2022. A ordem não mede qualidade do serviço.</p>
      </div>
      <SinteseTopo frases={sinteseMunicipios(resumo.data)} snapshot={resumo.data?.snapshot_date} regras={REGRAS_SINTESE_MUNICIPIOS}
        comoLer="Os totais são de todos os municípios da tabela do IBGE, sem o filtro de porte da lista; “longe” é distância em linha reta do centro do município, não o trajeto de fibra." />
      <MapaSobDemanda />
      <BarraDeAbas abas={LENTES} ativa={lente} aoEscolher={trocaLente} rotulo="Lentes da lista" />
      <div role="tabpanel" id={`painel-${lente}`} aria-labelledby={`aba-${lente}`} className="space-y-5">
      <p className="text-sm text-gray-500">{descricao}</p>
      {lente === 'penetracao' && (
        <ComoLer aberto>
          <p>Acessos fixos por domicílio acima de 1 significam mais acessos declarados à Anatel do que domicílios projetados no município. Acesso não é domicílio: um domicílio pode ter vários acessos, e há acessos de empresas (B2B) na conta. Em alguns municípios um único CNPJ concentra a maior parte dos acessos declarados (confira o líder na lente Mercado); a causa não é apurada aqui, e declaração na sede da empresa ou faturamento são hipóteses, não fatos. Valores bem acima de 1 merecem cautela: não indicam população atendida.</p>
        </ComoLer>
      )}
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col gap-0.5"><span className="text-xs text-gray-500">UF</span>
          <select value={uf} onChange={(e) => muda('uf', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
            <option value="">Brasil</option>{Object.keys(UFS).map((u) => <option key={u} value={u}>{u} — {nomeUf(u)}</option>)}
          </select></label>
        {lente !== 'sem-ptt' && (
          <>
            <label className="flex flex-col gap-0.5"><span className="text-xs text-gray-500">Ordenar por</span>
              <select value={lente === 'mercado' ? (ordem || 'acessos') : campo} onChange={(e) => muda(lente === 'mercado' ? 'ordem' : 'campo', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
                {Object.entries(lente === 'mercado' ? ORDENS_MERCADO : CAMPOS_TERRITORIO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select></label>
            <label className="flex items-center gap-1.5 pb-1"><input type="checkbox" checked={asc} onChange={(e) => muda('asc', e.target.checked ? '1' : '')} /><span>Ordem crescente</span></label>
          </>
        )}
        {lente !== 'mercado' && (
          <label className="flex flex-col gap-0.5"><span className="text-xs text-gray-500">Porte (domicílios no município)</span>
            <select value={String(minDom)} onChange={(e) => muda('dom', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
              <option value="0">Todos</option><option value="1000">Pelo menos 1.000</option><option value="5000">Pelo menos 5.000</option><option value="20000">Pelo menos 20.000</option>
            </select></label>
        )}
      </div>
      {ativa.isLoading && <p className="text-sm text-gray-400" role="status">Carregando…</p>}
      {ativa.isError && <EstadoDados erro={ativa.error} oQue="a lista de municípios" mensagem="A lista de municípios não está publicada neste snapshot." aoTentarDeNovo={() => void ativa.refetch()} />}
      {ativa.data && <p className="text-xs text-gray-500">{ativa.data.criterio ?? ''} · {n(total)} municípios · snapshot {ativa.data.snapshot_date}{'mes_referencia' in ativa.data && ativa.data.mes_referencia ? ` · SICI ${ativa.data.mes_referencia}` : ''}</p>}
      {lente === 'mercado' && mercado.data && (
        <div className="overflow-x-auto bg-white border border-gray-200 rounded-lg">
          <table className="min-w-full text-sm" aria-label="Municípios por mercado">
            <thead className="bg-gray-50 text-xs text-gray-500"><tr><Th r="#" esq /><Th r="Município" esq />{CAB_MERCADO.map(([r, d, k]) => <Th key={r} r={r} dica={d} ativa={!!k && k === (ordem || 'acessos')} crescente={asc} aoOrdenar={k ? () => ordenar(k) : undefined} />)}</tr></thead>
            <tbody className="divide-y divide-gray-100">
              {mercado.data.items.map((r) => (
                <tr key={r.ibge}>
                  <td className="px-2 py-1 text-gray-400 tabular-nums">{r.posicao}</td>
                  <td className="px-2 py-1"><Link to={`/municipio/${r.ibge}`} className="text-primario-600 hover:underline">{r.nome}</Link> <span className="text-xs text-gray-400">{r.uf}</span></td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(r.acessos)}</td><td className="px-2 py-1 text-right tabular-nums">{n(r.hhi)}</td><td className="px-2 py-1 text-right tabular-nums">{n(r.n_operadoras)} <AvisosRecorte avisos={r.avisos} /></td>
                  <td className="px-2 py-1 text-right tabular-nums">{pct(r.var_aa_pct)}</td>
                  <td className="px-2 py-1 text-xs text-right">{r.lider ? `${r.lider.empresa} (${r.lider.share.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%)` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {lente !== 'mercado' && terr.data && (
        <>
          <div className="overflow-x-auto bg-white border border-gray-200 rounded-lg">
            <table className="min-w-full text-sm" aria-label="Municípios por território">
              <thead className="bg-gray-50 text-xs text-gray-500"><tr><Th r="#" esq /><Th r="Município" esq />{CAB_TERRITORIO.map(([r, d, k]) => <Th key={r} r={r} dica={d} ativa={!!k && ativaT(k)} crescente={asc} aoOrdenar={k ? () => ordenar(k) : undefined} />)}</tr></thead>
              <tbody className="divide-y divide-gray-100">
                {terr.data.items.map((r) => (
                  <tr key={r.ibge}>
                    <td className="px-2 py-1 text-gray-400 tabular-nums">{r.posicao}</td>
                    <td className="px-2 py-1"><Link to={`/municipio/${r.ibge}`} className="text-primario-600 hover:underline">{r.nome}</Link> <span className="text-xs text-gray-400">{r.uf}</span></td>
                    <td className="px-2 py-1 text-right tabular-nums">{n(r.populacao_estimada ?? r.populacao)}</td><td className="px-2 py-1 text-right tabular-nums">{n(r.domicilios_projetados ?? r.domicilios)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{n(r.acessos)}</td><td className="px-2 py-1 text-right tabular-nums">{razao(r.penetracao)}</td><td className="px-2 py-1 text-right tabular-nums">{n(r.nao_visto)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{r.fibra_pct == null ? '—' : `${r.fibra_pct.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`}</td>
                    <td className="px-2 py-1 text-right tabular-nums" title={r.reclam_ano ? `ano ${r.reclam_ano}` : undefined}>{r.reclam_100mil == null ? '—' : n(Math.round(r.reclam_100mil))}</td>
                    <td className="px-2 py-1 text-xs text-right" data-testid="redes-sede">{r.redes_sede ? (r.redes_sede.asns === 0 ? '0 ASNs' : `${n(r.redes_sede.asns)} ASNs · ${n(r.redes_sede.sessao_ptt)} com sessão em PTT · ${n(r.redes_sede.rotas_ptt)} com rotas vistas em PTT`) : '—'}</td>
                    <td className="px-2 py-1 text-xs text-right">{r.ptt_proximo ? `${rotuloPix(r.pix_proximo)}PTT ${r.ptt_proximo.toUpperCase()} · ${r.km_ptt?.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} km` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500">{terr.data.limites} <strong>Reclamações por 100 mil habitantes:</strong> último ano completo, só municípios com 30 ou mais reclamações (abaixo disso a taxa oscila por acaso e vem como —); depende da adesão ao canal da Anatel e do conhecimento dele, e não mede a qualidade do serviço. Municípios pequenos oscilam mais: use o filtro de porte.</p>
        </>
      )}
      {ativa.data && total > POR_PAGINA && (
        anon ? (
          <p className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2">Sem login você vê os {POR_PAGINA} primeiros. <Link to="/login" className="underline">Entre</Link> para navegar pela lista inteira.</p>
        ) : (
          <div className="flex items-center gap-3 text-sm">
            <button disabled={pagina === 1} onClick={() => muda('p', String(pagina - 1))} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
            <span className="text-gray-500">Página {pagina} de {Math.ceil(total / POR_PAGINA)}</span>
            <button disabled={pagina * POR_PAGINA >= total} onClick={() => muda('p', String(pagina + 1))} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
          </div>
        )
      )}
      <p className="text-xs text-gray-500">Acessos autodeclarados pelas operadoras ao SICI; penetração = acessos fixos ÷ domicílios do Censo 2022 projetados para o ano mais recente da PNAD (aproximação por UF). <Link to="/rankings" className="text-primario-600 hover:underline">Rankings de operadoras</Link>.</p>
      </div>
    </div>
  )
}
