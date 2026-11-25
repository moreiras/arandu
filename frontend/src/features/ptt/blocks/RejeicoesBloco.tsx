// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { descreverCobertura } from '../cobertura'

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
  const motivos = useOrdenacao(r?.por_motivo, { motivo: (m) => m.rotulo ?? m.codigo, rotas: (m) => m.rotas, asns: (m) => m.asns })
  return (
    <div className="space-y-3 text-sm" data-testid="rejeicoes">
      {r && (
        <>
          <p className="text-xs text-gray-600">
            Rejeições (nível 2): {descreverCobertura(r.cobertura, 'vizinhos')}.
            {' '}{n(r.rotas_rejeitadas)} rotas rejeitadas de {n(r.asns_com_rejeicao)} ASNs, {n(r.rotas_com_motivo_decodificado)} com motivo decodificado (uma rota pode ter mais de um motivo: as linhas abaixo somam {n(r.soma_dos_motivos)}).
          </p>
          <table className="min-w-full text-xs">
            <thead className="text-gray-500"><tr><ThOrdenavel {...motivos.props('motivo')} className="text-left px-2 py-1">Motivo</ThOrdenavel><ThOrdenavel {...motivos.props('rotas')} alinhar="right" className="text-right px-2 py-1">Rotas</ThOrdenavel><ThOrdenavel {...motivos.props('asns')} alinhar="right" className="text-right px-2 py-1">ASNs</ThOrdenavel></tr></thead>
            <tbody className="divide-y divide-gray-100">
              {motivos.ordenados.map((m) => (
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
          Política declarada (nível 3): {descreverCobertura(p.cobertura, 'vizinhos')}; {n(p.asns_com_dado)} ASNs com dado. Perfis inferidos:{' '}
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
