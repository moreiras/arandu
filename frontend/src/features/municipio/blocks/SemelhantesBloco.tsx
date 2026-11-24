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
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../../../components/ui/EstadoDados'
import { useOrdenacao } from '../../../lib/ordenacao'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }))
const razao = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 2 }))

/** Municípios do mesmo porte: quem tem entre metade e o dobro dos domicílios e como o município se compara em penetração e fibra. É uma regra de porte, não um modelo de "cidades parecidas". */
export function SemelhantesBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const date = useActiveDate()
  const q = useQuery({ queryKey: ['mun-semelhantes', dados.ibge, date], queryFn: () => fetchMunicipiosSemelhantes(dados.ibge, date ?? undefined), staleTime: 10 * 60 * 1000 })
  const r = q.data
  // Os itens são o conjunto escolhido pelo porte (os mais próximos em domicílios), não um corte por coluna: ordená-los não esconde
  // ninguém. O próprio município fica sempre na primeira linha.
  const { ordenados, props } = useOrdenacao(r?.items, {
    nome: (m) => m.nome,
    domicilios: (m) => m.domicilios,
    acessos: (m) => m.acessos,
    penetracao: (m) => m.penetracao,
    fibra: (m) => m.fibra_pct,
    km: { valor: (m) => m.km_ptt, primeiro: 'asc' },
  })
  if (q.isLoading) return <div className="h-24 bg-gray-50 rounded animate-pulse" />
  if (!r) return q.isError && ehErroDeAcessoOuFalha(q.error) ? <EstadoDados erro={q.error} oQue="a comparação com municípios do mesmo porte" /> : null
  const pos = (p: { posicao: number; de: number } | null) => (p ? `${p.posicao}º de ${p.de}` : 'sem dado')
  return (
    <div className="space-y-2 text-sm" data-testid="semelhantes">
      <p className="text-gray-700">Entre {n(r.total_do_porte)} municípios do mesmo porte ({r.criterio.replace('mesmo porte: ', '')}): penetração <strong>{pos(r.posicao.penetracao)}</strong>, fibra <strong>{pos(r.posicao.fibra_pct)}</strong> (1º = maior valor).</p>
      <div className="overflow-x-auto"><table className="min-w-full text-xs">
        <thead className="text-gray-500"><tr>
          <ThOrdenavel {...props('nome')} className="text-left px-2 py-1">Município</ThOrdenavel>
          <ThOrdenavel {...props('domicilios')} alinhar="right" className="text-right px-2 py-1">Domicílios</ThOrdenavel>
          <ThOrdenavel {...props('acessos')} alinhar="right" className="text-right px-2 py-1">Acessos fixos</ThOrdenavel>
          <ThOrdenavel {...props('penetracao')} alinhar="right" className="text-right px-2 py-1">Por domicílio</ThOrdenavel>
          <ThOrdenavel {...props('fibra')} alinhar="right" className="text-right px-2 py-1">Fibra</ThOrdenavel>
          <ThOrdenavel {...props('km')} alinhar="right" className="text-right px-2 py-1">km ao PTT</ThOrdenavel>
        </tr></thead>
        <tbody>
          {[r.municipio, ...ordenados].map((m, i) => (
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
