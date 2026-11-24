// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link } from '../../../components/layout/LinkDatado'
import { ASRelationsGraph } from '../../../components/graphs/ASRelationsGraph'
import type { AsnRelacoes, EstratoRelacao, NivelRelacao, RelacaoItem, TransitoAsn } from '../../../types/api'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { SITE } from '../../../lib/site'
import { Dica } from '../../../components/ui/Dica'
import { nomesFamilias } from '../../../lib/familias'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'

const NIVEIS: Record<NivelRelacao, { rotulo: string; classe: string; dica: string }> = {
  declarado: { rotulo: 'declarado', classe: 'bg-mercado-100 text-mercado-800', dica: 'O próprio AS declarou o provedor em um objeto ASPA (RPKI)' },
  confirmado: { rotulo: 'confirmado', classe: 'bg-ok-100 text-ok-800', dica: 'Probabilidade ≥ 95% e pelo menos duas fontes independentes (ASPA, route servers, coletores, topo da hierarquia)' },
  provavel: { rotulo: 'provável', classe: 'bg-primario-100 text-primario-800', dica: 'Probabilidade ≥ 70% e uma fonte independente' },
  possivel: { rotulo: 'possível', classe: 'bg-gray-100 text-gray-700', dica: 'Indício fraco ou só o dataset do CAIDA' },
  sem_classificacao: { rotulo: 'sem classificação', classe: 'bg-gray-50 text-gray-500', dica: 'Elo visto, mas sem evidência suficiente para classificar' },
}

const LIMITE = 10

/** Elos rebaixados de "provável" para "possível" por falta de evidência independente. Só aparecem com o nível `possivel`: um elo `conflito` ou `sem_evidencia`
 * com nível maior (ex.: declarado no ASPA) mantém o selo do nível. */
const REBAIXO: Partial<Record<EstratoRelacao, { rotulo: string; dica: string }>> = {
  sem_evidencia: {
    rotulo: 'possível · sem confirmação',
    dica: `Inferido apenas pelo modelo do ${SITE.nome}, sem confirmação do CAIDA nem das triplas de caminho. Rebaixado de 'provável' para 'possível'.`,
  },
  conflito: {
    rotulo: 'possível · fontes divergem',
    dica: "O CAIDA e as triplas de caminho apontam relações diferentes para este elo. Rebaixado de 'provável' para 'possível'.",
  },
}

function NivelBadge({ nivel, estrato }: { nivel: NivelRelacao; estrato?: EstratoRelacao }) {
  const n = NIVEIS[nivel]
  const r = nivel === 'possivel' && estrato ? REBAIXO[estrato] : undefined
  // T2: a explicação do nível abre no hover, no foco e no toque (o `title` nativo só aparecia com mouse)
  return <span data-estrato={r ? estrato : undefined} className={`inline-block text-xs rounded-full px-2 py-0.5 ${n.classe}`}><Dica texto={r?.dica ?? n.dica}>{r?.rotulo ?? n.rotulo}</Dica></span>
}

const PAPEL = { provedor: 'provedor', cliente: 'cliente', par: 'par' } as const

/** Força do nível para ordenar a coluna (maior = mais evidência). */
const FORCA_NIVEL: Record<NivelRelacao, number> = { declarado: 4, confirmado: 3, provavel: 2, possivel: 1, sem_classificacao: 0 }

/** Níveis que entram no grafo. */
const NIVEIS_GRAFO = new Set<NivelRelacao>(['declarado', 'confirmado', 'provavel'])
const VAZIO: number[] = []
function noGrafo(itens: RelacaoItem[] | undefined, afi: 'v4' | 'v6'): number[] {
  return (itens ?? []).filter((i) => NIVEIS_GRAFO.has(i.nivel) && i.afi.includes(afi)).map((i) => i.asn)
}

