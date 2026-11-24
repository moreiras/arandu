// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
// Cartões do route server do DE-CIX na página do IXP externo: sessões, ASNs diretos e de origem (piso), cobertura da leitura e comparação com o IX.br da cidade.
// Dado do Alice-LG do DE-CIX (`route_server` de GET /external-ixps/{code}); o PeeringDB continua sendo a fonte da tabela de membros.
import type { ExternalIXPDocument } from '../types/api'

export interface DecixRouteServer {
  snapshot_date?: string
  coletado_em?: string | null
  rotas_coletadas_em?: string | null
  fonte?: string
  versao_alice?: string
  aviso?: string
  bloqueio?: { motivo?: string } | null
  cidade: string
  criterio: { asn_direct: string; asn_origin: string }
  resumo: {
    rs: number; rs_consultados: number; sessoes: number; sessoes_up: number; sessoes_down: number; membros: number; membros_up: number
    asn_direct_count: number; br_asn_direct_count: number; asn_origin_count: number; br_asn_origin_count: number
  }
  asn_direct: number[]
  rotas: {
    parcial: boolean; vizinhos_lidos: number; vizinhos_completos: number; herdados: number; rotas_total_dos_lidos: number; rotas_lidas: number
    cobertura?: { elegiveis: number; lidos_na_rodada: number; herdados: number; sem_leitura: number; idade_max_dias: number | null } | null
  }
  peeringdb?: { cadastrados: number; cadastrados_sem_sessao_up_total: number; sessao_up_sem_cadastro_total: number } | null
  comparacao_cidade: {
    cidade: string
    ixbr: { ptt: string; asn_direct: number; br_asn_origin: number } | null
    decix: { ptt: string; asn_direct: number; br_asn_direct: number; asn_origin_piso: number }
    interseccao_direct?: { ambos: number; so_decix: number; so_ixbr: number; pct_do_decix_no_ixbr: number | null }
    no_decix_sem_ixbr?: { total: number; asns: number[]; truncado: boolean }
    externos?: Record<string, { membros_peeringdb: number; ambos_decix_sessao: number; ambos_ixbr?: number }>
  }
}

export type ExternalIXPComRouteServer = ExternalIXPDocument & { route_server?: DecixRouteServer }

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))

/** Redes (ASNs distintos), redes brasileiras e portas a partir das linhas do PeeringDB (uma por porta): vale também para snapshot antigo. */
export function contagemRedes(members: ExternalIXPDocument['members']): { redes: number; redesBr: number; portas: number } {
  return { redes: new Set(members.map((m) => m.asn)).size, redesBr: new Set(members.filter((m) => m.is_br).map((m) => m.asn)).size, portas: members.length }
}

/**
 * Redes brasileiras por fonte (IXE-E2): cadastradas no PeeringDB, com sessão up no route server, e o cruzamento. "Com sessão e sem
 * cadastro" é derivado: brasileiros com sessão menos os cadastrados que têm sessão.
 */
export function redesBrPorFonte(members: ExternalIXPDocument['members'], rs: DecixRouteServer) {
  const cadastradas = new Set(members.filter((m) => m.is_br).map((m) => m.asn))
  const comSessao = new Set(rs.asn_direct)
  const cadastradasComSessao = [...cadastradas].filter((a) => comSessao.has(a)).length
  return {
    cadastradas: cadastradas.size,
    sessao: rs.resumo.br_asn_direct_count,
    sessaoSemCadastro: Math.max(0, rs.resumo.br_asn_direct_count - cadastradasComSessao),
    cadastradasSemSessao: cadastradas.size - cadastradasComSessao,
  }
}

export function RedesBrPorFonte({ members, rs }: { members: ExternalIXPDocument['members']; rs: DecixRouteServer }) {
  const r = redesBrPorFonte(members, rs)
  const linhas: Array<[string, number]> = [
    ['Cadastradas no PeeringDB', r.cadastradas],
    ['Com sessão up no route server', r.sessao],
    ['Com sessão up e sem cadastro no PeeringDB', r.sessaoSemCadastro],
    ['Cadastradas e sem sessão up no route server', r.cadastradasSemSessao],
  ]
  return (
    <section className="bg-white rounded-lg border border-gray-200 px-4 py-3 space-y-2" data-testid="redes-br-por-fonte">
      <h2 className="text-base font-semibold text-gray-800">Redes brasileiras por fonte</h2>
      <table className="text-sm"><tbody>
        {linhas.map(([rot, v]) => <tr key={rot}><td className="pr-6 py-0.5 text-gray-600">{rot}</td><td className="text-right tabular-nums">{n(v)}</td></tr>)}
      </tbody></table>
      <p className="text-xs text-gray-500">Como ler: "brasileira" é ASN delegado pela LACNIC ao Brasil. O cadastro é o que a rede declara no PeeringDB; a sessão é o que o route server do DE-CIX mostra na coleta. Uma rede pode estar no PTT só com peering bilateral (sem sessão no route server) ou ter sessão sem ter se cadastrado.</p>
    </section>
  )
}

