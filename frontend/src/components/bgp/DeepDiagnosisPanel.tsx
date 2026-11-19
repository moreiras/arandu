import type { AsDiagnosis, DeepVerdict } from '../../types/bgpStability'

const VERDICT_CFG: Record<DeepVerdict, { label: string; color: string; desc: string }> = {
  upstream_instability: {
    label: 'Instabilidade de upstream',
    color: 'bg-perigo-50 border-perigo-300 text-perigo-700',
    desc:  'Prefixos flapam em sincronia e o mesmo AS upstream aparece na maioria dos eventos — o problema provavelmente está no provedor de trânsito, não neste AS.',
  },
  prefix_specific: {
    label: 'Problema em prefixo específico',
    color: 'bg-alerta-50 border-alerta-300 text-alerta-700',
    desc:  'Apenas um ou poucos prefixos concentram o ruído — o restante do AS está estável. Possível rota estática, link dedicado ou configuração isolada.',
  },
  origin_instability: {
    label: 'Instabilidade de origem',
    color: 'bg-aviso-50 border-aviso-300 text-aviso-700',
    desc:  'Prefixos flapam de forma independente sem upstream dominante — ruído gerado internamente, possivelmente por timers, sessões BGP instáveis ou scripts de anúncio.',
  },
}

function VerdictBadge({ verdict }: { verdict: DeepVerdict }) {
  const cfg = VERDICT_CFG[verdict]
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

interface Props {
  diagnosis: AsDiagnosis
}

export function DeepDiagnosisPanel({ diagnosis: d }: Props) {
  const verdictCfg = VERDICT_CFG[d.verdict]

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-base font-semibold text-gray-800">Diagnóstico aprofundado</h2>
        <p className="text-xs text-gray-400 mt-0.5">Análise de causa raiz com AS_PATH completo dos eventos de flap</p>
      </div>

      {/* Veredito */}
      <div className={`rounded-lg border px-4 py-3 ${verdictCfg.color.replace('text-', 'border-').replace('bg-', 'border-')} ${verdictCfg.color}`}>
        <div className="flex items-start gap-2">
          <VerdictBadge verdict={d.verdict} />
        </div>
        <p className="text-xs mt-1.5 opacity-80">{verdictCfg.desc}</p>
      </div>

      {/* Métricas de diagnóstico */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Sincronismo de prefixos</p>
          <p className="text-lg font-semibold text-gray-800">{(d.prefix_sync_score * 100).toFixed(0)}%</p>
          <p className="text-xs text-gray-400">
            {d.prefix_sync_score > 0.8 ? 'alto — prefixos flapam juntos' :
             d.prefix_sync_score > 0.4 ? 'moderado' : 'baixo — prefixos independentes'}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Concentração no upstream</p>
          <p className="text-lg font-semibold text-gray-800">
            {d.suspected_upstream_asn ? `${d.upstream_concentration_pct.toFixed(0)}%` : '—'}
          </p>
          {d.suspected_upstream_asn && (
            <p className="text-xs text-gray-400 truncate">
              AS{d.suspected_upstream_asn}
              {d.suspected_upstream_name ? ` · ${d.suspected_upstream_name}` : ''}
            </p>
          )}
        </div>
      </div>

      {/* Upstream suspeito */}
      {d.suspected_upstream_asn && (
        <div className="text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
          <span className="font-medium">Upstream suspeito: </span>
          <a
            href={`/asn/${d.suspected_upstream_asn}`}
            className="text-primario-600 hover:underline font-mono"
          >
            AS{d.suspected_upstream_asn}
          </a>
          {d.suspected_upstream_name && (
            <span className="text-gray-500"> · {d.suspected_upstream_name}</span>
          )}
          <span className="text-gray-400"> aparece em {d.upstream_concentration_pct.toFixed(0)}% dos eventos de anúncio</span>
        </div>
      )}

      {/* Prefixos mais quentes */}
      {d.hot_prefixes.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-600 mb-2">Prefixos com maior atividade de flap</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="py-1.5 pr-3">Prefixo</th>
                  <th className="py-1.5 pr-2 text-right">Eventos flap</th>
                  <th className="py-1.5 pr-2">Upstream dominante</th>
                  <th className="py-1.5 text-right">Concentração</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {d.hot_prefixes.map(hp => (
                  <tr key={hp.prefix} className="hover:bg-gray-50">
                    <td className="py-1.5 pr-3 font-mono text-primario-700">{hp.prefix}</td>
                    <td className="py-1.5 pr-2 text-right tabular-nums">{hp.flap_events.toLocaleString('pt-BR')}</td>
                    <td className="py-1.5 pr-2">
                      {hp.dominant_upstream_asn ? (
                        <a href={`/asn/${hp.dominant_upstream_asn}`} className="text-primario-600 hover:underline font-mono">
                          AS{hp.dominant_upstream_asn}
                        </a>
                      ) : <span className="text-gray-400">—</span>}
                      {hp.dominant_upstream_name && (
                        <span className="text-gray-400"> · {hp.dominant_upstream_name}</span>
                      )}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-gray-600">
                      {hp.dominant_upstream_pct > 0 ? `${hp.dominant_upstream_pct.toFixed(0)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