/** Relação complexa: v6 e v4 divergem com força; mostra o papel do outro AS em cada família (ARC v2). */
function ListaComplexas({ itens, total }: { itens: RelacaoItem[]; total?: number }) {
  if (itens.length === 0) return null
  return (
    <div data-testid="relacoes-complexas">
      <h3 className="text-sm font-medium text-gray-700 mb-1" title="IPv6 e IPv4 divergem com força (p ≥ 80% e nível ≥ provável nas duas famílias): híbrida = provedor-cliente numa família e par na outra; inversa = o sentido se inverte">
        Relações complexas <span className="text-gray-400 font-normal">({total ?? itens.length})</span>
      </h3>
      <ul className="text-sm divide-y divide-gray-100 border border-gray-100 rounded">
        {itens.map((i) => (
          <li key={i.asn} className="flex items-center gap-2 px-2 py-1">
            <Link to={`/asn/${i.asn}`} className="text-primario-700 hover:underline whitespace-nowrap">AS{i.asn}</Link>
            <span className="text-gray-600 truncate flex-1" title={i.nome}>{i.nome ?? ''}</span>
            <span className="text-xs text-gray-600">{i.subtipo === 'inversa' ? 'inversa' : 'híbrida'}</span>
            <span className="text-xs text-gray-500">IPv6: {i.v6 ? PAPEL[i.v6] : '—'} · IPv4: {i.v4 ? PAPEL[i.v4] : '—'}</span>
            <NivelBadge nivel={i.nivel} estrato={i.estrato} />
          </li>
        ))}
      </ul>
    </div>
  )
}

function Cone({ t }: { t: TransitoAsn }) {
  const ufs = Object.entries(t.cone_ufs ?? {}).sort((a, b) => b[1] - a[1])
  return (
    <div className="text-sm border border-gray-100 rounded px-3 py-2" data-testid="cone-transito">
      <h3 className="text-sm font-medium text-gray-700 mb-1">Clientes inferidos (cone)</h3>
      {t.com_cliente ? (
        <>
          <p>
            <span className="tabular-nums font-medium">{t.clientes_diretos.toLocaleString('pt-BR')}</span> cliente(s) direto(s) · cone de{' '}
            <span className="tabular-nums font-medium">{t.cone_asns.toLocaleString('pt-BR')}</span> ASN(s), <span className="tabular-nums">{t.cone_br.toLocaleString('pt-BR')}</span> do Brasil
            {t.posicao_cone_br ? <span className="text-gray-500"> (posição {t.posicao_cone_br.toLocaleString('pt-BR')} no Brasil)</span> : null}
          </p>
          {ufs.length > 0 && <p className="text-xs text-gray-500">UFs (sede) no cone: {ufs.slice(0, 8).map(([u, n]) => `${u} ${n}`).join(' · ')}{ufs.length > 8 ? ` e mais ${ufs.length - 8}` : ''}</p>}
          <p className="text-xs text-gray-500">Usuários estimados (APNIC) nos ASNs do Brasil do cone: {t.cone_usuarios.toLocaleString('pt-BR')}; repetem-se entre ASNs da mesma operadora.</p>
        </>
      ) : (
        <p className="text-xs text-gray-500">Nenhum cliente inferido (nível provável ou superior) neste snapshot; não quer dizer que o AS não tenha clientes.</p>
      )}
      <p className="text-xs text-gray-400 mt-1">Inferência sobre relações inferidas (snapshot {t.snapshot_date}). {t.limites}</p>
    </div>
  )
}

