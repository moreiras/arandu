// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchInterconexaoAsn } from '../../../services/api'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { nomesFamilias } from '../../../lib/familias'

const fam = (f: string[]) => nomesFamilias(f)

/**
 * O que é mensurável na interconexão do AS: onde ele origina prefixos sem ter sessão no route server (e quem os entrega), onde cadastro e route server não batem e o que os route servers rejeitam.
 * São fatos observados na data da coleta: não dizem com quem o AS troca tráfego (peering bilateral não é visível) nem recomendam nada.
 */
export function InterconexaoMensuravelBloco({ dados }: BlocoProps<AsnCtx>) {
  const q = useQuery({ queryKey: ['interconexao-as', dados.doc.asn, dados.date], queryFn: () => fetchInterconexaoAsn(dados.doc.asn, dados.date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
  if (q.isLoading) return <div className="h-24 bg-gray-50 rounded animate-pulse" />
  const r = q.data
  if (!r) return <p className="text-sm text-gray-500">Sem dado de interconexão para este AS neste snapshot.</p>
  const nada = !r.origem_sem_direto.length && !r.sessoes.length && !r.rejeicoes.length
  return (
    <div className="space-y-4 text-sm" data-testid="interconexao-mensuravel">
      {nada && <p className="text-gray-600">Nenhum item mensurável neste snapshot: o AS não origina prefixos em PTT sem ter sessão no route server, cadastro e route servers coincidem e não há rejeição coletada.</p>}
      {r.origem_sem_direto.length > 0 && (
        <div><h3 className="mb-1 font-medium text-gray-700">Origina prefixos sem ter sessão no route server ({r.origem_sem_direto.length} PTTs)</h3>
          <ul className="divide-y divide-gray-100 rounded border border-gray-100">
            {r.origem_sem_direto.map((o) => (
              <li key={o.ixp} className="flex flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1.5">
                <Link to={`/ixp/${o.ixp}`} className="text-primario-700 hover:underline">{o.nome}</Link><span className="text-xs text-gray-500">{o.uf}{o.mesma_uf && ' · mesma UF da sede'}{o.km_da_sede != null && ` · a ${Math.round(o.km_da_sede).toLocaleString('pt-BR')} km da sede`}</span>
                <span className="text-xs text-gray-600">{fam(o.familias)}</span>
                {o.carregadores.length > 0
                  ? <span className="text-xs text-gray-500">entregue por {o.carregadores.map((c) => `AS${c.asn}${c.via?.length ? ` via ${c.via.map((v) => `AS${v}`).join(', ')}` : ''}${c.vinculo === 'mesmo_cnpj' ? ', mesmo CNPJ' : c.vinculo === 'mesma_org' ? ', mesma organização (inferido)' : ''} (${c.caminhos})`).join('; ')}</span>
                  : r.carregadores_disponiveis && <span className="text-xs text-gray-500">caminho observado sem AS identificável</span>}
              </li>
            ))}
          </ul>
          {!r.carregadores_disponiveis && <p className="mt-1 text-xs text-gray-500">Os caminhos observados não estão disponíveis para este AS; por isso não aparece quem entrega.</p>}
          <p className="mt-1 text-xs text-gray-500">Como ler: entregue por = AS com sessão no PTT que aparece por último no caminho observado (via = o AS logo depois da origem); um caminho por prefixo coletado, não volume de tráfego.</p>
        </div>
      )}
      {r.sessoes.length > 0 && (
        <div><h3 className="mb-1 font-medium text-gray-700">Cadastro e sessões nos route servers</h3>
          <ul className="divide-y divide-gray-100 rounded border border-gray-100">{r.sessoes.map((s) => <li key={s.ixp + s.situacao} className="px-3 py-1.5"><Link to={`/ixp/${s.ixp}`} className="text-primario-700 hover:underline">{s.nome}</Link> <span className="text-gray-600">({s.rotulo})</span></li>)}</ul>
        </div>
      )}
      {r.rejeicoes.length > 0 && (
        <div><h3 className="mb-1 font-medium text-gray-700">Rejeições e política declarada nos route servers</h3>
          <ul className="divide-y divide-gray-100 rounded border border-gray-100">
            {r.rejeicoes.map((j) => (
              <li key={j.ixp} className="px-3 py-1.5"><Link to={`/ixp/${j.ixp}`} className="text-primario-700 hover:underline">{j.nome}</Link>
                {j.rotas_rejeitadas > 0 && <span className="text-gray-600"> ({j.rotas_rejeitadas.toLocaleString('pt-BR')} rotas rejeitadas{j.motivos.length > 0 && `: ${j.motivos.map((m) => `${m.rotulo} (${m.rotas})`).join('; ')}`})</span>}
                {j.perfil && <span className="text-xs text-gray-500"> · perfil {j.perfil}{j.perfil_inferido ? ' (inferido)' : ''}</span>}
                {j.acoes.length > 0 && <span className="text-xs text-gray-500"> · ações declaradas: {j.acoes.map((a) => a.replace(/_/g, ' ')).join(', ')}</span>}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-xs text-gray-500">{r.limites}</p>
    </div>
  )
}
