// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const MAX_LINHAS = 15
const data = (iso: string | null | undefined) => (iso ? iso.slice(0, 16).replace('T', ' ') + ' UTC' : '—')

/**
 * Route servers do PTT: estado de cada route server no Alice-LG e as sessões dos membros, cruzadas com o cadastro do IX.br. É o que o route server mostra
 * na data da coleta: sessão down não diz de quem é a causa e "cadastrado sem sessão" pode ser peering bilateral. Sem adjetivar (política editorial); o cabeçalho
 * reordena a lista inteira de membros down antes do corte nas primeiras linhas, e a lista completa está em Rankings → Route servers.
 */
export function RouteServersBloco({ dados }: BlocoProps<PttCtx>) {
  const rs = dados.routeServers!
  const r = rs.resumo
  const membrosDown = rs.membros.filter((m) => m.membro_down).sort((a, b) => (b.max_dias_down ?? 0) - (a.max_dias_down ?? 0) || a.asn - b.asn)
  const sem = rs.membros.filter((m) => m.cadastrado_sem_sessao)
  const incertos = rs.rs.filter((x) => x.vizinhos_incerto)
  const down = useOrdenacao(membrosDown, {
    asn: { valor: (m) => m.asn, primeiro: 'asc' },
    nome: (m) => m.nome || null,
    sessoes: (m) => m.sessoes,
    dias: (m) => m.max_dias_down,
  })
  const servidores = useOrdenacao(rs.rs, {
    rs: (x) => x.rs,
    em: (x) => (x.consultado ? x.vizinhos_em : null),
    up: (x) => x.sessoes_up,
    cache: (x) => x.estado_rotas,
    rotas: (x) => x.rotas_importadas,
  })
  return (
    <div className="space-y-3 text-sm" data-testid="route-servers">
      <dl className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div><dt className="text-xs text-gray-500">Route servers com sessões atuais</dt><dd className="text-lg font-semibold tabular-nums">{n(r.rs_vizinhos_atuais)} de {n(r.rs)}</dd>
          <dd className="text-xs text-gray-500">{n(r.rs_consultados)} consultados · cache de rotas pronto em {n(r.rs_rotas_prontas)}</dd></div>
        <div><dt className="text-xs text-gray-500">Sessões up</dt><dd className="text-lg font-semibold tabular-nums">{n(r.sessoes_up)} de {n(r.sessoes)}</dd>
          <dd className="text-xs text-gray-500">{n(r.sessoes_down)} down</dd></div>
        <div><dt className="text-xs text-gray-500">Cadastrados com sessão</dt><dd className="text-lg font-semibold tabular-nums">{n(r.cadastrados_com_sessao)} de {n(r.cadastrados)}</dd>
          <dd className="text-xs text-gray-500">{n(r.cadastrados_sem_sessao)} sem sessão · {n(r.sessao_sem_cadastro)} sessão sem cadastro</dd></div>
        <div><dt className="text-xs text-gray-500">Membros com todas as sessões down há {rs.parametros.dias_down} dias ou mais</dt><dd className="text-lg font-semibold tabular-nums">{n(r.membros_down)}</dd></div>
        <div><dt className="text-xs text-gray-500">Membros com {Math.round(rs.parametros.uso_limite * 100)}% ou mais do limite de importação</dt><dd className="text-lg font-semibold tabular-nums">{n(r.membros_perto_do_limite)}</dd></div>
      </dl>
      {incertos.length > 0 && (
        <p className="text-xs text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2">
          {incertos.map((x) => `${x.rs} (sessões atualizadas em ${data(x.vizinhos_em)})`).join('; ')}: o Alice não confirma sessões com menos de {rs.parametros.idade_max_vizinhos_h} horas
          para {incertos.length === 1 ? 'esse route server' : 'esses route servers'}; as sessões {incertos.length === 1 ? 'dele' : 'deles'} não contam como membro down.
        </p>
      )}
      {membrosDown.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 mb-1">Membros com todas as sessões down há {rs.parametros.dias_down} dias ou mais</h4>
          <table className="min-w-full text-xs">
            <thead className="text-gray-500"><tr>
              <ThOrdenavel {...down.props('asn')} className="text-left px-2 py-1">ASN</ThOrdenavel>
              <ThOrdenavel {...down.props('nome')} className="text-left px-2 py-1">Nome cadastrado</ThOrdenavel>
              <ThOrdenavel {...down.props('sessoes')} alinhar="right" className="text-right px-2 py-1">Sessões</ThOrdenavel>
              <ThOrdenavel {...down.props('dias')} alinhar="right" className="text-right px-2 py-1">Maior tempo de queda (dias)</ThOrdenavel>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {down.ordenados.slice(0, MAX_LINHAS).map((m) => (
                <tr key={m.asn}>
                  <td className="px-2 py-1"><Link to={`/asn/${m.asn}`} className="text-primario-600 hover:underline">AS{m.asn}</Link></td>
                  <td className="px-2 py-1">{m.nome || '—'}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(m.sessoes)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(m.max_dias_down)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {membrosDown.length > MAX_LINHAS && (
            <p className="text-xs text-gray-500 mt-1">e mais {n(membrosDown.length - MAX_LINHAS)}. <Link to={`/rankings?aba=route-servers&ixp=${dados.code}`} className="text-primario-600 hover:underline">Ver a lista em Rankings</Link></p>
          )}
        </div>
      )}
      {sem.length > 0 && (
        <p className="text-xs text-gray-600">
          Cadastrados no IX.br sem sessão nos route servers ({n(sem.length)}): {sem.slice(0, MAX_LINHAS).map((m) => `AS${m.asn}`).join(', ')}{sem.length > MAX_LINHAS ? ` e mais ${n(sem.length - MAX_LINHAS)}` : ''}.
          Pode ser peering bilateral.
        </p>
      )}
      <details className="text-xs text-gray-600">
        <summary className="cursor-pointer">Route servers do PTT ({n(rs.rs.length)})</summary>
        <table className="min-w-full mt-1">
          <thead className="text-gray-500"><tr>
            <ThOrdenavel {...servidores.props('rs')} className="text-left px-2 py-1">Route server</ThOrdenavel>
            <ThOrdenavel {...servidores.props('em')} className="text-left px-2 py-1">Sessões atualizadas em</ThOrdenavel>
            <ThOrdenavel {...servidores.props('up')} alinhar="right" className="text-right px-2 py-1">Sessões up</ThOrdenavel>
            <ThOrdenavel {...servidores.props('cache')} className="text-left px-2 py-1">Cache de rotas</ThOrdenavel>
            <ThOrdenavel {...servidores.props('rotas')} alinhar="right" className="text-right px-2 py-1">Rotas importadas</ThOrdenavel>
          </tr></thead>
          <tbody className="divide-y divide-gray-100">
            {servidores.ordenados.map((x) => (
              <tr key={x.rs}>
                <td className="px-2 py-1 font-mono">{x.rs}</td>
                <td className="px-2 py-1">{x.consultado ? data(x.vizinhos_em) : 'não consultado'}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(x.sessoes_up)} de {n(x.sessoes)}</td>
                <td className="px-2 py-1">{x.estado_rotas ?? '—'}, {data(x.rotas_atualizadas_em)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(x.rotas_importadas)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-1 text-gray-500">O estado do cache de rotas (READY, BUSY ou ERROR) é o do Alice para as rotas importadas e não diz nada das sessões.</p>
      </details>
      <p className="text-xs text-gray-500">{rs.limites}</p>
      <p className="text-xs text-gray-400">Fonte: {rs.fonte ?? 'Looking Glass do IX.br (Alice-LG)'}{rs.versao_alice ? ` ${rs.versao_alice}` : ''}; cadastro de membros do IX.br. Coletado em {data(rs.coletado_em)}.</p>
    </div>
  )
}