function Lista({ titulo, itens, total }: { titulo: string; itens: RelacaoItem[]; total?: number }) {
  const [tudo, setTudo] = useState(false)
  if (itens.length === 0) return null
  const visiveis = tudo ? itens : itens.slice(0, LIMITE)
  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-1">{titulo} <span className="text-gray-400 font-normal">({total ?? itens.length})</span></h3>
      <ul className="text-sm divide-y divide-gray-100 border border-gray-100 rounded">
        {visiveis.map((i) => (
          <li key={i.asn} className="flex items-center gap-2 px-2 py-1">
            <Link to={`/asn/${i.asn}`} className="text-primario-700 hover:underline whitespace-nowrap">AS{i.asn}</Link>
            <span className="text-gray-600 truncate flex-1" title={i.nome}>{i.nome ?? ''}</span>
            <span className="text-xs text-gray-500 tabular-nums" title="Probabilidade do modelo (ARC v2); a calibração contra o ASPA está no painel">{Math.round(i.p * 100)}%</span>
            {i.p_calibrada != null && (
              <span data-testid="p-calibrada" className="text-xs text-gray-500 tabular-nums" title="Fração dos elos deste estrato que o ASPA confirmou. Estimada em validação cruzada por AS cliente.">
                calibrada {Math.round(i.p_calibrada * 100)}%
              </span>
            )}
            <NivelBadge nivel={i.nivel} estrato={i.estrato} />
            {i.mudanca_pendente && <span title="Uma mudança desta relação foi vista, mas só vira estado depois de persistir em outra coleta (histerese)" className="text-xs bg-aviso-50 text-aviso-700 rounded-full px-2 py-0.5">mudança pendente</span>}
            <span className="text-xs text-gray-400 w-12 text-right">{nomesFamilias(i.afi, ' ')}</span>
          </li>
        ))}
      </ul>
      {itens.length > LIMITE && (
        <button type="button" className="mt-1 text-xs text-primario-700 hover:underline" onClick={() => setTudo(!tudo)}>
          {tudo ? 'mostrar menos' : `mostrar os ${itens.length}`}
        </button>
      )}
      {total != null && total > itens.length && <p className="text-xs text-gray-400 mt-1">Mostrando {itens.length} de {total}, os de maior confiança.</p>}
    </div>
  )
}

type Papel = 'provedor' | 'cliente' | 'par' | 'mesmo_grupo' | 'complexa'
const ROTULO_PAPEL: Record<Papel, string> = { provedor: 'Provedor', cliente: 'Cliente', par: 'Par', mesmo_grupo: 'Mesmo grupo', complexa: 'Complexa' }

