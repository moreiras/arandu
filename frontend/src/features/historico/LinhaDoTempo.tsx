// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { ComoLer } from '../../components/ui'
import { VerDados } from '../../components/ui/VerDados'
import type { HistoricoBloco, HistoricoEvento, MetricaHistorico } from '../../types/api'
import { textoVariacao } from '../series/SerieComparavel'
import { fraseEvento, METRICAS_ESCOPO, ROTULO_ESTADO, ROTULO_METRICA } from './rotulos'

const fmt = (n: number) => n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const L = 160, A = 44, P = 4

/**
 * Miniatura de uma série: pontos em SVG (sem estado de hover; o título nativo dá o valor de cada ponto). A regra de comparabilidade vem da API (PT-28):
 * a linha só liga pontos comparáveis seguidos e só em trechos com o mínimo de pontos; o ponto vazado e o traço marcam onde a série é cortada. Tracejado
 * claro marca as datas com evento.
 */
function Mini({ pontos, datasEvento, metrica, minLinha }: { pontos: { date: string; v: number }[]; datasEvento: Set<string>; metrica?: MetricaHistorico; minLinha: number }) {
  const vs = pontos.map((p) => p.v)
  const min = Math.min(...vs), max = Math.max(...vs)
  const x = (i: number) => (pontos.length === 1 ? L / 2 : P + (i * (L - 2 * P)) / (pontos.length - 1))
  const y = (v: number) => (max === min ? A / 2 : A - P - ((v - min) * (A - 2 * P)) / (max - min))
  const corte = (i: number) => metrica?.pontos[i]?.comparavel_com_anterior === false
  const cortes = pontos.filter((_, i) => corte(i)).length
  return (
    <svg viewBox={`0 0 ${L} ${A}`} className="w-full h-11 text-primario-600" role="img"
      aria-label={`Série por snapshot${cortes ? `, com ${cortes} ${cortes === 1 ? 'corte' : 'cortes'} onde os pontos não são comparáveis` : ''}. Os valores estão na tabela.`}>
      {pontos.map((p, i) => datasEvento.has(p.date) && <line key={'e' + p.date} x1={x(i)} x2={x(i)} y1={0} y2={A} stroke="currentColor" strokeOpacity={0.25} strokeDasharray="2 2" />)}
      {pontos.map((p, i) => i > 0 && corte(i) && (
        <line key={'c' + p.date} x1={(x(i) + x(i - 1)) / 2} x2={(x(i) + x(i - 1)) / 2} y1={0} y2={A} stroke="currentColor" strokeOpacity={0.5} strokeDasharray="3 3"><title>{`Corte antes de ${p.date}: pontos não comparáveis`}</title></line>
      ))}
      {metrica && metrica.segmentos.filter((sg) => sg.length >= minLinha).map((sg) => (
        <polyline key={'s' + sg[0]} fill="none" stroke="currentColor" strokeWidth={1.5} points={sg.map((i) => `${x(i)},${y(pontos[i].v)}`).join(' ')} />
      ))}
      {pontos.map((p, i) => <circle key={p.date} cx={x(i)} cy={y(p.v)} r={2.5} fill={corte(i) ? 'white' : 'currentColor'} stroke="currentColor" strokeWidth={1.5}><title>{`${p.date}: ${fmt(p.v)}${corte(i) ? ' (não comparável com o anterior)' : ''}`}</title></circle>)}
    </svg>
  )
}

function Evento({ e }: { e: HistoricoEvento }) {
  const link = e.entidade.startsWith('asn:') ? `/asn/${e.entidade.slice(4)}` : null
  return (
    <li className="flex flex-wrap items-baseline gap-x-2 text-sm">
      <time className="text-xs text-gray-500 tabular-nums">{e.data}</time>
      <span>{fraseEvento(e)}</span>
      {link && <Link to={link} className="text-primario-600 hover:underline text-xs">AS{e.entidade.slice(4)}</Link>}
      {e.destaque && <span className="text-xs text-aviso-700">novo estado: RPKI inválido</span>}
      {e.atipico && <span className="text-xs text-gray-600" title={e.atipico}>data atípica marcada</span>}
      <span className={`text-xs ${e.estado === 'pendente' ? 'text-gray-500 italic' : 'text-gray-400'}`}>{ROTULO_ESTADO[e.estado]}</span>
    </li>
  )
}

