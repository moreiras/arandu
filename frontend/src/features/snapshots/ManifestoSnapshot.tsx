// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DESCRICAO_SELO, ROTULO_SELO, fonteDe, formatarReferencia, rotuloFrescor, type FonteEntrada, type Selo } from '../../components/entidade'

/** O que `/snapshots/{data}` traz do manifesto (api/snapshot_detail.py `manifest_meta`); tudo opcional: snapshot antigo não tem. */
export interface ManifestoSnapshot {
  sources?: FonteEntrada[] | null
  pipeline_version?: string | null
  generated_at?: string | null
  ixps_configured?: string[]
  ixps_collected?: string[]
  ixps_failed?: unknown[]
  coleta?: string | null
  coleta_ok?: boolean | null
  checks?: Record<string, { status: string; [k: string]: unknown }> | null
}

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const COR_SELO: Record<Selo, string> = { fato: 'bg-fato-50 text-fato-700', inferido: 'bg-inferido-50 text-inferido-700', estimado: 'bg-estimado-50 text-estimado-700' }

export interface LinhaIndicador { label: string; valor: string; fontes: string[]; selo: Selo }

/**
 * Data de referência e estado da coleta da fonte de um indicador, a partir de `sources[]`. Sem o registro por fonte (snapshot anterior a ele), diz que a data não está
 * registrada: não usa a data do snapshot no lugar da data da fonte.
 */
export function referenciaDaFonte(sources: FonteEntrada[] | null | undefined, ids: string[]): string {
  if (!sources || sources.length === 0) return 'data da fonte não registrada neste snapshot'
  return ids.map((id) => {
    const f = fonteDe(sources, id)
    if (!f || f.frescor === 'ausente' || !f.as_of) return `${id}: ${rotuloFrescor(f)}`
    return `${id} · ref. ${formatarReferencia(f.as_of)}${f.frescor && f.frescor !== 'ok' ? ` (${rotuloFrescor(f)})` : ''}`
  }).join('; ')
}

/** Indicadores do snapshot, cada um com valor, selo e a data da sua fonte (IPv6 antes de IPv4). */
export function IndicadoresSnapshot({ linhas, sources }: { linhas: LinhaIndicador[]; sources: FonteEntrada[] | null | undefined }) {
  return (
    <dl className="grid grid-cols-2 gap-3 text-sm" data-testid="indicadores-snapshot">
      {linhas.map((row) => (
        <div key={row.label} className="bg-gray-50 rounded p-2">
          <dt className="text-xs text-gray-500">{row.label}</dt>
          <dd className="font-semibold text-gray-800">{row.valor}</dd>
          <dd className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs font-normal text-gray-500" data-testid="referencia-indicador">
            <span className={`rounded px-1 py-0.5 font-medium ${COR_SELO[row.selo]}`} title={DESCRICAO_SELO[row.selo]}>{ROTULO_SELO[row.selo]}</span>
            <span>{referenciaDaFonte(sources, row.fontes)}</span>
          </dd>
        </div>
      ))}
    </dl>
  )
}

const ROTULO_CHECK: Record<string, string> = {
  ptt_coletados: 'PTTs coletados', asns_br: 'ASNs brasileiros', prefixos_v6: 'Prefixos IPv6 do Registro.br', prefixos_v4: 'Prefixos IPv4 do Registro.br',
  vrps: 'VRPs do RPKI', asn_names: 'Nomes de ASN', pdb_registrados: 'ASNs com cadastro no PeeringDB',
}
const ORDEM_CHECK = Object.keys(ROTULO_CHECK)
const ROTULO_ESTADO: Record<string, string> = { ok: 'ok', falha: 'falhou', sem_base: 'sem base de comparação', pendente: 'pendente' }

function detalheCheck(c: { status: string; [k: string]: unknown }): string {
  const num = (k: string) => (typeof c[k] === 'number' ? (c[k] as number) : null)
  if (num('configurados') != null) return `${n(num('coletados'))} de ${n(num('configurados'))}${Array.isArray(c.faltam) && c.faltam.length ? `; faltam: ${(c.faltam as string[]).join(', ')}` : ''}`
  const partes: string[] = []
  if (num('valor') != null) partes.push(n(num('valor')))
  if (num('anterior') != null) partes.push(`contra ${n(num('anterior'))} no snapshot comparado`)
  if (num('variacao_pct') != null) partes.push(`variação de ${(num('variacao_pct') as number).toLocaleString('pt-BR')}% para o limite de ${n(num('limite_pct'))}%`)
  else if (num('pct_dos_asns_br') != null) partes.push(`${(num('pct_dos_asns_br') as number).toLocaleString('pt-BR')}% dos ASNs brasileiros (mínimo ${n(num('limite_pct'))}%)`)
  if (typeof c.motivo === 'string') partes.push(c.motivo)
  return partes.join('; ') || '—'
}

/** Estado da coleta do snapshot: PTTs, versão do processamento e verificações de sanidade (`manifest.checks`), com o estado de cada uma. */
export function ColetaSnapshot({ m }: { m: ManifestoSnapshot }) {
  const conf = m.ixps_configured?.length ?? 0
  const col = m.ixps_collected?.length ?? 0
  const estado = m.coleta ?? (m.coleta_ok === false ? 'com falha' : null)
  const checks = m.checks ? [...ORDEM_CHECK.filter((k) => m.checks![k]), ...Object.keys(m.checks).filter((k) => !ORDEM_CHECK.includes(k))] : []
  return (
    <div className="border-t border-gray-100 pt-3 space-y-2 text-sm" data-testid="coleta-snapshot">
      <p className="text-gray-700">
        Coleta: {estado ?? 'estado não registrado neste snapshot'}{conf ? ` (${n(col)} de ${n(conf)} PTTs)` : ''}
        {m.coleta_ok === false ? '; ao menos uma verificação falhou' : ''}. Versão do processamento: {m.pipeline_version ?? 'não registrada'}. Gerado em {m.generated_at ?? '—'}.
      </p>
      {checks.length > 0 ? (
        <table className="min-w-full text-xs">
          <caption className="sr-only">Verificações de sanidade da coleta</caption>
          <thead className="text-gray-500"><tr><th scope="col" className="text-left px-2 py-1">Verificação</th><th scope="col" className="text-left px-2 py-1">Estado</th><th scope="col" className="text-left px-2 py-1">Detalhe</th></tr></thead>
          <tbody className="divide-y divide-gray-100">
            {checks.map((k) => (
              <tr key={k}><th scope="row" className="text-left font-normal px-2 py-1">{ROTULO_CHECK[k] ?? k}</th><td className="px-2 py-1">{ROTULO_ESTADO[m.checks![k].status] ?? m.checks![k].status}</td><td className="px-2 py-1 text-gray-600">{detalheCheck(m.checks![k])}</td></tr>
            ))}
          </tbody>
        </table>
      ) : <p className="text-xs text-gray-500">Este snapshot não traz as verificações de sanidade da coleta.</p>}
    </div>
  )
}