/** Todas as relações num quadro só, filtrável por papel e ordenável por confiança ou por AS: para quem quer comparar, filtrar ou copiar. Mesmos dados e mesmos selos das listas. */
function TabelaRelacoes({ rel }: { rel: AsnRelacoes }) {
  const [papel, setPapel] = useState<'todos' | Papel>('todos')
  // Ordem padrão: confiança do modelo, depois o número do AS. O cabeçalho reordena as linhas recebidas (clientes e pares já vêm limitados
  // aos de maior confiança, como diz a nota abaixo da tabela).
  const base = useMemo(() => [
    ...rel.provedores.map((i) => ({ papel: 'provedor' as Papel, i })), ...rel.clientes.map((i) => ({ papel: 'cliente' as Papel, i })), ...rel.pares.map((i) => ({ papel: 'par' as Papel, i })),
    ...rel.irmaos.map((i) => ({ papel: 'mesmo_grupo' as Papel, i })), ...(rel.complexas ?? []).map((i) => ({ papel: 'complexa' as Papel, i })),
  ].filter((l) => papel === 'todos' || l.papel === papel).sort((a, b) => b.i.p - a.i.p || a.i.asn - b.i.asn), [rel, papel])
  const { ordenados: linhas, ordem, setOrdem, props } = useOrdenacao(base, {
    papel: (l) => ROTULO_PAPEL[l.papel],
    asn: { valor: (l) => l.i.asn, primeiro: 'asc' },
    nome: (l) => l.i.nome,
    nivel: (l) => FORCA_NIVEL[l.i.nivel],
    p: (l) => l.i.p,
    p_calibrada: (l) => l.i.p_calibrada,
    afi: (l) => nomesFamilias(l.i.afi, ' '),
  })
  const ordemSelect = ordem?.campo === 'asn' && ordem.dir === 'asc' ? 'asn' : ordem == null || (ordem.campo === 'p' && ordem.dir === 'desc') ? 'confianca' : ''
  return (
    <div className="space-y-2" data-testid="relacoes-tabela">
      <div className="flex flex-wrap gap-3">
        <label className="text-sm text-gray-600 flex flex-col">Papel
          <select value={papel} onChange={(e) => setPapel(e.target.value as 'todos' | Papel)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
            <option value="todos">Todos</option>{(Object.keys(ROTULO_PAPEL) as Papel[]).map((k) => <option key={k} value={k}>{ROTULO_PAPEL[k]}</option>)}
          </select></label>
        <label className="text-sm text-gray-600 flex flex-col">Ordenar por
          <select value={ordemSelect} onChange={(e) => setOrdem(e.target.value === 'asn' ? { campo: 'asn', dir: 'asc' } : null)} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
            {ordemSelect === '' && <option value="" disabled>Coluna escolhida no cabeçalho</option>}
            <option value="confianca">Confiança do modelo</option><option value="asn">Número do AS</option>
          </select></label>
      </div>
      {linhas.length === 0 ? <p className="text-sm text-gray-500">Nenhuma relação com esse papel neste snapshot.</p> : (
        <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="Relações do AS em tabela" data-tabela="grade">
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200">
            <ThOrdenavel {...props('papel')} className="py-1 pr-3">Papel do outro AS</ThOrdenavel><ThOrdenavel {...props('asn')} className="pr-3">AS</ThOrdenavel>
            <ThOrdenavel {...props('nome')} className="pr-3">Nome</ThOrdenavel><ThOrdenavel {...props('nivel')} className="pr-3">Nível</ThOrdenavel>
            <ThOrdenavel {...props('p')} alinhar="right" className="pr-3 text-right">Probabilidade</ThOrdenavel><ThOrdenavel {...props('p_calibrada')} alinhar="right" className="pr-3 text-right">Calibrada</ThOrdenavel>
            <ThOrdenavel {...props('afi')}>Famílias</ThOrdenavel></tr></thead>
          <tbody>{linhas.map(({ papel: pp, i }) => (
            <tr key={`${pp}-${i.asn}`} className="border-b border-gray-100">
              <td className="py-1 pr-3">{ROTULO_PAPEL[pp]}</td>
              <td className="pr-3"><Link to={`/asn/${i.asn}`} className="text-primario-700 hover:underline">AS{i.asn}</Link></td>
              <td className="pr-3 text-gray-600">{i.nome ?? '—'}</td>
              <td className="pr-3"><NivelBadge nivel={i.nivel} estrato={i.estrato} /></td>
              <td className="pr-3 text-right tabular-nums">{Math.round(i.p * 100)}%</td>
              <td className="pr-3 text-right tabular-nums">{i.p_calibrada != null ? `${Math.round(i.p_calibrada * 100)}%` : '—'}</td>
              <td>{nomesFamilias(i.afi, ' ')}</td>
            </tr>))}</tbody></table></div>
      )}
      <p className="text-xs text-gray-500">Mesmos elos e mesmos níveis das listas; clientes e pares aparecem limitados aos de maior confiança (o total está nas listas). Probabilidade do modelo, não contrato nem acordo comercial.</p>
    </div>
  )
}

function Situacao({ rel, afi }: { rel: AsnRelacoes; afi: 'v4' | 'v6' }) {
  const rotulo = afi === 'v4' ? 'IPv4' : 'IPv6'
  const vis = rel.visibilidade[afi]
  const dica = `Visibilidade: ${vis.vps} pontos de observação, ${vis.ptts} PTTs${vis.coletores ? '' : ' (sem coletores neste snapshot)'}`
  if (rel.single_homed[afi]) return <span title={dica} className="text-xs bg-aviso-100 text-aviso-800 rounded-full px-2 py-0.5">{rotulo}: um só provedor inferido</span>
  if (rel.multihomed[afi]) return <span title={dica} className="text-xs bg-ok-100 text-ok-800 rounded-full px-2 py-0.5">{rotulo}: mais de um provedor inferido</span>
  return <span title={dica} className="text-xs bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">{rotulo}: indeterminado (pouca visibilidade)</span>
}

export function RelacoesBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  const rel = doc.relacoes
  const transito = dados.transito
  const navigate = useNavigate()
  const relationsRef = useRef<HTMLDivElement>(null)
  const [relationsWidth, setRelationsWidth] = useState(520)
  const [vista, setVista] = useState<'listas' | 'tabela'>('listas')
  const grafo = useMemo(() => ({
    v6: { ups: noGrafo(rel?.provedores, 'v6'), dns: noGrafo(rel?.clientes, 'v6') },
    v4: { ups: noGrafo(rel?.provedores, 'v4'), dns: noGrafo(rel?.clientes, 'v4') },
  }), [rel])
  useLayoutEffect(() => {
    const el = relationsRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      setRelationsWidth(Math.min(Math.floor(entries[0].contentRect.width), 520))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return (
    <div>
      {rel && (
        <div className="mb-6">
          <p className="text-xs text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-1.5 mb-3 inline-block">
            Relações inferidas ({rel.algoritmo}) a partir da rampa dos route servers do IX.br, de caminhos de coletores públicos, do ASPA e do
            CAIDA, com abstenção abaixo de 50% e mudança só confirmada depois de persistir em outra coleta. A probabilidade e o nível indicam a confiança
            ({rel.p_calibrada && (rel.p_calibrada.v4 || rel.p_calibrada.v6) ? 'probabilidade calibrada contra o ASPA, que é pequeno e incompleto' : 'probabilidade ainda NÃO calibrada contra o ASPA'});
            não são contratos nem acordos comerciais verificados.
          </p>
          <details className="text-xs text-gray-600 mb-3" data-testid="como-ler-niveis">
            <summary className="cursor-pointer text-gray-700">Como ler os níveis, "possível · …" e a probabilidade calibrada</summary>
            <p className="mt-1">
              <strong>Possível · sem confirmação:</strong> neste elo nenhuma fonte além do próprio modelo aponta o mesmo sentido de relação. Na comparação com o ASPA
              (só ASes que publicam ASPA), poucos desses elos concordaram. Trate como hipótese a verificar, não como fato.
            </p>
            <p className="mt-1">
              <strong>Possível · fontes divergem:</strong> quando o CAIDA e as triplas de caminho divergem, o sentido da relação é incerto: pode ser relação mista (como a híbrida),
              dado desatualizado de uma das fontes ou erro da inferência. A divergência em si é informação.
            </p>
            <p className="mt-1">
              <strong>Probabilidade calibrada:</strong> é a taxa de acerto observada para elos como este (mesmo estrato de evidência) na comparação com o ASPA. Limites: o ASPA cobre só ASes
              que o declaram e pode não representar a Internet toda; e a taxa é do estrato, não do elo. Não é uma probabilidade garantida de este elo estar certo.
            </p>
            <p className="mt-1">CAIDA e as triplas usam os mesmos coletores BGP do {SITE.nome}; só o ASPA é referência independente.</p>
          </details>
          <div className="flex flex-wrap gap-2 mb-3">
            <Situacao rel={rel} afi="v6" />
            <Situacao rel={rel} afi="v4" />
          </div>
          <div role="group" aria-label="Forma de mostrar as relações" className="flex gap-1 mb-3">
            {([['listas', 'Listas'], ['tabela', 'Tabela']] as const).map(([id, rot]) => (
              <button key={id} type="button" aria-pressed={vista === id} onClick={() => setVista(id)}
                className={`px-3 py-1 text-sm rounded border ${vista === id ? 'bg-primario-600 text-white border-primario-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}>{rot}</button>
            ))}
          </div>
          {vista === 'tabela' ? <TabelaRelacoes rel={rel} /> : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Lista titulo="Provedores" itens={rel.provedores} />
                <Lista titulo="Clientes" itens={rel.clientes} total={rel.clientes_total} />
                <Lista titulo="Pares" itens={rel.pares} total={rel.pares_total} />
              </div>
              {rel.irmaos.length > 0 && <div className="mt-4"><Lista titulo="Mesmo grupo (CNPJ ou organização do CAIDA)" itens={rel.irmaos} total={rel.irmaos_total} /></div>}
              {(rel.complexas?.length ?? 0) > 0 && <div className="mt-4"><ListaComplexas itens={rel.complexas ?? []} /></div>}
            </>
          )}
          {transito && <div className="mt-4"><Cone t={transito} /></div>}
        </div>
      )}
      {/* O grafo desenha as relações inferidas — a montante os provedores, a jusante os clientes, só nos
          níveis declarado, confirmado e provável. Os vizinhos observados no AS_PATH (sem classificar) ficam na lista recolhida abaixo. */}
      <h2 className="text-base font-semibold text-gray-800 mb-1">Provedores e clientes</h2>
      <p className="text-xs text-gray-600 mb-3">
        A montante, os provedores; a jusante, os clientes. Só relações <strong>inferidas</strong> nos níveis declarado, confirmado e provável (as possíveis e os pares
        ficam nas listas acima). Não são contratos verificados.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {(['v6', 'v4'] as const).map((afi, k) => {
          const { ups, dns } = grafo[afi]
          return (
            <div key={afi} ref={k === 0 ? relationsRef : undefined} className="overflow-hidden">
              <h3 className={`text-sm font-medium mb-2 ${afi === 'v6' ? 'text-v6-700' : 'text-primario-700'}`}>{afi === 'v6' ? 'IPv6' : 'IPv4'}</h3>
              <ASRelationsGraph
                mainAsn={doc.asn}
                afi={afi}
                upsIxp={VAZIO}
                dnsIxp={VAZIO}
                upsGlobal={ups}
                dnsGlobal={dns}
                nodeMeta={doc.path_node_meta}
                onAsnClick={(id) => navigate(`/asn/${id}`)}
                width={relationsWidth}
                height={Math.round(relationsWidth * 380 / 520)}
                textoVazio={`Nenhum provedor nem cliente ${afi === 'v6' ? 'IPv6' : 'IPv4'} inferido com nível provável ou superior`}
              />
            </div>
          )
        })}
      </div>
      <details className="mt-4 text-sm" data-testid="vizinhos-observados">
        <summary className="cursor-pointer text-xs font-medium text-primario-700">Vizinhos observados no AS_PATH (sem classificar)</summary>
        <p className="mt-1 text-xs text-gray-600">Vizinho imediato em caminhos vistos nos looking glasses dos PTTs e nos coletores públicos. Estar acima ou abaixo no caminho não indica provedor ou cliente.</p>
        <div className="mt-2 grid gap-2 md:grid-cols-2 text-xs">
          {(['v6', 'v4'] as const).map((afi) => {
            const acima = [...new Set([...(afi === 'v6' ? doc.upstreams_v6 ?? [] : doc.upstreams_v4 ?? []), ...(afi === 'v6' ? doc.upstreams_global_v6 ?? [] : doc.upstreams_global_v4 ?? [])])]
            const abaixo = [...new Set(afi === 'v6' ? doc.downstreams_global_v6 ?? [] : doc.downstreams_global_v4 ?? [])]
            return (
              <div key={afi}>
                <div className="font-medium text-gray-700">{afi === 'v6' ? 'IPv6' : 'IPv4'}{afi === 'v6' ? (doc.is_multihomed_v6 ? ' · mais de um vizinho a montante' : doc.single_upstream_v6 ? ` · único vizinho a montante: AS${doc.single_upstream_v6}` : '') : (doc.is_multihomed_v4 ? ' · mais de um vizinho a montante' : doc.single_upstream_v4 ? ` · único vizinho a montante: AS${doc.single_upstream_v4}` : '')}</div>
                <div>Acima ({acima.length}): {acima.slice(0, 40).map((a, i) => <span key={a}>{i > 0 && ', '}<Link to={`/asn/${a}`} className="text-primario-700 hover:underline">AS{a}</Link></span>)}{acima.length > 40 ? ` e mais ${acima.length - 40}` : ''}</div>
                <div>Abaixo ({abaixo.length}): {abaixo.slice(0, 40).map((a, i) => <span key={a}>{i > 0 && ', '}<Link to={`/asn/${a}`} className="text-primario-700 hover:underline">AS{a}</Link></span>)}{abaixo.length > 40 ? ` e mais ${abaixo.length - 40}` : ''}</div>
              </div>
            )
          })}
        </div>
      </details>
    </div>
  )
}
