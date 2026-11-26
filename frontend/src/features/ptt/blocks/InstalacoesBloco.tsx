// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { FacilitiesPtt, PortasIxp } from '../../../types/api'
import type { PttCtx } from '../contexto'
import { AtribuicaoPeeringDb, LinkInstalacao, SeloCadastro, fmtMbps, localDe, n } from '../../instalacoes/comum'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'
import { palavra } from '../../../lib/sintese'

/** Instalações onde o PeeringDB diz que o PTT tem presença, e, nos PTTs externos, as portas por velocidade. Autodeclarado; sem veredito sobre as instalações. */
export function InstalacoesPtt({ facilities, portas }: { facilities?: FacilitiesPtt | null; portas?: PortasIxp | null }) {
  const { ordenados, props } = useOrdenacao(facilities?.items, {
    nome: (f) => f.nome,
    org: (f) => f.org_nome,
    local: (f) => (localDe(f) === '—' ? null : localDe(f)),
    redes: (f) => f.n_redes ?? f.redes_declaradas,
    ptts: (f) => f.n_ptts,
    cadastro: { valor: (f) => f.cadastro?.dias, primeiro: 'asc' },
  })
  return (
    <div className="space-y-4 text-sm" data-testid="instalacoes-ptt">
      {facilities && (
        <div className="space-y-2">
          <p><span className="font-medium">{n(facilities.total)} {palavra(facilities.total, 'instalação', 'instalações')}</span> {palavra(facilities.total, 'cadastrada', 'cadastradas')} para este PTT no PeeringDB</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <ThOrdenavel {...props('nome')} className="py-1 pr-3 font-medium">Instalação</ThOrdenavel><ThOrdenavel {...props('org')} className="py-1 pr-3 font-medium">Organização</ThOrdenavel><ThOrdenavel {...props('local')} className="py-1 pr-3 font-medium">Local</ThOrdenavel>
                  <ThOrdenavel {...props('redes')} alinhar="right" className="py-1 pr-3 font-medium text-right">Redes</ThOrdenavel><ThOrdenavel {...props('ptts')} alinhar="right" className="py-1 pr-3 font-medium text-right">PTTs</ThOrdenavel><ThOrdenavel {...props('cadastro')} className="py-1 font-medium">Cadastro</ThOrdenavel>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {ordenados.map((f) => (
                  <tr key={f.id}>
                    <td className="py-1 pr-3"><LinkInstalacao f={f} /></td>
                    <td className="py-1 pr-3 text-gray-600">{f.org_nome ?? '—'}</td>
                    <td className="py-1 pr-3 text-gray-600">{localDe(f)}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">{n(f.n_redes ?? f.redes_declaradas)}</td>
                    <td className="py-1 pr-3 text-right tabular-nums">{n(f.n_ptts)}</td>
                    <td className="py-1"><SeloCadastro c={f.cadastro} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <AtribuicaoPeeringDb meta={facilities} />
        </div>
      )}
      {portas && (
        <div className="space-y-2" data-testid="portas-ptt">
          <p>
            <span className="font-medium">{n(portas.portas)} {palavra(portas.portas, 'porta', 'portas')}</span> de {n(portas.membros)} {palavra(portas.membros, 'membro', 'membros')}: mediana {fmtMbps(portas.mediana_mbps)}, maior {fmtMbps(portas.maior_mbps)}, soma declarada {fmtMbps(portas.capacidade_mbps)}
          </p>
          <ul className="flex flex-wrap gap-2 text-xs">
            {Object.entries(portas.por_velocidade).map(([v, q]) => (
              <li key={v} className="rounded border border-gray-200 bg-white px-2 py-0.5">{fmtMbps(Number(v))}: <span className="tabular-nums">{n(q)}</span></li>
            ))}
          </ul>
          <p className="text-xs text-gray-500">{portas.limites}</p>
          <AtribuicaoPeeringDb meta={portas} />
        </div>
      )}
    </div>
  )
}

export function InstalacoesBloco({ dados }: BlocoProps<PttCtx>) {
  return <InstalacoesPtt facilities={dados.facilities} portas={dados.portas} />
}
