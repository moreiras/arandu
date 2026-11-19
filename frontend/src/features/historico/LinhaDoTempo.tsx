// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { HistoricoBloco, HistoricoEvento } from '../../types/api'
import { fraseEvento, METRICAS_ESCOPO, ROTULO_ESTADO, ROTULO_METRICA } from './rotulos'

const fmt = (n: number) => n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const L = 160, A = 44, P = 4

/** Miniatura de uma série: linha e pontos em SVG (sem estado de hover; o título nativo dá o valor de cada ponto). Marca com tracejado as datas com evento. */
function Mini({ pontos, datasEvento }: { pontos: { date: string; v: number }[]; datasEvento: Set<string> }) {
  const vs = pontos.map((p) => p.v)
  const min = Math.min(...vs), max = Math.max(...vs)
  const x = (i: number) => (pontos.length === 1 ? L / 2 : P + (i * (L - 2 * P)) / (pontos.length - 1))
  const y = (v: number) => (max === min ? A / 2 : A - P - ((v - min) * (A - 2 * P)) / (max - min))
  return (
    <svg viewBox={`0 0 ${L} ${A}`} className="w-full h-11 text-primario-600" role="img" aria-label="Série por snapshot">
      {pontos.map((p, i) => datasEvento.has(p.date) && <line key={'e' + p.date} x1={x(i)} x2={x(i)} y1={0} y2={A} stroke="currentColor" strokeOpacity={0.25} strokeDasharray="2 2" />)}
      {pontos.length > 1 && <polyline fill="none" stroke="currentColor" strokeWidth={1.5} points={pontos.map((p, i) => `${x(i)},${y(p.v)}`).join(' ')} />}
      {pontos.map((p, i) => <circle key={p.date} cx={x(i)} cy={y(p.v)} r={2.5} fill="currentColor"><title>{`${p.date}: ${fmt(p.v)}`}</title></circle>)}
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
      <span className={`text-xs ${e.estado === 'pendente' ? 'text-gray-500 italic' : 'text-gray-400'}`}>{ROTULO_ESTADO[e.estado]}</span>
    </li>
  )
}

/**
 * Linha do tempo de uma entidade: miniaturas das métricas principais, uma por snapshot com histórico, e os eventos recentes.
 * Eventos são diferenças OBSERVADAS entre snapshots, sem causa nem intenção. O histórico começou a ser guardado em 2026-10: poucos pontos no início.
 * `escopo` escolhe as métricas desenhadas.
 */
export function LinhaDoTempo({ historico, escopo }: { historico?: HistoricoBloco | null; escopo: 'asn' | 'ixp' | 'operadora' | 'uf' }) {
  if (!historico || historico.serie.length === 0) {
    return <p className="text-sm text-gray-500">Ainda não há histórico guardado para esta entidade (a camada de histórico começou em outubro de 2026).</p>
  }
  const datasEvento = new Set(historico.eventos.filter((e) => e.estado !== 'revertido').map((e) => e.data))
  const metricas = METRICAS_ESCOPO[escopo].filter((m) => historico.colunas.includes(m))
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
          const ultimo = pontos[pontos.length - 1].v, primeiro = pontos[0].v
          return (
            <div key={m} className="rounded border border-gray-200 p-2">
              <div className="text-xs text-gray-500">{ROTULO_METRICA[m] ?? m}</div>
              <div className="text-lg font-semibold tabular-nums">{fmt(ultimo)}</div>
              <Mini pontos={pontos} datasEvento={datasEvento} />
              {pontos.length > 1 && <div className="text-xs text-gray-500 tabular-nums">{ultimo - primeiro >= 0 ? '+' : ''}{fmt(ultimo - primeiro)} desde {pontos[0].date}</div>}
            </div>
          )
        })}
      </div>
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
