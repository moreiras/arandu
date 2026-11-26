// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../entidade/registry'
import type { ExposicaoAsn, ExposicaoUf } from '../../types/api'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined, d = 1) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: d })}%`)
const dia = (v: string | null | undefined) => (v ? v.slice(0, 10).split('-').reverse().join('/') : '—')

function Rodape({ b }: { b: ExposicaoAsn | ExposicaoUf }) {
  const c = b.cobertura
  return (
    <>
      <p className="text-xs text-gray-500" data-testid="exposicao-cobertura">
        Cobertura (snapshot {b.snapshot_date}): {n(c.asns_com_leitura)} de {n(c.asns_do_brasil_no_snapshot)} ASNs do Brasil já consultados no Shodan (leituras de {dia(c.leitura_mais_antiga)} a {dia(c.leitura_mais_recente)}; o rodízio
        completa a lista em alguns dias), {n(c.asns_com_servicos_observados)} com algum serviço observado. {b.limites}
      </p>
      <p className="text-xs text-gray-500" data-testid="exposicao-atribuicao">
        {b.fonte.atribuicao ?? 'Dados: Shodan.'} Coletado em {dia(b.coletado_em)}.
      </p>
    </>
  )
}

/**
 * Exposição de serviços neste AS. Contagens observadas pelo Shodan na data da leitura; não é prova de vulnerabilidade; ASN sem leitura não é zero; nunca lista de IPs.
 */
export function ExposicaoAsnBloco({ dados }: BlocoProps<{ exposicao?: ExposicaoAsn | null }>) {
  const e = dados.exposicao
  if (!e) return null
  const classes = Object.entries(e.risco?.classes ?? {})
  const vuln = e.vulnerabilidades
  return (
    <div className="space-y-3 text-sm" data-testid="exposicao-asn">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="exposicao-aviso">{e.aviso}</p>
      {e.sem_servico_observado ? (
        <p className="text-sm text-gray-700" data-testid="exposicao-vazio">O Shodan não observou serviço neste AS (leitura de {dia(e.lido_em)}). Isso não prova que não há serviço exposto.</p>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
            <div><dt className="text-xs text-gray-500">Serviços observados</dt><dd className="tabular-nums font-medium" data-testid="exposicao-total">{n(e.servicos_observados)} (lido em {dia(e.lido_em)})</dd></div>
            <div><dt className="text-xs text-gray-500">Em portas de risco</dt><dd className="tabular-nums font-medium" data-testid="exposicao-risco">{n(e.risco?.servicos_de_risco)} ({pct(e.risco?.pct_dos_servicos_observados, 2)})</dd></div>
            <div className="sm:col-span-2"><dt className="text-xs text-gray-500">Portas mais vistas</dt><dd className="tabular-nums">{(e.portas_mais_vistas ?? []).map((p) => `${p.porta} (${n(p.n)})`).join(', ') || '—'}</dd></div>
          </dl>
          {classes.length > 0 ? (
            <ul className="space-y-1 text-xs text-gray-700" data-testid="exposicao-classes">
              {classes.map(([k, c]) => (
                <li key={k}><span className="font-medium">{e.classes_de_risco?.[k]?.rotulo ?? k}</span>: {n(c.total)}. Por serviço: {c.servicos.map((s) => `${s.servico} (${s.porta}): ${n(s.n)}`).join('; ')}</li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-600" data-testid="exposicao-sem-risco">Nenhum serviço nas portas de risco monitoradas (Telnet, RDP, VNC, TR-069, Winbox, SNMP, bancos de dados, SMB, FTP) na leitura do Shodan.</p>
          )}
          <p className="text-xs text-gray-600" data-testid="exposicao-vuln">
            {vuln == null
              ? 'CVEs: não consultadas nesta leitura.'
              : vuln.disponivel
                ? `CVEs mais vistas (inferidas pelo Shodan a partir do banner; não provam a falha): ${vuln.cves_mais_vistas.map((c) => `${c.cve} (${n(c.n)})`).join(', ') || 'nenhuma'}.`
                : 'CVEs: não disponível no plano da conta do Shodan.'}
          </p>
        </>
      )}
      <Rodape b={e} />
    </div>
  )
}

/** Exposição de serviços agregada na UF: DERIVADO dos ASNs já lidos pelo mapeamento ASN → UF; sem CVEs. */
export function ExposicaoUfBloco({ dados }: BlocoProps<{ exposicao?: ExposicaoUf | null }>) {
  const e = dados.exposicao
  if (!e) return null
  const classes = Object.entries(e.classes ?? {}).filter(([, v]) => v > 0)
  return (
    <div className="space-y-3 text-sm" data-testid="exposicao-uf">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="exposicao-aviso">Agregado derivado dos ASNs da UF já lidos (mapeamento ASN → UF do projeto). {e.aviso}</p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        <div><dt className="text-xs text-gray-500">ASNs da UF já lidos</dt><dd className="tabular-nums font-medium" data-testid="exposicao-uf-asns">{n(e.asns_com_leitura)} de {n(e.asns_do_cadastro)}</dd></div>
        <div><dt className="text-xs text-gray-500">Serviços observados</dt><dd className="tabular-nums font-medium">{n(e.servicos_observados)}</dd></div>
        <div><dt className="text-xs text-gray-500">Em portas de risco</dt><dd className="tabular-nums font-medium" data-testid="exposicao-uf-risco">{n(e.servicos_de_risco)} ({pct(e.pct_de_servicos_de_risco, 2)})</dd></div>
        <div><dt className="text-xs text-gray-500">ASNs com algum serviço</dt><dd className="tabular-nums font-medium">{n(e.asns_com_servicos_observados)}</dd></div>
      </dl>
      {classes.length > 0 && (
        <p className="text-xs text-gray-700" data-testid="exposicao-uf-classes">
          {classes.map(([k, v]) => `${e.classes_de_risco?.[k]?.rotulo ?? k}: ${n(v)}`).join('; ')}. Por serviço: {Object.entries(e.servicos_de_risco_por_servico ?? {}).map(([s, v]) => `${s} (${n(v)})`).join(', ') || '—'}.
        </p>
      )}
      <Rodape b={e} />
    </div>
  )
}