export function ExternalIXPRouteServer({ rs }: { rs: DecixRouteServer }) {
  const r = rs.resumo
  const cob = rs.rotas.cobertura
  const comp = rs.comparacao_cidade
  const cartoes = [
    { label: 'Sessões up / total', value: `${n(r.sessoes_up)} / ${n(r.sessoes)}`, nota: `${n(r.rs_consultados)} de ${n(r.rs)} route servers consultados` },
    { label: 'ASNs diretos (sessão up)', value: n(r.asn_direct_count), nota: `${n(r.br_asn_direct_count)} brasileiros` },
    { label: 'ASNs de origem (piso)', value: n(r.asn_origin_count), nota: rs.rotas.parcial ? 'leitura parcial: é um mínimo' : `${n(r.br_asn_origin_count)} brasileiros` },
  ]
  return (
    <section className="bg-white rounded-lg border border-gray-200 px-4 py-4 space-y-4" data-testid="decix-route-server">
      <div className="flex items-center gap-2 flex-wrap">
        <h2 className="text-base font-semibold text-gray-800">Route server (Alice-LG do DE-CIX)</h2>
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-tecnico-100 text-tecnico-800 border border-tecnico-200">dados: lg.de-cix.net</span>
      </div>
      {rs.bloqueio && (
        <div className="bg-perigo-50 border border-perigo-200 rounded px-3 py-2 text-xs text-perigo-800">
          A coleta parou por sinal de bloqueio do servidor ({rs.bloqueio.motivo}); os números abaixo são os da última leitura completa que coube.
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {cartoes.map(c => (
          <div key={c.label} className="rounded-lg border border-gray-200 px-4 py-3">
            <div className="text-xs text-gray-500 mb-1">{c.label}</div>
            <div className="text-xl font-semibold text-gray-900">{c.value}</div>
            <div className="text-xs text-gray-400 mt-1">{c.nota}</div>
          </div>
        ))}
      </div>
      {cob && (
        <p className="text-xs text-gray-500">
          Rotas lidas por vizinho em rodízio: {n(cob.lidos_na_rodada)} nesta coleta, {n(cob.herdados)} herdados de coletas anteriores e {n(cob.sem_leitura)} ainda sem leitura, de {n(cob.elegiveis)} vizinhos
          {cob.idade_max_dias != null ? ` (leitura mais antiga: ${n(cob.idade_max_dias)} dia${cob.idade_max_dias === 1 ? '' : 's'})` : ''}; {n(rs.rotas.vizinhos_completos)} lidos por inteiro.
        </p>
      )}
      <div className="text-xs text-gray-500 space-y-1">
        <p><strong>Direto:</strong> {rs.criterio.asn_direct}.</p>
        <p><strong>Origem:</strong> {rs.criterio.asn_origin}.</p>
      </div>

      {comp && (
        <div className="space-y-2" data-testid="comparacao-cidade">
          <h3 className="text-sm font-semibold text-gray-700">Comparação em {comp.cidade}</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
                  <th className="px-3 py-2 font-medium">Rede</th>
                  <th className="px-3 py-2 font-medium">ASNs diretos</th>
                  <th className="px-3 py-2 font-medium">Critério</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {comp.ixbr && (
                  <tr><td className="px-3 py-2">IX.br {comp.ixbr.ptt.toUpperCase()}</td><td className="px-3 py-2 tabular-nums">{n(comp.ixbr.asn_direct)}</td><td className="px-3 py-2 text-gray-500">primeiro salto do AS_PATH</td></tr>
                )}
                <tr><td className="px-3 py-2">DE-CIX</td><td className="px-3 py-2 tabular-nums">{n(comp.decix.asn_direct)}</td><td className="px-3 py-2 text-gray-500">sessão up no route server</td></tr>
                {Object.entries(comp.externos ?? {}).map(([codigo, e]) => (
                  <tr key={codigo}><td className="px-3 py-2">{codigo}</td><td className="px-3 py-2 tabular-nums">{n(e.membros_peeringdb)}</td><td className="px-3 py-2 text-gray-500">cadastro no PeeringDB</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          {comp.interseccao_direct && (
            <p className="text-xs text-gray-600">
              {n(comp.interseccao_direct.ambos)} ASNs estão nos dois; {n(comp.interseccao_direct.so_decix)} só no DE-CIX; {n(comp.interseccao_direct.so_ixbr)} só no IX.br
              {comp.interseccao_direct.pct_do_decix_no_ixbr != null ? ` (${comp.interseccao_direct.pct_do_decix_no_ixbr.toLocaleString('pt-BR')}% dos ASNs do DE-CIX também estão no IX.br)` : ''}.
              Os critérios diferem: é uma comparação de conjuntos de ASNs, não de tráfego.
            </p>
          )}
          {comp.no_decix_sem_ixbr && comp.no_decix_sem_ixbr.asns.length > 0 && (
            <p className="text-xs text-gray-600">
              Com sessão no DE-CIX e sem direto no IX.br:{' '}
              {comp.no_decix_sem_ixbr.asns.slice(0, 20).map((a, i) => (
                <span key={a}>{i > 0 ? ', ' : ''}<a href={`/asn/${a}`} className="text-primario-600 hover:underline font-mono">AS{a}</a></span>
              ))}
              {comp.no_decix_sem_ixbr.total > 20 ? ` e mais ${n(comp.no_decix_sem_ixbr.total - 20)}` : ''}.
            </p>
          )}
        </div>
      )}
      {rs.peeringdb && (
        <p className="text-xs text-gray-500">
          PeeringDB: {n(rs.peeringdb.cadastrados)} cadastrados; {n(rs.peeringdb.cadastrados_sem_sessao_up_total)} sem sessão up no route server (podem peerar só bilateralmente) e {n(rs.peeringdb.sessao_up_sem_cadastro_total)} com sessão e sem cadastro.
        </p>
      )}
      <p className="text-xs text-gray-400">
        {rs.aviso} Coletado em {rs.coletado_em ?? '—'}{rs.rotas_coletadas_em ? `; rotas em ${rs.rotas_coletadas_em}` : ''} (Alice {rs.versao_alice ?? '—'}).
      </p>
    </section>
  )
}
