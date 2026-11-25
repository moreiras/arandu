// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Navigate, useSearchParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchOmissaoSici, fetchRankingOperadoras, fetchRankingRouteServers } from '../services/api'
import { useAuth } from '../auth/AuthContext'
import { UFS, nomeUf } from '../lib/ufs'
import { BarraDeAbas } from '../features/entidade/EntityPage'
import { DICA_PREFIXOS_LIMITE } from '../lib/textos'
import { Dica } from '../components/ui/Dica'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados } from '../components/ui/EstadoDados'
import { PreviaLista } from '../components/ui/PreviaLista'
import { PREVIEW_LIMIT } from '../auth/accessPolicy'
import { alternarOrdem, type Ordem } from '../lib/ordenacao'

const POR_PAGINA = 25
const POR_PAGINA_RANK = 25
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`)

const ABAS = [
  { id: 'operadoras', rotulo: 'Operadoras' },
  { id: 'omissao', rotulo: 'Sem declaração ao SICI' },
  { id: 'route-servers', rotulo: 'Route servers' },
] as const
type Aba = (typeof ABAS)[number]['id']

const ORDENS_OPERADORA: Record<string, string> = {
  acessos: 'Acessos declarados', share: 'Parcela dos acessos', var_aa_pct: 'Variação em 12 meses (%)', var_mm_pct: 'Variação no mês (%)', declinio: 'Meses seguidos de queda',
}
const CRITERIOS_RS: Record<string, string> = {
  sessoes_down: 'Sessões down (número absoluto)', dias_down: 'Maior tempo de queda de uma sessão (dias)', uso_limite: 'Prefixos recebidos ÷ limite de importação (max-prefix)', sessoes: 'Sessões do membro no PTT',
}
const razao = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const CLASSES: Record<string, string> = { com_usuarios_apnic: 'com usuários estimados (APNIC)', sem_usuarios: 'sem usuários estimados', nao_comparavel: 'sem ASN no CNPJ' }

/**
 * `/rankings` — Rankings do SICI e outorgas sem declaração. Só dado declarado ou medido, com o critério e o mês de referência à vista, sem juízo
 * de valor (política editorial). Sem login vale a prévia da API (as 100 primeiras linhas, página 1); a lista inteira, paginada de 25 em 25, exige login.
 */
export function RankingsPage() {
  // as três abas territoriais são a lista de municípios: o link continua respondendo (regra 8 do AGENTS.md) e leva à lente certa
  const [params] = useSearchParams()
  const lente = ALIAS_LENTE[params.get('aba') ?? '']
  if (lente) {
    const q = new URLSearchParams(params); q.delete('aba'); q.set('lente', lente)
    return <Navigate to={`/municipios?${q.toString()}`} replace />
  }
  // As outras três abas moram em outras páginas: operadoras e omissão em /operadoras, route servers em /ixps. O link continua respondendo.
  const q = new URLSearchParams(params); const aba = q.get('aba'); q.delete('aba')
  const resto = q.toString() ? `&${q.toString()}` : ''
  if (aba === 'route-servers') return <Navigate to={`/ixps?visao=route-servers${resto}`} replace />
  return <Navigate to={`/operadoras?visao=${aba === 'omissao' ? 'omissao' : 'ranking'}${resto}`} replace />
}

const ALIAS_LENTE: Record<string, string> = { municipios: 'mercado', penetracao: 'penetracao', 'sem-ptt': 'sem-ptt' }

/** O ranking do SICI, a omissão de declaração ou o ranking de route servers (`abaFixa`), embutido na página que hospeda cada um; a página hospedeira põe o título e as abas. */
export function RankingsSici({ abaFixa }: { abaFixa: Aba }) {
  return <RankingsConteudo abaFixa={abaFixa} />
}

function RankingsConteudo({ abaFixa }: { abaFixa?: Aba }) {
  const [sp, setSp] = useSearchParams()
  const { anon, requireLogin } = useAuth()
  // Sem login a primeira página tem até PREVIEW_LIMIT linhas (D9); com login, 25 por vez.
  const porPagina = anon ? PREVIEW_LIMIT : POR_PAGINA
  const porPaginaRank = anon ? PREVIEW_LIMIT : POR_PAGINA_RANK
  const aba = (abaFixa ?? ABAS.find((a) => a.id === sp.get('aba'))?.id ?? 'operadoras') as Aba
  const uf = sp.get('uf') ?? ''
  const ordem = sp.get('ordem') ?? ''
  const asc = sp.get('asc') === '1'
  const classe = sp.get('classe') ?? ''
  const criterioRs = sp.get('criterio') ?? 'sessoes_down'
  const ixpRs = sp.get('ixp') ?? ''
  const soDown = sp.get('down') === '1'
  const tipo = sp.get('tipo') === 'parou' ? 'parou_de_declarar' : 'outorga_sem_declaracao'
  const pagina = Math.max(1, Number(sp.get('p') ?? 1) || 1)
  const muda = (k: string, v: string) => { const q = new URLSearchParams(sp); if (v) q.set(k, v); else q.delete(k); if (k !== 'p') q.delete('p'); setSp(q, { replace: true }) }
  const trocaAba = (a: Aba) => setSp(new URLSearchParams({ aba: a }), { replace: true })
  const embutido = !!abaFixa
  // Ordem pelo cabeçalho: vai à API (lista paginada), que ordena a lista inteira antes de cortar a página.
  const ordemOp: Ordem = { campo: ordem || 'acessos', dir: asc ? 'asc' : 'desc' }
  const ordenaOp = (campo: string) => {
    const o = alternarOrdem(ordemOp, campo, 'desc')
    const q = new URLSearchParams(sp)
    if (o.campo === 'acessos') q.delete('ordem'); else q.set('ordem', o.campo)
    if (o.dir === 'asc') q.set('asc', '1'); else q.delete('asc')
    q.delete('p'); setSp(q, { replace: true })
  }
  const thOp = (campo: string) => ({ campo, ordem: ordemOp, onOrdenar: ordenaOp })
  // A API dos route servers só ordena do maior para o menor: o cabeçalho troca o critério, não inverte o sentido.
  const thRs = (campo: string) => ({ campo, ordem: { campo: criterioRs, dir: 'desc' } as Ordem, onOrdenar: (c: string) => muda('criterio', c === 'sessoes_down' ? '' : c) })

  const base = { retry: false, staleTime: 5 * 60 * 1000 }
  const ops = useQuery({ queryKey: ['rank-op', uf, ordem, asc, pagina], enabled: aba === 'operadoras', ...base,
    queryFn: () => fetchRankingOperadoras({ uf: uf || undefined, ordem: ordem || undefined, asc: asc || undefined, limit: porPagina, page: pagina }) })
  const om = useQuery({ queryKey: ['rank-om', tipo, uf, classe, pagina], enabled: aba === 'omissao', ...base,
    queryFn: () => fetchOmissaoSici({ tipo, uf: uf || undefined, classe: classe || undefined, limit: porPagina, page: pagina }) })
  const rsq = useQuery({ queryKey: ['rank-rs', criterioRs, ixpRs, soDown, pagina], enabled: aba === 'route-servers', ...base,
    queryFn: () => fetchRankingRouteServers({ criterio: criterioRs, ixp: ixpRs || undefined, apenas_down: soDown || undefined, limit: porPaginaRank, page: pagina }) })
  const ativa = aba === 'operadoras' ? ops : aba === 'omissao' ? om : rsq
  const dados = ativa.data
  const total = dados?.total ?? 0

  return (
    <div className="space-y-5">
      {!embutido && <div>
        <h1 className="text-titulo-1 text-gray-900">Rankings do SICI</h1>
        <p className="text-sm text-gray-500 mt-1">
          Operadoras e municípios ordenados por um critério de dado <strong>declarado</strong> à Anatel (SICI, banda larga fixa) e as outorgas SCM que não têm acessos
          declarados no mês. Os rankings de municípios (mercado, penetração, sem PTT a 100 km) estão em <Link to="/municipios" className="text-primario-600 hover:underline">Municípios</Link>. Cada lista mostra o critério, o mês de referência e a data do snapshot; a ordem não mede qualidade nem tamanho de rede.
        </p>
      </div>}
      {!embutido && <BarraDeAbas abas={ABAS} ativa={aba} aoEscolher={(id) => trocaAba(id as Aba)} rotulo="Rankings" />}
      <div {...(embutido ? {} : { role: 'tabpanel', id: `painel-${aba}`, 'aria-labelledby': `aba-${aba}` })} className="space-y-5">
      <div className="flex flex-wrap items-end gap-3 text-sm">
        {aba !== 'route-servers' && <label className="flex flex-col gap-0.5">
          <span className="text-xs text-gray-500">UF</span>
          <select value={uf} onChange={(e) => muda('uf', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
            <option value="">Brasil</option>
            {Object.keys(UFS).map((u) => <option key={u} value={u}>{u} — {nomeUf(u)}</option>)}
          </select>
        </label>}
        {aba === 'route-servers' && (
          <>
            <label className="flex flex-col gap-0.5">
              <span className="text-xs text-gray-500">Ordenar por</span>
              <select value={criterioRs} onChange={(e) => muda('criterio', e.target.value === 'sessoes_down' ? '' : e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
                {Object.entries(CRITERIOS_RS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-0.5">
              <span className="text-xs text-gray-500">PTT (código)</span>
              <input value={ixpRs} onChange={(e) => muda('ixp', e.target.value.trim().toLowerCase())} placeholder="todos (ex.: sp)" className="border border-gray-200 rounded px-2 py-1 bg-white w-32" />
            </label>
            <label className="flex items-center gap-1.5 pb-1"><input type="checkbox" checked={soDown} onChange={(e) => muda('down', e.target.checked ? '1' : '')} />
              <span>Só quem tem todas as sessões down há 7 dias ou mais</span></label>
          </>
        )}
        {aba !== 'omissao' && aba !== 'route-servers' && (
          <>
            <label className="flex flex-col gap-0.5">
              <span className="text-xs text-gray-500">Ordenar por</span>
              <select value={ordem || 'acessos'} onChange={(e) => muda('ordem', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
                {Object.entries(ORDENS_OPERADORA).map(([k, v]) => (
                  <option key={k} value={k} disabled={!!uf && k !== 'acessos' && k !== 'share' && k !== 'declinio'}>{v}</option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5 pb-1"><input type="checkbox" checked={asc} onChange={(e) => muda('asc', e.target.checked ? '1' : '')} /><span>Ordem crescente</span></label>
          </>
        )}
        {aba === 'omissao' && (
          <>
            <label className="flex flex-col gap-0.5">
              <span className="text-xs text-gray-500">Mostrar</span>
              <select value={tipo === 'parou_de_declarar' ? 'parou' : 'outorga'} onChange={(e) => muda('tipo', e.target.value === 'parou' ? 'parou' : '')} className="border border-gray-200 rounded px-2 py-1 bg-white">
                <option value="outorga">Outorgas SCM sem acessos declarados</option>
                <option value="parou">CNPJs que pararam de declarar</option>
              </select>
            </label>
            {tipo === 'outorga_sem_declaracao' && (
              <label className="flex flex-col gap-0.5">
                <span className="text-xs text-gray-500">Classe</span>
                <select value={classe} onChange={(e) => muda('classe', e.target.value)} className="border border-gray-200 rounded px-2 py-1 bg-white">
                  <option value="">Todas</option>
                  {Object.entries(CLASSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
            )}
          </>
        )}
      </div>
      {dados && (
        <p className="text-xs text-gray-500" data-testid="rotulo-ranking">
          Critério: {dados.criterio}. {'coletado_em' in dados ? `Route servers do IX.br, coletado em ${dados.coletado_em?.slice(0, 10) ?? '—'}` : `Declaração de ${dados.mes_referencia}`} · snapshot {dados.snapshot_date} · {total.toLocaleString('pt-BR')} resultados.
        </p>
      )}
      {ativa.isLoading && <p className="text-sm text-gray-400" role="status">Carregando…</p>}
      {ativa.isError && <EstadoDados erro={ativa.error} oQue="a lista" mensagem="Esta lista não está publicada neste snapshot." aoTentarDeNovo={() => void ativa.refetch()} />}
      {aba === 'operadoras' && ops.data && (
        <Tabela legenda="Operadoras por acessos fixos declarados (SICI)" cab={['#', 'Operadora', 'Acessos', 'Parcela', ...(uf ? [] : ['12 meses', 'Queda seguida'])]}
          ord={{ Acessos: thOp('acessos'), Parcela: thOp('share'), '12 meses': thOp('var_aa_pct'), 'Queda seguida': thOp('declinio') }}>
          {ops.data.items.map((r) => (
            <tr key={r.cnpj}>
              <td className="px-2 py-1 text-gray-400 tabular-nums">{r.posicao}</td>
              <td className="px-2 py-1"><Link to={`/operadora/${r.cnpj}`} className="text-primario-600 hover:underline">{r.empresa}</Link> <span className="text-xs text-gray-400">{r.uf_sede}</span></td>
              <td className="px-2 py-1 text-right tabular-nums">{n(r.acessos)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{r.share.toLocaleString('pt-BR', { maximumFractionDigits: 3 })}%</td>
              {!uf && <td className="px-2 py-1 text-right tabular-nums">{pct(r.var_aa_pct)}</td>}
              {!uf && <td className="px-2 py-1 text-right tabular-nums">{r.meses_declinio > 0 ? `${r.meses_declinio} meses` : '—'}</td>}
            </tr>
          ))}
        </Tabela>
      )}
      {aba === 'route-servers' && rsq.data && (
        <>
          <Tabela legenda="Sessões nos route servers do IX.br por membro" cab={['#', 'Membro', 'PTT', 'Sessões up', 'Down', 'Maior tempo de queda (dias)', 'Prefixos / limite']} dicas={{ 'Prefixos / limite': DICA_PREFIXOS_LIMITE }}
            ord={{ Down: thRs('sessoes_down'), 'Maior tempo de queda (dias)': thRs('dias_down'), 'Prefixos / limite': thRs('uso_limite') }}>
            {rsq.data.items.map((r) => (
              <tr key={`${r.ixp}-${r.asn}`}>
                <td className="px-2 py-1 text-gray-400 tabular-nums">{r.posicao}</td>
                <td className="px-2 py-1"><Link to={`/asn/${r.asn}`} className="text-primario-600 hover:underline">AS{r.asn}</Link> <span className="text-xs text-gray-500">{r.nome ?? ''}</span></td>
                <td className="px-2 py-1"><Link to={`/ixp/${r.ixp}`} className="text-primario-600 hover:underline">{r.ixp.toUpperCase()}</Link></td>
                <td className="px-2 py-1 text-right tabular-nums">{n(r.up)} de {n(r.sessoes)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(r.down_certo)}{r.down > r.down_certo ? <span className="text-xs text-gray-400"> (+{n(r.down - r.down_certo)} em RS sem frescor confirmado)</span> : null}</td>
                <td className="px-2 py-1 text-right tabular-nums">{r.max_dias_down != null ? n(r.max_dias_down) : '—'}</td>
                <td className="px-2 py-1 text-right tabular-nums">{r.max_uso_limite != null ? `${Math.round(r.max_uso_limite * 100)}%` : '—'}</td>
              </tr>
            ))}
          </Tabela>
          <p className="text-xs text-gray-500">{rsq.data.limites} Sessões de route server cujo cache de vizinhos no Alice tem mais de 24 h, ou que não foi consultado, ficam fora da contagem de sessões down e do tempo de queda. Coletado em {rsq.data.coletado_em?.slice(0, 16).replace('T', ' ')} UTC.</p>
        </>
      )}
      {aba === 'omissao' && om.data && tipo === 'outorga_sem_declaracao' && (
        <Tabela legenda="Outorgas SCM sem acessos declarados" cab={['#', 'Outorgada (SCM)', 'UF', 'Usuários estimados (APNIC)', 'Classe', 'Grupo']}>
          {om.data.items.map((r) => (
            <tr key={r.cnpj}>
              <td className="px-2 py-1 text-gray-400 tabular-nums">{r.posicao}</td>
              <td className="px-2 py-1"><Link to={`/operadora/${r.cnpj}`} className="text-primario-600 hover:underline">{r.razao_social}</Link></td>
              <td className="px-2 py-1 text-xs">{r.uf}</td>
              <td className="px-2 py-1 text-right tabular-nums">{n(r.usuarios_apnic)}</td>
              <td className="px-2 py-1 text-xs">{r.classe ? CLASSES[r.classe] : ''}</td>
              <td className="px-2 py-1 text-xs text-gray-500">{r.grupo_declara ? 'outro CNPJ do grupo declarou' : ''}</td>
            </tr>
          ))}
        </Tabela>
      )}
      {aba === 'omissao' && om.data && tipo === 'parou_de_declarar' && (
        <Tabela legenda="CNPJs que pararam de declarar" cab={['#', 'CNPJ', 'Último mês declarado', 'Meses sem declarar', 'Acessos no último mês']}>
          {om.data.items.map((r) => (
            <tr key={r.cnpj}>
              <td className="px-2 py-1 text-gray-400 tabular-nums">{r.posicao}</td>
              <td className="px-2 py-1"><Link to={`/operadora/${r.cnpj}`} className="text-primario-600 hover:underline">{r.empresa || r.cnpj}</Link></td>
              <td className="px-2 py-1 tabular-nums">{r.ultimo_mes_declarado}</td>
              <td className="px-2 py-1 text-right tabular-nums">{n(r.meses_sem_declarar)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{n(r.acessos_no_ultimo_mes)}</td>
            </tr>
          ))}
        </Tabela>
      )}
      {dados && total > POR_PAGINA && (
        anon ? (
          <PreviaLista mostradas={(dados as { items?: unknown[] }).items?.length ?? 0} total={total} aoEntrar={() => requireLogin('lista-expandida')} className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" />
        ) : (
          <div className="flex items-center gap-3 text-sm">
            <button disabled={pagina === 1} onClick={() => muda('p', String(pagina - 1))} className="px-2 py-1 border rounded disabled:opacity-40">Anterior</button>
            <span className="text-gray-500">Página {pagina} de {Math.ceil(total / POR_PAGINA)}</span>
            <button disabled={pagina * POR_PAGINA >= total} onClick={() => muda('p', String(pagina + 1))} className="px-2 py-1 border rounded disabled:opacity-40">Próxima</button>
          </div>
        )
      )}
      <details className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
        <summary className="cursor-pointer text-gray-700">Como ler estas listas</summary>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Acessos são <strong>autodeclarados</strong> pelas operadoras ao SICI (Anatel), por CNPJ. Parcela e HHI são sobre acessos declarados, não sobre receita.</li>
          <li>"Sem declaração" diz só que o CNPJ tem outorga SCM e não tem acessos declarados no mês de referência. Não indica causa nem intenção.</li>
          <li>Os usuários são <strong>estimados</strong> pela APNIC por medição estatística, somados nos ASNs do CNPJ. A classe "sem ASN" quer dizer que não há como observar usuários.</li>
          <li>"Outro CNPJ do grupo declarou" usa os grupos societários (Receita Federal); grupo parcial não prova controle.</li>
          <li>Penetração = acessos fixos declarados ÷ domicílios do Censo 2022 projetados para o ano mais recente da PNAD pelo crescimento de domicílios da UF (aproximação: vale igual para todos os municípios dela); passa de 1 quando há mais de um acesso por domicílio. "Não visto" é <strong>estimativa</strong>: domicílios projetados × taxa de internet da UF (PNAD) − acessos de pessoa física, e inclui quem usa só o celular. A distância ao PTT é em linha reta do centróide do município.</li>
          <li>Janelas: "queda seguida" = 6 meses seguidos; "pararam de declarar" = 6 meses ou mais sem declaração e declaração nos últimos 36 meses.</li>
          <li>Para corrigir um dado, use o <a href="/sobre#contato" className="text-primario-600 hover:underline">contato da página Sobre</a>; a correção vale no próximo snapshot.</li>
        </ul>
      </details>
      </div>
    </div>
  )
}

type PropsOrdem = { campo: string; ordem: Ordem; onOrdenar: (campo: string) => void }

/** Cabeçalho ordenável com a dica fora do botão (botão dentro de botão não é permitido). */
function ThOrdenavelComDica({ o, rotulo, dica, className }: { o: PropsOrdem; rotulo: string; dica: string; className: string }) {
  const sentido = o.ordem.campo === o.campo ? o.ordem.dir : null
  return (
    <th scope="col" className={className} aria-sort={sentido === 'asc' ? 'ascending' : sentido === 'desc' ? 'descending' : 'none'}>
      <span className="inline-flex items-baseline justify-end gap-0.5">
        <button type="button" onClick={() => o.onOrdenar(o.campo)} className="inline-flex items-center gap-0.5 rounded hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
          <span>{rotulo}</span>
          <span aria-hidden="true" className={sentido ? 'text-primario-700' : 'text-gray-300'}>{sentido === 'asc' ? '▲' : sentido === 'desc' ? '▼' : '↕'}</span>
        </button>
        <Dica texto={dica} rotulo={rotulo} />
      </span>
    </th>
  )
}

function Tabela({ cab, dicas = {}, ord = {}, legenda, children }: { cab: string[]; dicas?: Record<string, string>; ord?: Record<string, PropsOrdem>; legenda: string; children: React.ReactNode }) {
  const th = (c: string, i: number) => {
    const cls = `px-2 py-1.5 font-medium ${i > 1 ? 'text-right' : 'text-left'}`
    const o = ord[c]
    if (o && dicas[c]) return <ThOrdenavelComDica key={c} o={o} rotulo={c} dica={dicas[c]} className={cls} />
    if (o) return <ThOrdenavel key={c} {...o} alinhar={i > 1 ? 'right' : 'left'} className={cls}>{c}</ThOrdenavel>
    return <th key={c} scope="col" className={cls}>{c}{dicas[c] && <Dica texto={dicas[c]} rotulo={c} />}</th>
  }
  return (
    <div className="overflow-x-auto bg-white border border-gray-200 rounded-lg">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{legenda}</caption>
        <thead className="bg-gray-50 text-xs text-gray-500"><tr>{cab.map(th)}</tr></thead>
        <tbody className="divide-y divide-gray-100">{children}</tbody>
      </table>
    </div>
  )
}
