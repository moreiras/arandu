// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao, type Acessor } from '../../../lib/ordenacao'
import { eventosDaSerie } from '../eventosSerie'

const CORES = ['#2563eb', '#d97706', '#059669', '#7c3aed', '#0891b2', '#475569']
const mes = (m: string) => m.slice(2).replace('-', '/')
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

/** Participação das maiores operadoras no município ao longo de 13 meses, sobre acessos declarados ao SICI (não receita). Mês sem declaração fica sem ponto, nunca zero. */
export function SerieMercadoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const s = dados.serieMercado!
  const pontos = s.meses.map((m, i) => ({ mes: mes(m), ...Object.fromEntries(s.lideres.map((l) => [l.empresa || l.cnpj, l.share[i]])), hhi: s.hhi[i], acessos: s.acessos[i] }))
  const eventos = eventosDaSerie(s)
  const mesesComEvento = [...new Set(eventos.map((e) => e.mes))]
  const com = s.acessos.filter((v) => v != null).length
  // Linhas são os meses (índices); a ordem inicial é a cronológica.
  const acessores: Record<string, Acessor<number>> = {
    mes: { valor: (i) => s.meses[i], primeiro: 'asc' },
    acessos: (i) => s.acessos[i],
    hhi: (i) => s.hhi[i],
    ...Object.fromEntries(s.lideres.map((l) => [`l:${l.cnpj}`, (i: number) => l.share[i]])),
  }
  const { ordenados, props } = useOrdenacao(s.meses.map((_, i) => i), acessores)
  if (com < 2) return <p className="text-sm text-gray-500">Só há {com} mês com declaração neste município na janela; a série precisa de ao menos dois.</p>
  return (
    <div className="space-y-2" data-testid="serie-mercado">
      <div role="img" aria-label={`Participação das ${s.lideres.length} maiores operadoras em ${s.meses.length} meses`}>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={pontos} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} width={44} />
            {mesesComEvento.map((m) => <ReferenceLine key={m} x={mes(m)} stroke="#94a3b8" strokeDasharray="4 3" label={{ value: 'evento', position: 'insideTop', fontSize: 10, fill: '#475569' }} />)}
            <Tooltip formatter={(v: number) => pct(v)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {s.lideres.map((l, i) => <Line key={l.cnpj} type="monotone" dataKey={l.empresa || l.cnpj} stroke={CORES[i % CORES.length]} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-500">Participação sobre os acessos fixos declarados ao SICI (não sobre receita). Entram as operadoras que estiveram entre as {s.parametros.lideres} maiores do município em algum mês da janela, até {s.parametros.linhas_max ?? s.lideres.length} linhas pelos maiores acessos na janela ({s.lideres.length} {s.lideres.length === 1 ? 'linha' : 'linhas'} aqui); mês sem declaração do CNPJ fica sem ponto.</p>
      {eventos.length > 0 && (
        <ul className="list-disc pl-5 text-xs text-gray-600" data-testid="eventos-serie" aria-label="Eventos de declaração na série">
          {eventos.map((e) => <li key={`${e.cnpj}-${e.mes}`}>{e.texto}</li>)}
        </ul>
      )}
      <details className="text-sm">
        <summary className="cursor-pointer text-primario-600 hover:underline">Ver dados (tabela)</summary>
        <div className="overflow-x-auto mt-2"><table className="text-xs min-w-full" data-tabela="grade">
          <thead className="text-gray-500"><tr><ThOrdenavel {...props('mes')} className="text-left px-2 py-1">Mês</ThOrdenavel><ThOrdenavel {...props('acessos')} alinhar="right" className="text-right px-2 py-1">Acessos</ThOrdenavel><ThOrdenavel {...props('hhi')} alinhar="right" className="text-right px-2 py-1">HHI</ThOrdenavel>{s.lideres.map((l) => <ThOrdenavel key={l.cnpj} {...props(`l:${l.cnpj}`)} alinhar="right" className="text-right px-2 py-1">{l.empresa || l.cnpj}</ThOrdenavel>)}<th scope="col" className="text-left px-2 py-1">Evento</th></tr></thead>
          <tbody>{ordenados.map((i) => { const m = s.meses[i]; return (
            <tr key={m} className="border-t border-gray-100"><td className="px-2 py-1">{m}</td><td className="px-2 py-1 text-right tabular-nums">{s.acessos[i]?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{s.hhi[i] ?? '—'}</td>
              {s.lideres.map((l) => <td key={l.cnpj} className="px-2 py-1 text-right tabular-nums">{pct(l.share[i])}</td>)}<td className="px-2 py-1">{eventos.filter((e) => e.indice === i).map((e) => e.texto).join('; ') || '—'}</td></tr>) })}</tbody>
        </table></div>
      </details>
    </div>
  )
}
