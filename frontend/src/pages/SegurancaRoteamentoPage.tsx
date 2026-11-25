// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { RovTerritorio, TransitoTerritorio } from '../features/rede/PanoramaRede'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchProntidaoResumo } from '../services/api'
import { CartogramaIndicador, type IndicadorUf } from '../features/estados/CartogramaIndicador'
import { BarraClasses, PILARES } from '../features/prontidao/blocos'
import type { ManrsResumo, ProntidaoAgregado } from '../types/api'
import { ComoLer } from '../components/ui/ComoLer'
import { Dica } from '../components/ui/Dica'
import { BarraDeAbas } from '../features/entidade/EntityPage'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados } from '../components/ui/EstadoDados'
import { useOrdenacao } from '../lib/ordenacao'
import { AvisosRecorte, textoPeso } from '../components/ui/AvisoRecorte'

import { EstadoRpkiRotas, RpkiPublicacao } from '../features/panorama/AbaSeguranca'
const num = (v: number | null | undefined, c = 1) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c }))
const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const PORTES: Record<string, string> = { sem_usuarios: 'Sem usuários estimados', ate_1000: 'Até 1.000 usuários', de_1000_a_10000: '1.000 a 10.000 usuários', de_10000_a_100000: '10.000 a 100.000 usuários', de_100000_a_1000000: '100.000 a 1 milhão', acima_de_1000000: 'Mais de 1 milhão de usuários' }
const ORDEM_PORTE = Object.keys(PORTES)
/** Texto sobre a lista por ASN quando ela é pública (`lista_nominal` verdadeiro em `/prontidao/resumo`, o padrão). */
export const TEXTO_LISTA_NOMINAL_PUBLICA = 'A lista por ASN é pública: coluna Prontidão em /ases, GET /prontidao/asns e a coleção prontidao_asn do Explorar. A ordem padrão é por ASN, não pelo índice. Pilar sem dado aparece como “não medido” e fica fora do índice e da classe, e a classe informa quantos pilares foram medidos. O índice é soma ponderada de medições de terceiros, não um veredito sobre a empresa; cite o snapshot e a versão das regras.'
/** Texto quando a instância desliga a lista (`PRONTIDAO_LISTA_NOMINAL=0`). */
export const TEXTO_SEM_LISTA_NOMINAL = 'Esta instância não publica a lista nominal de ASNs nem de empresas: o índice de cada ASN está na página dele.'
const ABAS_MAPA = [
  { id: 'indice', rotulo: 'Índice por UF', descricao: 'Índice de prontidão e componentes por UF (sede do ASN)' },
  { id: 'rov', rotulo: 'Usuários atrás de ROV', descricao: 'Estimativa de usuários cuja rede descarta rotas RPKI-inválidas' },
  { id: 'transito', rotulo: 'Dependência de trânsito', descricao: 'Dependência de trânsito da região (inferida)' },
]

/** As tabelas com os elementos do índice ganham cartão com faixa lateral e cabeçalho com fundo, para não se misturarem ao texto. */
const CARTAO_TABELA = 'bg-white border border-gray-200 border-l-4 border-l-tecnico-500 rounded-lg p-4 space-y-2 shadow-sm'
const THEAD = 'bg-gray-50 text-gray-600'

