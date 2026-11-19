// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const MAX_ASNS = 10

/**
 * Rejeições e política nos route servers do PTT: rotas que o route server rejeitou, por motivo decodificado, e o resumo da política declarada por communities.
 * Mede só os vizinhos coletados (a cobertura vem junto): não é o PTT inteiro. O perfil é inferido; nada aqui é veredito sobre um membro.
 */
export function RejeicoesBloco({ dados }: BlocoProps<PttCtx>) {
  const rj = dados.rejeicoes!
  const r = rj.rejeicoes
  const p = rj.politica
  return (
    <div className="space-y-3 text-sm" data-testid="rejeicoes">
      {r && (
        <>
          <p className="text-xs text-gray-600">
            Coletado o nível 2 de {n(r.cobertura.coletados)} dos {n(r.cobertura.elegiveis)} vizinhos com rotas rejeitadas{r.cobertura.herdados ? ` (${n(r.cobertura.herdados)} de rodada anterior)` : ''}:
            {' '}{n(r.rotas_rejeitadas)} rotas rejeitadas de {n(r.asns_com_rejeicao)} ASNs, {n(r.rotas_com_motivo_decodificado)} com motivo decodificado (uma rota pode ter mais de um motivo: as linhas abaixo somam {n(r.soma_dos_motivos)}).
          </p>
          <table className="min-w-full text-xs">
            <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Motivo</th><th className="text-right px-2 py-1">Rotas</th><th className="text-right px-2 py-1">ASNs</th></tr></thead>
            <tbody className="divide-y divide-gray-100">
              {r.por_motivo.map((m) => (
                <tr key={m.codigo}><td className="px-2 py-1">{m.rotulo ?? m.codigo} <span className="font-mono text-gray-400">{m.codigo}</span></td><td className="px-2 py-1 text-right tabular-nums">{n(m.rotas)}</td><td className="px-2 py-1 text-right tabular-nums">{n(m.asns)}</td></tr>
              ))}
            </tbody>
          </table>
          {r.asns.length > 0 && (
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer">ASNs com mais rotas rejeitadas ({n(r.asns_total)})</summary>
              <table className="min-w-full mt-1">
                <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">ASN</th><th className="text-left px-2 py-1">Nome no route server</th><th className="text-right px-2 py-1">Rotas rejeitadas</th></tr></thead>
                <tbody className="divide-y divide-gray-100">
                  {r.asns.slice(0, MAX_ASNS).map((a) => (
                    <tr key={a.asn}><td className="px-2 py-1"><Link to={`/asn/${a.asn}`} className="text-primario-600 hover:underline">AS{a.asn}</Link></td><td className="px-2 py-1">{a.nome ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{n(a.rotas)}</td></tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}
        </>
      )}
      {p && (
        <p className="text-xs text-gray-600">
          Política declarada: {n(p.cobertura.coletados)} de {n(p.cobertura.elegiveis)} vizinhos coletados no nível 3 ({n(p.asns_com_dado)} ASNs). Perfis inferidos:{' '}
          {Object.keys(p.perfis).length ? Object.entries(p.perfis).map(([k, v]) => `${n(v)} ${k}`).join(', ') : 'nenhum'}. Blackhole em {n(p.blackhole.asns)} ASNs ({n(p.blackhole.rotas)} rotas).
          {' '}<Link to={`/communities?ixp=${dados.code}`} className="text-primario-600 hover:underline">Communities usadas neste PTT</Link>
        </p>
      )}
      {!r && !p && <p className="text-xs text-gray-600">Sem coleta de rotas dos route servers deste PTT no snapshot.</p>}
      <p className="text-xs text-gray-500">{rj.limites}</p>
      <p className="text-xs text-gray-400">Fonte: {rj.fonte ?? 'Looking Glass do IX.br (Alice-LG)'}{rj.versao_alice ? ` ${rj.versao_alice}` : ''}. Rejeições coletadas em {rj.coletado_nivel2?.slice(0, 16).replace('T', ' ') ?? '—'} UTC.</p>
    </div>
  )
}
