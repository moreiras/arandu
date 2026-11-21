// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { familiasV6Primeiro } from '../../../lib/familias'
import type { RsPolMotivo } from '../../../types/api'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : v > 0 && v < 0.01 ? '<1%' : `${Math.round(v * 100)}%`)
const dia = (iso: string | null | undefined) => iso ?? '—'
const ACOES: Record<string, string> = {
  nao_exportar_para: 'Não exportar para o AS', exportar_somente_para: 'Exportar somente para o AS', nao_exportar_rir: 'Não exportar por RIR', exportar_somente_rir: 'Exportar somente por RIR',
  nao_exportar_ptt: 'Não exportar para o PTT', nao_exportar_rtt: 'Não exportar por RTT', nao_exportar_perda: 'Não exportar por perda de pacotes',
}
const MAX_ALVOS = 6

/** Rejeições por motivo; a lista de motivos vem inteira, então ordena no navegador. "Sem motivo" fica sempre no fim. */
function TabelaMotivos({ motivos, semMotivo }: { motivos: RsPolMotivo[]; semMotivo: number }) {
  const { ordenados, props } = useOrdenacao(motivos, { motivo: (m) => m.rotulo ?? m.codigo, rotas: (m) => m.rotas })
  return (
    <table className="min-w-full text-xs">
      <thead className="text-gray-500"><tr>
        <ThOrdenavel {...props('motivo')} className="text-left px-2 py-1">Motivo</ThOrdenavel>
        <ThOrdenavel {...props('rotas')} alinhar="right" className="text-right px-2 py-1">Rotas</ThOrdenavel>
        <th scope="col" className="text-left px-2 py-1">Amostra de prefixos</th>
      </tr></thead>
      <tbody className="divide-y divide-gray-100">
        {ordenados.map((m) => (
          <tr key={m.codigo}>
            <td className="px-2 py-1">{m.rotulo ?? m.codigo} <span className="font-mono text-gray-400">{m.codigo}</span></td>
            <td className="px-2 py-1 text-right tabular-nums">{n(m.rotas)}</td>
            <td className="px-2 py-1 font-mono">{m.amostra.length ? m.amostra.map((a) => a.p).join(', ') : '—'}</td>
          </tr>
        ))}
        {semMotivo > 0 && <tr><td className="px-2 py-1">sem motivo decodificado</td><td className="px-2 py-1 text-right tabular-nums">{n(semMotivo)}</td><td /></tr>}
      </tbody>
    </table>
  )
}

/**
 * Política de roteamento do ASN nos route servers do IX.br, por PTT coletado: o que as communities das rotas recebidas declaram (não exportar para, exportar somente
 * para…) e o que o route server rejeitou, por motivo. O perfil (aberto, seletivo, restritivo) é INFERIDO por heurística e só existe para quem foi coletado; é a declaração do
 * membro e a decisão do route server, não tráfego nem relação comercial.
 */