/**
 * Linha do tempo de uma entidade: miniaturas das métricas principais, uma por snapshot com histórico, e os eventos recentes.
 * Eventos são diferenças OBSERVADAS entre snapshots, sem causa nem intenção.
 * `escopo` escolhe as métricas desenhadas.
 */
export function LinhaDoTempo({ historico, escopo }: { historico?: HistoricoBloco | null; escopo: 'asn' | 'ixp' | 'operadora' | 'uf' }) {
  if (!historico || historico.serie.length === 0) {
    return <p className="text-sm text-gray-500">Ainda não há histórico guardado para esta entidade.</p>
  }
  const datasEvento = new Set(historico.eventos.filter((e) => e.estado !== 'revertido').map((e) => e.data))
  const metricas = METRICAS_ESCOPO[escopo].filter((m) => historico.colunas.includes(m))
  const regra = historico.regra
  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">
        {historico.serie.length} {historico.serie.length === 1 ? 'snapshot' : 'snapshots'} com histórico, de {historico.serie[0].date} a {historico.serie[historico.serie.length - 1].date}
        {historico.snapshots_com_historico > historico.serie.length && ` (${historico.snapshots_com_historico} existem)`}. Os eventos são diferenças observadas entre snapshots, sem causa atribuída.
      </p>
      {!historico.completo && (
        <p className="text-xs text-aviso-700">Você vê só os 2 snapshots mais recentes. <Link to="/login" className="underline">Entre</Link> para a série completa.</p>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metricas.map((m) => {
          const pontos = historico.serie.filter((p) => typeof p[m] === 'number').map((p) => ({ date: p.date, v: p[m] as number }))
          if (pontos.length === 0) return null
          const anotada = historico.metricas?.find((x) => x.id === m)
          const variacao = textoVariacao(anotada?.variacao, { motivos: regra?.motivos ?? {} })
          return (
            <div key={m} className="rounded border border-gray-200 p-2" data-testid="linha-do-tempo-metrica" data-metrica={m}>
              <div className="text-xs text-gray-500">{ROTULO_METRICA[m] ?? m}</div>
              <div className="text-lg font-semibold tabular-nums">{fmt(pontos[pontos.length - 1].v)}</div>
              <div className="text-xs text-gray-500 tabular-nums">em {pontos[pontos.length - 1].date}</div>
              <Mini pontos={pontos} datasEvento={datasEvento} metrica={anotada} minLinha={regra?.min_pontos_linha ?? 4} />
              {variacao && <div className="text-xs text-gray-600" data-testid="linha-do-tempo-variacao">{variacao}</div>}
              {anotada?.nota && <div className="mt-0.5 text-xs text-gray-600">{anotada.nota}</div>}
            </div>
          )
        })}
      </div>
      <VerDados dados={historico.serie} campos={['date', ...metricas]} rotulos={{ date: 'Data', ...Object.fromEntries(metricas.map((m) => [m, ROTULO_METRICA[m] ?? m])) }} />
      {regra && <ComoLer titulo="Como ler a linha do tempo">{regra.texto.map((t, i) => <p key={i}>{t}</p>)}<p>Cada ponto é um snapshot; com poucos pontos, o que se vê é a diferença entre eles, não uma tendência.</p></ComoLer>}
      {historico.eventos.length > 0 ? (
        <div>
          <h3 className="text-sm font-medium mb-1">Mudanças observadas</h3>
          <ul className="space-y-1">{historico.eventos.slice(0, 12).map((e) => <Evento key={`${e.data}-${e.tipo}-${e.entidade}-${e.chave}`} e={e} />)}</ul>
          {historico.eventos_total > 12 && <p className="text-xs text-gray-500 mt-1">{historico.eventos_total} no total. <Link to="/mudancas" className="text-primario-600 hover:underline">Ver todas em O que mudou</Link>.</p>}
        </div>
      ) : (
        <p className="text-sm text-gray-500">Nenhuma mudança observada entre os snapshots com histórico.</p>
      )}
    </div>
  )
}