function Tabela({ titulo, itens, rotulo }: { titulo: string; itens: Array<[string, ProntidaoAgregado]>; rotulo: (k: string) => string }) {
  const { ordenados, props } = useOrdenacao(itens, {
    recorte: ([k]) => rotulo(k),
    asns: ([, a]) => a.asns,
    com_indice: ([, a]) => a.asns_com_indice,
    com_filtragem: ([, a]) => a.cobertura_pilares?.filtragem ?? null,
    media: ([, a]) => a.media_ponderada_usuarios,
    mediana: ([, a]) => a.mediana,
    maior: ([, a]) => a.peso_top1 ?? null,
  })
  return (
    <section className={CARTAO_TABELA}>
      <h3 className="text-titulo-4 text-gray-800">{titulo}</h3>
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full" aria-label={titulo}>
          <thead className={THEAD}><tr>
            <ThOrdenavel {...props('recorte')} className="text-left px-2 py-1">Recorte</ThOrdenavel>
            <ThOrdenavel {...props('asns')} alinhar="right" className="text-right px-2 py-1">ASNs</ThOrdenavel>
            <ThOrdenavel {...props('com_indice')} alinhar="right" className="text-right px-2 py-1">Com índice</ThOrdenavel>
            <ThOrdenavel {...props('com_filtragem')} alinhar="right" className="text-right px-2 py-1">ASNs com Filtragem (ROV)</ThOrdenavel>
            <ThOrdenavel {...props('media')} alinhar="right" className="text-right px-2 py-1">Média ponderada</ThOrdenavel>
            <ThOrdenavel {...props('mediana')} alinhar="right" className="text-right px-2 py-1">Mediana</ThOrdenavel>
            <ThOrdenavel {...props('maior')} alinhar="right" className="text-right px-2 py-1" extra={<Dica texto="Parcela do ASN com mais usuários estimados entre os ASNs com índice do recorte. Aviso quando há menos de 5 ASNs com índice ou um deles pesa 30% ou mais; o valor da linha continua à vista." rotulo="Maior ASN" />}>Maior ASN</ThOrdenavel>
            <th scope="col" className="px-2 py-1 w-56">Distribuição por classe</th>
          </tr></thead>
          <tbody>
            {ordenados.map(([k, a]) => (
              <tr key={k} className="border-t border-gray-100 align-middle">
                <td className="px-2 py-1 font-medium">{rotulo(k)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(a.asns)}</td><td className="px-2 py-1 text-right tabular-nums">{inteiro(a.asns_com_indice)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{inteiro(a.cobertura_pilares?.filtragem)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{num(a.media_ponderada_usuarios)}</td><td className="px-2 py-1 text-right tabular-nums">{num(a.mediana)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{a.peso_top1 == null ? '—' : `${num(100 * a.peso_top1, 0)}%`} <AvisosRecorte avisos={a.avisos} /></td>
                <td className="px-2 py-1"><BarraClasses a={a} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

const MEDIDAS: Array<[string, string, string]> = [
  ['rov', 'ROV', 'Rede não alcança rota RPKI-inválida (medição do APNIC, ≥ 100 amostras): % médio'],
  ['sem_bogon', 'Sem bogon', '% dos ASNs que não originam prefixo reservado ou não alocado (só ASNs com ROV medido)'],
  ['spoofer', 'Anti-spoofing', 'CAIDA Spoofer: % médio de sessões conclusivas em que a rede barrou pacotes forjados (≥ 5 sessões)'],
  ['peeringdb', 'PeeringDB', '% dos ASNs com registro no PeeringDB'],
  ['irr_aut_num', 'aut-num IRR', '% dos ASNs com objeto aut-num no TC ou no RADB'],
  ['irr_as_set', 'as-set', '% dos registrados no PeeringDB que informam um as-set IRR'],
  ['roa', 'ROA válido', '% médio dos prefixos anunciados com origem RPKI válida'],
  ['irr', 'Route object', '% médio dos prefixos anunciados com route/route6 no TC ou no RADB'],
  ['aspa', 'ASPA', '% dos ASNs do recorte que publicam ASPA'],
]

/** Valor do componente no agregado: média simples ou ponderada (% de ASNs ou de usuários); a ASPA é a fração de ASNs do recorte que publicam. */
function medida(a: ProntidaoAgregado, c: string, pesoUsuarios: boolean): { v: number | null; n: number; peso: number | null; avisos: string[] } {
  const m = a.medicoes?.[c]
  if (!m) return { v: null, n: 0, peso: null, avisos: [] }
  const extra = { peso: m.peso_top1 ?? null, avisos: m.avisos ?? [] }
  if (c === 'aspa') return { v: a.asns ? (100 * m.asns) / a.asns : null, n: m.asns, ...extra }
  return { v: pesoUsuarios ? m.media_ponderada_usuarios : m.media, n: m.asns, ...extra }
}

function TabelaMedicoes({ titulo, itens, rotulo, pesoUsuarios }: { titulo: string; itens: Array<[string, ProntidaoAgregado]>; rotulo: (k: string) => string; pesoUsuarios: boolean }) {
  const acessores = Object.fromEntries(MEDIDAS.map(([id]) => [id, ([, a]: [string, ProntidaoAgregado]) => medida(a, id, pesoUsuarios).v]))
  // `itens` é um array novo a cada render do pai, então a troca de peso também reordena.
  const { ordenados, props } = useOrdenacao<[string, ProntidaoAgregado], string>(itens, { recorte: ([k]) => rotulo(k), ...acessores })
  return (
    <section className={CARTAO_TABELA}>
      <h3 className="text-titulo-4 text-gray-800">{titulo}</h3>
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full" aria-label={titulo}>
          <thead className={THEAD}>
            <tr><ThOrdenavel {...props('recorte')} className="text-left px-2 py-1">Recorte</ThOrdenavel>{MEDIDAS.map(([id, nome, dica]) => <ThOrdenavel key={id} {...props(id)} alinhar="right" className="text-right px-2 py-1 font-medium whitespace-nowrap" extra={<Dica texto={dica} rotulo={nome} />}>{nome}</ThOrdenavel>)}</tr>
          </thead>
          <tbody>
            {ordenados.map(([k, a]) => (
              <tr key={k} className="border-t border-gray-100">
                <td className="px-2 py-1 font-medium">{rotulo(k)}</td>
                {MEDIDAS.map(([id]) => {
                  const { v, n, peso, avisos } = medida(a, id, pesoUsuarios)
                  return <td key={id} className="px-2 py-1 text-right tabular-nums" title={`${inteiro(n)} ASNs com dado`}>{v == null ? '—' : `${num(v, 0)}%`}<span className="block text-xs text-gray-500">{inteiro(n)}{peso != null && id !== 'aspa' ? ` · ${textoPeso(peso)}` : ''}</span><AvisosRecorte avisos={avisos} /></td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

/** Participação em organizações do programa de operadores do MANRS: só agregados (termos do MANRS), com a atribuição exigida; recorte com poucos participantes, ou dominado por um ASN, sai com aviso (nada é suprimido). */
function CartaoManrs({ m }: { m: ManrsResumo }) {
  const b = m.brasil
  const comp = b.comparacao_prontidao
  const portes = Object.entries(m.por_faixa_porte).sort((a, c) => ORDEM_PORTE.indexOf(a[0]) - ORDEM_PORTE.indexOf(c[0]))
  const ufs = Object.entries(m.por_uf).sort((a, c) => (c[1].pct_asns ?? -1) - (a[1].pct_asns ?? -1))
  // `suprimido` só existe em snapshots anteriores à regra sem supressão (D6); os publicados são imutáveis
  const celula = (c: ManrsResumo['brasil']) => (c.suprimido ? <span className="text-gray-500" title={c.motivo}>não divulgado neste snapshot</span> : <>{num(c.pct_asns, 0)}% <span className="text-gray-500">({inteiro(c.asns_participantes)})</span> <AvisosRecorte avisos={c.avisos} /></>)
  return (
    <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3" data-testid="manrs">
      <h2 className="text-sm font-semibold text-gray-700">Participação no MANRS</h2>
      {b.suprimido ? <p className="text-sm text-gray-600">Menos de {m.regras.minimo_asns_por_recorte} ASNs participantes: o total não é divulgado neste snapshot.</p> : (
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-3xl font-semibold tabular-nums">{num(b.pct_asns, 1)}%</span> <span className="text-gray-500">dos {inteiro(b.asns)} ASNs do Brasil ({inteiro(b.asns_participantes)}) estão em organizações participantes</span></div>
          <div className="text-gray-600"><span className="tabular-nums">{num(b.pct_usuarios, 1)}%</span> dos usuários estimados do APNIC nesses ASNs · {inteiro(b.organizacoes_com_asn_br)} organizações com ASN no Brasil</div>
        </div>
      )}
      {comp && (
        <p className="text-sm text-gray-600">Índice de prontidão (média ponderada pelos usuários): <strong className="tabular-nums">{num(comp.participantes.media_ponderada_usuarios)}</strong> nos ASNs de participantes contra <strong className="tabular-nums">{num(comp.nao_participantes.media_ponderada_usuarios)}</strong> nos demais
          (medianas {num(comp.participantes.mediana)} e {num(comp.nao_participantes.mediana)}). É associação, não causa: participar é um compromisso declarado.</p>
      )}
      <div className="grid md:grid-cols-2 gap-4 text-xs">
        <div>
          <h3 className="font-medium text-gray-700 mb-1">Por porte (% dos ASNs)</h3>
          <table className="min-w-full"><tbody>{portes.map(([k, c]) => <tr key={k} className="border-t border-gray-100"><td className="py-0.5">{PORTES[k] ?? k}</td><td className="py-0.5 text-right tabular-nums">{celula(c)}</td></tr>)}</tbody></table>
        </div>
        <div>
          <h3 className="font-medium text-gray-700 mb-1">Por UF (% dos ASNs e, entre parênteses, os ASNs participantes; aviso com menos de {m.regras.minimo_asns_por_recorte} participantes ou um ASN com {Math.round((m.regras.peso_aviso ?? 0.3) * 100)}% ou mais dos usuários dos participantes)</h3>
          <div className="grid grid-cols-3 gap-x-4">{ufs.map(([k, c]) => <div key={k} className="flex justify-between border-t border-gray-100 py-0.5"><span>{k}</span><span className="tabular-nums">{celula(c)}</span></div>)}</div>
        </div>
      </div>
      <p className="text-xs text-gray-500">{m.atribuicao}. Fonte: {m.fonte.descricao}, medição de {m.fonte.medido_em ?? 'data não informada'}. {m.limites}</p>
    </section>
  )
}

/**
 * `/seguranca-de-roteamento` — Estado da segurança de roteamento: o índice de prontidão dos ASNs do Brasil em quatro pilares, com a metodologia completa (pesos, componentes, limiares, fontes) e os agregados por UF e porte.
 * É um conjunto de medições e fatos de terceiros somados com pesos públicos, não um veredito. A lista nominal por ASN é pública (decisão do mantenedor) com salvaguardas; o texto desta página sobre ela vem de `r.lista_nominal`
 * (o mesmo `lista_nominal_habilitada()` da API), nunca fixo: `tests/unit/test_prontidao_texto_contrato.py` confere.
 */
export function SegurancaRoteamentoPage() {
  const q = useQuery({ queryKey: ['prontidao-resumo'], queryFn: () => fetchProntidaoResumo(), staleTime: 10 * 60 * 1000, retry: false })
  const [ordem, setOrdem] = useState<'media' | 'asns'>('media')
  const [pesoUsuarios, setPesoUsuarios] = useState(false)
  const [mapa, setMapa] = useState('indice')
  const r = q.data
  if (!r) return q.isError
    ? <EstadoDados variante="pagina" erro={q.error} oQue="a prontidão em segurança de roteamento" mensagem="A prontidão em segurança de roteamento não foi publicada neste snapshot." aoTentarDeNovo={() => void q.refetch()} />
    : <p className="text-sm text-gray-500">Carregando…</p>
  const br = r.agregado
  const ufs = Object.entries(r.por_uf ?? {}).sort((a, b) => ordem === 'media' ? (b[1].media_ponderada_usuarios ?? -1) - (a[1].media_ponderada_usuarios ?? -1) : b[1].asns - a[1].asns)
  const portes = Object.entries(r.por_faixa_porte ?? {}).sort((a, b) => ORDEM_PORTE.indexOf(a[0]) - ORDEM_PORTE.indexOf(b[0]))
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Estado da segurança de roteamento</h1>
        <p className="text-sm text-gray-500">Índice de prontidão dos ASNs do Brasil em quatro pilares, com metodologia pública. Snapshot {r.snapshot_date}; regras v{r.regras.versao} ({r.regras.hash}).</p>
      </div>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-baseline gap-x-8 gap-y-1 text-sm">
          <div><span className="text-3xl font-semibold tabular-nums">{num(br.media_ponderada_usuarios)}</span> <span className="text-gray-500">média do índice ponderada pelos usuários estimados do APNIC</span></div>
          <div className="text-gray-600">mediana {num(br.mediana)} · {inteiro(br.asns_com_indice)} de {inteiro(br.asns)} ASNs com índice</div>
        </div>
        <BarraClasses a={br} detalhe />
        <ComoLer><p>A classe vem do índice, que soma os pilares <strong>medidos</strong> do ASN com os pesos das regras: pilar sem dado fica fora e os pesos dos demais são renormalizados. Por isso um ASN pode estar em "pronto" sem ter ROV medido (as duas linhas acima separam os casos) e a quantidade em cada classe depende de quantos ASNs têm ROV medido, que muda de um snapshot para outro: o ROV de um ASN só entra com pelo menos 100 amostras do APNIC na janela de 7 dias, e o volume de amostras da fonte muda de semana em semana. Compare classes entre snapshots só com a mesma cobertura do pilar Filtragem ({inteiro(br.cobertura_pilares.filtragem)} ASNs neste).</p></ComoLer>
        <p className="text-xs text-gray-500">ASNs com dado em cada pilar: {PILARES.map((id) => `${r.regras.pilares[id].nome} ${inteiro(br.cobertura_pilares[id])}`).join(' · ')}. O anti-spoofing só existe para os ASNs com testes do CAIDA Spoofer.</p>
      </section>
      {/* A publicação no RPKI e o estado das rotas no total do país (os mesmos números do Panorama técnico). */}
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-4" aria-label="RPKI no Brasil">
        <h2 className="text-titulo-3 text-gray-800">RPKI no Brasil</h2>
        <RpkiPublicacao />
        <h3 className="text-titulo-4 text-gray-800">Estado RPKI das rotas brasileiras</h3>
        <EstadoRpkiRotas />
      </section>
      {/* os mapas em abas, um por vez. */}
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
        <h2 className="text-titulo-3 text-gray-800">No mapa</h2>
        <BarraDeAbas abas={ABAS_MAPA} ativa={mapa} aoEscolher={setMapa} rotulo="Mapas da segurança de roteamento" />
        <div role="tabpanel" id={`painel-${mapa}`} aria-labelledby={`aba-${mapa}`}>
          {mapa === 'indice' && <>
      <div data-testid="seguranca-por-uf">
                <CartogramaIndicador
          inicial="indice"
          indicadores={[
            { id: 'indice', rotulo: 'Índice (média ponderada por usuários)', maximo: 100, texto: (v) => num(v, 0), nota: 'Média do índice de prontidão ponderada pelos usuários estimados do APNIC.', valor: (uf) => r.por_uf?.[uf]?.media_ponderada_usuarios ?? null },
            ...MEDIDAS.filter(([id]) => ['rov', 'sem_bogon', 'roa', 'irr'].includes(id)).map(([id, nome, dica]): IndicadorUf => ({
              id, rotulo: nome, maximo: 100, texto: (v) => `${num(v, 0)}%`, nota: dica, valor: (uf) => { const a = r.por_uf?.[uf]; return a ? medida(a, id, pesoUsuarios).v : null },
            })),
          ]}
          verDados={<div className="space-y-4"><TabelaMedicoes titulo="O que foi medido, por UF" itens={ufs} rotulo={(k) => k} pesoUsuarios={pesoUsuarios} /></div>}
        />
      </div>
          </>}
          {mapa === 'rov' && <RovTerritorio />}
          {mapa === 'transito' && <TransitoTerritorio />}
        </div>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
        <h2 className="text-titulo-3 text-gray-800">O que foi medido, por grupo</h2>
        <ComoLer><p>Cada coluna é um componente do índice, entre os ASNs do recorte que têm o dado (o número pequeno abaixo do percentual é quantos são e, ao lado, a parcela do maior deles nos usuários estimados; o selo avisa quando são menos de 5 ou um deles pesa 30% ou mais. Nenhuma UF é ocultada). Nos componentes sim/não é o % de ASNs com “sim”; nos demais, o valor médio da medição.
          O anti-spoofing só existe para os ASNs com testes do CAIDA Spoofer; “sem bogon” só para os que têm ROV medido.</p></ComoLer>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <span>Contar:</span>
          <button className={`px-2 py-1 rounded border ${!pesoUsuarios ? 'bg-primario-50 border-primario-300' : 'border-gray-200'}`} onClick={() => setPesoUsuarios(false)}>cada ASN igual</button>
          <button className={`px-2 py-1 rounded border ${pesoUsuarios ? 'bg-primario-50 border-primario-300' : 'border-gray-200'}`} onClick={() => setPesoUsuarios(true)}>ponderado pelos usuários estimados</button>
        </div>
      </section>
      <TabelaMedicoes titulo="Total (Brasil)" itens={[['BR', br]]} rotulo={() => 'Brasil'} pesoUsuarios={pesoUsuarios} />
      <TabelaMedicoes titulo="Por porte" itens={portes} rotulo={(k) => PORTES[k] ?? k} pesoUsuarios={pesoUsuarios} />
      <Tabela titulo="Distribuição por classe, por porte (usuários estimados do APNIC no ASN)" itens={portes} rotulo={(k) => PORTES[k] ?? k} />
      <section className="bg-white border border-gray-200 rounded-lg p-4 flex items-center gap-3 text-sm text-gray-600">
        <span>Estados por:</span>
        <button className={`px-2 py-1 rounded border ${ordem === 'media' ? 'bg-primario-50 border-primario-300' : 'border-gray-200'}`} onClick={() => setOrdem('media')}>média do índice</button>
        <button className={`px-2 py-1 rounded border ${ordem === 'asns' ? 'bg-primario-50 border-primario-300' : 'border-gray-200'}`} onClick={() => setOrdem('asns')}>número de ASNs</button>
      </section>
      <details className="bg-white border border-gray-200 rounded-lg p-4">
        <summary className="cursor-pointer text-sm font-semibold text-gray-700">Distribuição por classe, por UF (tabela)</summary>
        <div className="mt-2"><Tabela titulo="Por UF (sede do ASN)" itens={ufs} rotulo={(k) => k} /></div>
      </details>
      {r.manrs && <CartaoManrs m={r.manrs} />}
      <ComoLer titulo="Como o índice é calculado">
        <p className="text-sm text-gray-600">Cada pilar vai de 0 a 100 pela média ponderada dos seus componentes; o índice é a média ponderada dos pilares. Componente ou pilar sem dado sai da conta (os pesos que restam se renormalizam) e o índice sempre diz quais pilares entraram.
          Com menos de {r.regras.minimos.pilares} pilares, o ASN fica sem índice. Classes: <strong>pronto</strong> a partir de {r.regras.classes.pronto}, <strong>em progresso</strong> a partir de {r.regras.classes.em_progresso}, <strong>atrasado</strong> abaixo disso.</p>
        <div className="grid md:grid-cols-2 gap-3">
          {PILARES.map((id) => {
            const p = r.regras.pilares[id]
            return (
              <div key={id} className="border border-gray-100 rounded p-3 text-sm space-y-1">
                <div className="flex justify-between"><h3 className="font-medium text-gray-800">{p.nome}</h3><span className="text-gray-500">peso {p.peso}</span></div>
                <p className="text-xs text-gray-500">{p.descricao}{p.requer?.length ? ` O pilar só entra com o dado de: ${p.requer.map((c) => c.replace(/_/g, ' ')).join(', ')}.` : ''}</p>
                <ul className="text-xs text-gray-700 space-y-0.5">{Object.entries(p.componentes).map(([c, v]) => <li key={c}><span className="font-medium">{c.replace(/_/g, ' ')}</span> (peso {v.peso}): {v.descricao}</li>)}</ul>
              </div>
            )
          })}
        </div>
        <p className="text-xs text-gray-500">Mínimo de {r.regras.minimos.amostras_rov} amostras do APNIC para o ROV valer. Fontes: {r.fontes.seguranca.fonte}; {r.fontes.spoofer.citacao ?? r.fontes.spoofer.fonte}; {r.fontes.irr.fonte} ({Object.entries(r.fontes.irr.serial).map(([k, v]) => `${k} serial ${v}`).join(', ')}); PeeringDB; ROAs e ASPAs do RPKI.</p>
      </ComoLer>
      <p className="text-xs text-gray-500">{r.limites} A UF é a da sede do ASN; os agregados ponderam pelos usuários estimados do APNIC (ASN sem estimativa pesa 0 quando há outros com estimativa).</p>
      <p className="text-xs text-gray-500" data-testid="texto-lista-nominal">{r.lista_nominal === false ? TEXTO_SEM_LISTA_NOMINAL : TEXTO_LISTA_NOMINAL_PUBLICA}</p>
    </div>
  )
}
