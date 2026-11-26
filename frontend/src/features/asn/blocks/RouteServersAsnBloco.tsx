// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { DICA_PREFIXOS_LIMITE } from '../../../lib/textos'
import { Dica } from '../../../components/ui/Dica'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'
import { palavra } from '../../../lib/sintese'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const data = (iso: string | null | undefined) => (iso ? iso.slice(0, 16).replace('T', ' ') + ' UTC' : '—')

/**
 * Sessões do ASN nos route servers do IX.br, por PTT. É o que o route server mostra na data da coleta: sessão down não diz de quem é a causa,
 * e o motivo é o que o Alice reporta. Sessão em route server sem frescor confirmado (cache de vizinhos do Alice velho) vem marcada como incerta.
 */
export function RouteServersAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const rs = dados.routeServers!
  const ptts = Object.entries(rs.ixps).sort(([a], [b]) => a.localeCompare(b))
  const porPtt = useOrdenacao(ptts, {
    ptt: ([code]) => code,
    up: ([, x]) => x.up,
    down: ([, x]) => x.down,
    dias: ([, x]) => x.max_dias_down,
    uso: ([, x]) => x.max_uso_limite,
    cadastro: ([, x]) => (x.cadastrado ? 'cadastrado' : 'sem cadastro no IX.br'),
  })
  const sessoes = ptts.flatMap(([code, x]) => x.lista.map((s) => ({ code, s })))
  const porSessao = useOrdenacao(sessoes, {
    rs: ({ s }) => s.rs,
    ip: ({ s }) => s.ip,
    estado: ({ s }) => (s.estado === 'up' ? 'up' : 'down'),
    dias: ({ s }) => s.dias,
    recebidas: ({ s }) => s.recebidas,
    erro: ({ s }) => s.erro || null,
  })
  return (
    <div className="space-y-3 text-sm" data-testid="route-servers-asn">
      <p className="text-xs text-gray-600">
        {n(rs.total.sessoes)} {palavra(rs.total.sessoes, 'sessão', 'sessões')} em {n(rs.total.ixps)} {palavra(rs.total.ixps, 'PTT', 'PTTs')}: {n(rs.total.up)} up e {n(rs.total.down)} down.
      </p>
      <table className="min-w-full text-xs">
        <thead className="text-gray-500"><tr>
          <ThOrdenavel {...porPtt.props('ptt')} className="text-left px-2 py-1">PTT</ThOrdenavel><ThOrdenavel {...porPtt.props('up')} alinhar="right" className="text-right px-2 py-1">Sessões up</ThOrdenavel><ThOrdenavel {...porPtt.props('down')} alinhar="right" className="text-right px-2 py-1">Down</ThOrdenavel>
          <ThOrdenavel {...porPtt.props('dias')} alinhar="right" className="text-right px-2 py-1">Maior tempo de queda (dias)</ThOrdenavel>
          {/* Sem botão de ordem: a Dica é um botão e não pode ir dentro do botão do cabeçalho. */}
          <ThOrdenavel {...porPtt.props('uso')} alinhar="right" className="text-right px-2 py-1" extra={<Dica texto={DICA_PREFIXOS_LIMITE} rotulo="Prefixos / limite" />}>Prefixos / limite</ThOrdenavel><ThOrdenavel {...porPtt.props('cadastro')} className="text-left px-2 py-1">Cadastro</ThOrdenavel>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {porPtt.ordenados.map(([code, x]) => (
            <tr key={code}>
              <td className="px-2 py-1"><Link to={`/ixp/${code}`} className="text-primario-600 hover:underline">{code.toUpperCase()}</Link></td>
              <td className="px-2 py-1 text-right tabular-nums">{n(x.up)} de {n(x.sessoes)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{n(x.down)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{x.max_dias_down != null ? n(x.max_dias_down) : '—'}</td>
              <td className="px-2 py-1 text-right tabular-nums">{x.max_uso_limite != null ? `${Math.round(x.max_uso_limite * 100)}%` : '—'}</td>
              <td className="px-2 py-1">{x.cadastrado ? 'cadastrado' : 'sem cadastro no IX.br'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <details className="text-xs text-gray-600">
        <summary className="cursor-pointer">Cada sessão</summary>
        <table className="min-w-full mt-1">
          <thead className="text-gray-500"><tr>
            <ThOrdenavel {...porSessao.props('rs')} className="text-left px-2 py-1">Route server</ThOrdenavel><ThOrdenavel {...porSessao.props('ip')} className="text-left px-2 py-1">IP do par</ThOrdenavel><ThOrdenavel {...porSessao.props('estado')} className="text-left px-2 py-1">Estado</ThOrdenavel>
            <ThOrdenavel {...porSessao.props('dias')} alinhar="right" className="text-right px-2 py-1">Dias no estado</ThOrdenavel><ThOrdenavel {...porSessao.props('recebidas')} alinhar="right" className="text-right px-2 py-1">Recebidas / limite</ThOrdenavel><ThOrdenavel {...porSessao.props('erro')} className="text-left px-2 py-1">Último erro</ThOrdenavel>
          </tr></thead>
          <tbody className="divide-y divide-gray-100">
            {porSessao.ordenados.map(({ code, s }) => (
              <tr key={`${code}-${s.rs}-${s.ip}`}>
                <td className="px-2 py-1 font-mono">{s.rs}</td>
                <td className="px-2 py-1 font-mono">{s.ip}</td>
                <td className="px-2 py-1">{s.estado === 'up' ? 'up' : 'down'}{s.rs_incerto ? ' (sem frescor confirmado: incerta)' : ''}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(s.dias)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(s.recebidas)} / {n(s.limite)}</td>
                <td className="px-2 py-1">{s.erro || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
      <p className="text-xs text-gray-500">{rs.limites}</p>
      <p className="text-xs text-gray-400">Fonte: {rs.fonte ?? 'Looking Glass do IX.br (Alice-LG)'}{rs.versao_alice ? ` ${rs.versao_alice}` : ''}; cadastro de membros do IX.br. Coletado em {data(rs.coletado_em)}.</p>
    </div>
  )
}
