// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'

const CORES = ['#2563eb', '#d97706', '#059669', '#7c3aed']
const mes = (m: string) => m.slice(2).replace('-', '/')
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

/** Participação das maiores operadoras no município ao longo de 13 meses, sobre acessos declarados ao SICI (não receita). Mês sem declaração fica sem ponto, nunca zero. */
export function SerieMercadoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const s = dados.serieMercado!
  const pontos = s.meses.map((m, i) => ({ mes: mes(m), ...Object.fromEntries(s.lideres.map((l) => [l.empresa || l.cnpj, l.share[i]])), hhi: s.hhi[i], acessos: s.acessos[i] }))
  const com = s.acessos.filter((v) => v != null).length
  if (com < 2) return <p className="text-sm text-gray-500">Só há {com} mês com declaração neste município na janela; a série precisa de ao menos dois.</p>
  return (
    <div className="space-y-2" data-testid="serie-mercado">
      <div role="img" aria-label={`Participação das ${s.lideres.length} maiores operadoras em ${s.meses.length} meses`}>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={pontos} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} width={44} />
            <Tooltip formatter={(v: number) => pct(v)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {s.lideres.map((l, i) => <Line key={l.cnpj} type="monotone" dataKey={l.empresa || l.cnpj} stroke={CORES[i % CORES.length]} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-500">Participação sobre os acessos fixos declarados ao SICI (não sobre receita); as {s.lideres.length} maiores do mês de referência ({s.mes_referencia}); mês sem declaração fica sem ponto.</p>
      <details className="text-sm">
        <summary className="cursor-pointer text-primario-600 hover:underline">Ver dados (tabela)</summary>
        <div className="overflow-x-auto mt-2"><table className="text-xs min-w-full" data-tabela="grade">
          <thead className="text-gray-500"><tr><th className="text-left px-2 py-1">Mês</th><th className="text-right px-2 py-1">Acessos</th><th className="text-right px-2 py-1">HHI</th>{s.lideres.map((l) => <th key={l.cnpj} className="text-right px-2 py-1">{l.empresa || l.cnpj}</th>)}</tr></thead>
          <tbody>{s.meses.map((m, i) => (
            <tr key={m} className="border-t border-gray-100"><td className="px-2 py-1">{m}</td><td className="px-2 py-1 text-right tabular-nums">{s.acessos[i]?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{s.hhi[i] ?? '—'}</td>
              {s.lideres.map((l) => <td key={l.cnpj} className="px-2 py-1 text-right tabular-nums">{pct(l.share[i])}</td>)}</tr>))}</tbody>
        </table></div>
      </details>
    </div>
  )
}
