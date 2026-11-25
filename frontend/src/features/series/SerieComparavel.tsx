// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ComoLer, LinhaProveniencia } from '../../components/ui'
import { VerDados } from '../../components/ui/VerDados'
import type { MetricaSerie, SerieNacional } from '../../services/api'

type Regra = SerieNacional['regra']

const L = 320, A = 90, PX = 8, PY = 8
const num = (n: number, casas = 2) => n.toLocaleString('pt-BR', { maximumFractionDigits: casas })

/** Texto de uma variação vinda da API: o número só existe quando os dois pontos são comparáveis; senão, o motivo (a regra mora no servidor). */
export function textoVariacao(v: MetricaSerie['variacao'], regra: Pick<Regra, 'motivos'>): string | null {
  if (!v) return null
  if (v.calculada && v.absoluta != null) {
    const unidade = v.unidade === 'pp' ? ' p.p.' : ''
    return `${v.absoluta >= 0 ? '+' : ''}${num(v.absoluta)}${unidade} entre ${v.de} e ${v.para}`
  }
  const porque = v.motivos.map((m) => regra.motivos[m] ?? m).join('; ')
  return `Variação não calculada entre ${v.de} e ${v.para}${porque ? `: ${porque}` : ''}`
}

/**
 * Uma métrica de série nacional com a regra de comparabilidade da API: a linha é cortada onde os pontos não são comparáveis (marca tracejada e ponto vazado),
 * só se desenha linha em trechos com o mínimo de pontos comparáveis seguidos e a tabela traz os mesmos números e o motivo de cada corte. Sem estado do
 * React: o valor de cada ponto está no `title` do SVG e na tabela (WCAG 2.2 AA, alternativa textual).
 */
export function SerieComparavel({ metrica, regra }: { metrica: MetricaSerie; regra: Regra }) {
  const pts = metrica.pontos
  const valores = pts.map((p) => p.valor).filter((v): v is number => v != null)
  const min = Math.min(...valores), max = Math.max(...valores)
  const x = (i: number) => (pts.length === 1 ? L / 2 : PX + (i * (L - 2 * PX)) / (pts.length - 1))
  const y = (v: number) => (max === min ? A / 2 : A - PY - ((v - min) * (A - 2 * PY)) / (max - min))
  const cortes = pts.filter((p) => p.comparavel_com_anterior === false).length
  const ultimo = [...pts].reverse().find((p) => p.valor != null)
  const unidade = metrica.unidade === '%' ? '%' : ''
  const dados = pts.map((p) => ({
    data: p.date,
    valor: p.valor,
    comparavel: p.comparavel_com_anterior == null ? '—' : p.comparavel_com_anterior ? 'Sim' : `Não: ${(p.detalhes ?? []).map((d) => d.texto + (d.detalhe ? ` (${d.detalhe})` : '')).join('; ') || p.motivos.join(', ')}`,
  }))
  const variacao = textoVariacao(metrica.variacao, regra)
  return (
    <figure className="rounded border border-gray-200 bg-white p-3 min-w-0" data-testid="serie-comparavel" data-serie-id={metrica.id}>
      <figcaption className="text-sm font-medium text-gray-800">{metrica.rotulo}</figcaption>
      {ultimo && <div className="text-titulo-2 tabular-nums text-gray-900">{num(ultimo.valor as number)}{unidade}</div>}
      <LinhaProveniencia selo={metrica.selo} fonte={metrica.fonte} dataRef={ultimo?.date} />
      <svg viewBox={`0 0 ${L} ${A}`} className="mt-1 h-24 w-full text-primario-600" role="img"
        aria-label={`${metrica.rotulo}: ${pts.length} snapshots de ${pts[0]?.date} a ${pts[pts.length - 1]?.date}, ${cortes} ${cortes === 1 ? 'corte' : 'cortes'} onde os pontos não são comparáveis. Os valores estão na tabela abaixo.`}>
        {pts.map((p, i) => p.comparavel_com_anterior === false && (
          <line key={`c${p.date}`} x1={(x(i) + x(i - 1)) / 2} x2={(x(i) + x(i - 1)) / 2} y1={0} y2={A} stroke="currentColor" strokeOpacity={0.45} strokeDasharray="3 3">
            <title>{`Corte antes de ${p.date}: pontos não comparáveis`}</title>
          </line>
        ))}
        {metrica.segmentos.filter((s) => s.length >= regra.min_pontos_linha).map((s) => (
          <polyline key={`s${s[0]}`} fill="none" stroke="currentColor" strokeWidth={1.5} points={s.map((i) => `${x(i)},${y(pts[i].valor as number)}`).join(' ')} />
        ))}
        {pts.map((p, i) => p.valor != null && (
          <circle key={p.date} cx={x(i)} cy={y(p.valor)} r={3} fill={p.comparavel_com_anterior === false ? 'white' : 'currentColor'} stroke="currentColor" strokeWidth={1.5}>
            <title>{`${p.date}: ${num(p.valor)}${unidade}${p.comparavel_com_anterior === false ? ' (não comparável com o anterior)' : ''}`}</title>
          </circle>
        ))}
      </svg>
      {variacao && <p className="text-xs text-gray-700" data-testid="serie-variacao">{variacao}</p>}
      {metrica.nota && <p className="mt-0.5 text-xs text-gray-600" data-testid="serie-nota">{metrica.nota}</p>}
      <VerDados dados={dados} rotulos={{ data: 'Data', valor: `Valor${unidade ? ' (%)' : ''}`, comparavel: 'Comparável com o anterior' }} campos={['data', 'valor', 'comparavel']} />
    </figure>
  )
}

/** Conjunto de séries de uma família com o "Como ler" da regra (texto da API). */
export function SeriesNacionais({ serie, titulo, aviso }: { serie: SerieNacional; titulo: string; aviso?: string }) {
  return (
    <section className="space-y-3" aria-label={titulo} data-testid="series-nacionais">
      <h2 className="text-titulo-3 text-gray-800">{titulo}</h2>
      {aviso && <p className="text-xs text-aviso-700">{aviso}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {serie.metricas.map((m) => <SerieComparavel key={m.id} metrica={m} regra={serie.regra} />)}
      </div>
      <ComoLer titulo="Como ler as séries">
        {serie.regra.texto.map((t, i) => <p key={i}>{t}</p>)}
        <p>Cada ponto é um snapshot semanal. Os selos e as fontes de cada medida estão sob o valor; uma série curta não é tendência.</p>
      </ComoLer>
    </section>
  )
}