export function PoliticaRsAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const pol = dados.politicaRs!
  const ptts = Object.entries(pol.ixps).sort(([a], [b]) => a.localeCompare(b))
  const ev = pol.evidencia_rs
  return (
    <div className="space-y-4 text-sm" data-testid="politica-rs-asn">
      {ptts.map(([code, x]) => (
        <section key={code} className="space-y-2" data-testid={`politica-rs-${code}`}>
          <h4 className="text-xs font-semibold text-gray-700"><Link to={`/ixp/${code}`} className="text-primario-600 hover:underline">{code.toUpperCase()}</Link></h4>
          {x.politica && (
            <div className="space-y-1">
              <p>
                <span className="inline-block rounded bg-gray-100 border border-gray-200 px-2 py-0.5 text-xs font-medium">
                  Perfil {x.politica.perfil ?? 'indeterminado'} <span className="font-normal text-gray-500">(inferido)</span>
                </span>{' '}
                <span className="text-xs text-gray-600">{x.politica.perfil_criterio}.</span>
              </p>
              <p className="text-xs text-gray-600">
                {n(x.politica.rotas)} rotas recebidas coletadas ({familiasV6Primeiro(x.politica.afis).join(' e ')}), {n(x.politica.communities_distintas)} communities distintas; blackhole (65535:666) em {n(x.politica.blackhole_rotas)} rotas;
                RPKI: {n(x.politica.rpki.valid)} válidas, {n(x.politica.rpki.unknown)} desconhecidas, {n(x.politica.rpki.invalid)} inválidas. Coletado em {dia(x.politica.coletado_de)}{x.politica.coletado_ate !== x.politica.coletado_de ? ` a ${dia(x.politica.coletado_ate)}` : ''}
                {x.politica.herdado ? ' (parte de rodada anterior)' : ''}.
              </p>
              {Object.keys(x.politica.acoes).length === 0
                ? <p className="text-xs text-gray-600">Nenhuma community de ação de exportação nas rotas coletadas.</p>
                : (
                  <table className="min-w-full text-xs">
                    <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Ação declarada</th><th className="text-left px-2 py-1">Alvo</th><th className="text-right px-2 py-1">Rotas</th><th className="text-right px-2 py-1">% das rotas</th></tr></thead>
                    <tbody className="divide-y divide-gray-100">
                      {Object.entries(x.politica.acoes).flatMap(([classe, a]) => a.alvos.slice(0, MAX_ALVOS).map((al) => (
                        <tr key={`${classe}-${al.alvo}`}>
                          <td className="px-2 py-1">{ACOES[classe] ?? classe}</td>
                          <td className="px-2 py-1">{classe.endsWith('_para') && al.alvo != null ? <Link to={`/asn/${al.alvo}`} className="text-primario-600 hover:underline">AS{al.alvo}</Link> : al.rotulo}{al.forma === 'equivalente_padrao' ? ' *' : ''}</td>
                          <td className="px-2 py-1 text-right tabular-nums">{n(al.rotas)}</td>
                          <td className="px-2 py-1 text-right tabular-nums">{pct(al.fracao)}</td>
                        </tr>
                      )))}
                    </tbody>
                  </table>
                )}
              {Object.values(x.politica.acoes).some((a) => a.alvos.some((al) => al.forma === 'equivalente_padrao')) && (
                <p className="text-xs text-gray-500">* community padrão ou estendida lida como a grande equivalente do dicionário do Alice (equivalência assumida pela forma).</p>
              )}
            </div>
          )}
          {x.rejeicoes && (
            <div className="space-y-1">
              <p className="text-xs text-gray-600">
                O route server rejeitou {n(x.rejeicoes.rotas)} rotas do AS{pol.asn} ({familiasV6Primeiro(x.rejeicoes.afis).join(' e ')}; coletado em {dia(x.rejeicoes.coletado_de)}{x.rejeicoes.herdado ? ', parte de rodada anterior' : ''}):
              </p>
              <TabelaMotivos motivos={x.rejeicoes.motivos} semMotivo={x.rejeicoes.sem_motivo} />
            </div>
          )}
        </section>
      ))}
      {ev && ev.rotas_rejeitadas > 0 && (
        <p className="text-xs text-gray-600">
          Evidência do route server (insumo da prontidão, não veredito sobre o AS): {n(ev.rotas_rejeitadas)} rotas rejeitadas em {n(ev.ptts)} PTT(s), das quais {n(ev.rpki_invalido)} com RPKI inválido
          e {n(ev.bogon)} bogon.
        </p>
      )}
      <p className="text-xs text-gray-500">{pol.limites}</p>
      <p className="text-xs text-gray-400">Fonte: {pol.fonte ?? 'Looking Glass do IX.br (Alice-LG)'}{pol.versao_alice ? ` ${pol.versao_alice}` : ''}. <Link to="/communities" className="text-primario-600 hover:underline">Explorador de communities</Link></p>
    </div>
  )
}
