// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchMunicipiosSemelhantes } from '../../../services/api'
import { useActiveDate } from '../../../hooks/useSnapshot'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }))
const razao = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }))

/** Municípios do mesmo porte: quem tem entre metade e o dobro dos domicílios e como o município se compara em penetração e fibra. É uma regra de porte, não um modelo de "cidades parecidas". */
export function SemelhantesBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const date = useActiveDate()
  const q = useQuery({ queryKey: ['mun-semelhantes', dados.ibge, date], queryFn: () => fetchMunicipiosSemelhantes(dados.ibge, date ?? undefined), staleTime: 10 * 60 * 1000 })
  const r = q.data
  if (q.isLoading) return <div className="h-24 bg-gray-50 rounded animate-pulse" />
  if (!r) return null
  const pos = (p: { posicao: number; de: number } | null) => (p ? `${p.posicao}º de ${p.de}` : 'sem dado')
  return (
    <div className="space-y-2 text-sm" data-testid="semelhantes">
      <p className="text-gray-700">Entre {n(r.total_do_porte)} municípios do mesmo porte ({r.criterio.replace('mesmo porte: ', '')}): penetração <strong>{pos(r.posicao.penetracao)}</strong>, fibra <strong>{pos(r.posicao.fibra_pct)}</strong> (1º = maior valor).</p>
      <div className="overflow-x-auto"><table className="min-w-full text-xs">
        <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Município</th><th className="text-right px-2 py-1">Domicílios</th><th className="text-right px-2 py-1">Acessos fixos</th><th className="text-right px-2 py-1">Por domicílio</th><th className="text-right px-2 py-1">Fibra</th><th className="text-right px-2 py-1">km ao PTT</th></tr></thead>
        <tbody>
          {[r.municipio, ...r.items].map((m, i) => (
            <tr key={m.ibge} className={`border-t border-gray-100 ${i === 0 ? 'font-medium bg-primario-50' : ''}`}>
              <td className="px-2 py-1">{i === 0 ? m.nome : <Link to={`/municipio/${m.ibge}`} className="text-primario-700 hover:underline">{m.nome}</Link>} <span className="text-gray-400">{m.uf}</span></td>
              <td className="px-2 py-1 text-right tabular-nums">{n(m.domicilios)}</td><td className="px-2 py-1 text-right tabular-nums">{n(m.acessos)}</td><td className="px-2 py-1 text-right tabular-nums">{razao(m.penetracao)}</td>
              <td className="px-2 py-1 text-right tabular-nums">{m.fibra_pct == null ? '—' : `${n(m.fibra_pct)}%`}</td><td className="px-2 py-1 text-right tabular-nums">{n(m.km_ptt)}</td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  )
}
