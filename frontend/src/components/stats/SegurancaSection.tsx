// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fetchSegurancaResumo } from '../../services/api'
import type { AgregadoSinal } from '../../types/api'
import { VerDados } from '../ui/VerDados'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../ui/EstadoDados'

const FAIXAS = [
  { chave: 'ate_10', rotulo: 'até 10%', cor: '#9ca3af' },
  { chave: 'de_10_a_90', rotulo: 'de 10 a 90%', cor: '#60a5fa' },
  { chave: 'acima_de_90', rotulo: 'acima de 90%', cor: '#1d4ed8' },
] as const

function dadosPorUf(por: Record<string, { rov: AgregadoSinal }>) {
  return Object.entries(por).map(([uf, a]) => ({ uf, ...(a.rov.faixas ?? { ate_10: 0, de_10_a_90: 0, acima_de_90: 0 }) }))
}

/** Validação RPKI medida (APNIC) por UF, em faixas neutras de percentual: quantos ASNs com amostra suficiente ficam em cada faixa. Agregado, sem nomes de empresas. */
/** `semResumo`: omite a frase com os totais do país quando a página já os mostra em KPIs (aba Segurança do Panorama técnico). */
export function SegurancaSection({ date, semResumo = false }: { date?: string; semResumo?: boolean }) {
  const q = useQuery({ queryKey: ['seguranca-resumo', date ?? 'atual'], queryFn: () => fetchSegurancaResumo({ date }), staleTime: Infinity, gcTime: Infinity, retry: false })
  if (q.isLoading) return null
  if (q.isError && ehErroDeAcessoOuFalha(q.error)) return <EstadoDados erro={q.error} oQue="a validação RPKI por UF" />
  if (q.isError || !q.data?.por_uf) return null
  const r = q.data
  const porUf = q.data.por_uf
  const b = r.agregado
  return (
    <section className="space-y-3" aria-label="Segurança de roteamento">
      <div>
        <h3 className="text-titulo-4 text-gray-800">ROV por UF da sede do ASN (medido pelo APNIC)</h3>
        <p className="text-xs text-gray-500 mt-1">
          {!semResumo && <>Em {b.rov.asns?.toLocaleString('pt-BR')} ASNs do Brasil com amostra suficiente (≥ {r.parametros.min_amostras}), a mediana é de {b.rov.mediana_pct?.toLocaleString('pt-BR')}%
          e a média ponderada pela amostra, de {b.rov.media_ponderada_pct?.toLocaleString('pt-BR')}%; {b.rov.faixas?.acima_de_90.toLocaleString('pt-BR')} ficam acima de 90%.{' '}</>}
          O percentual é a parcela das medições em que a rede não alcança uma rota RPKI-inválida (alto = valida). É medição por amostragem, não declaração da rede.
        </p>
      </div>
      <div className="h-80 bg-white border border-gray-200 rounded-lg p-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dadosPorUf(porUf)} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="uf" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} label={{ value: 'ASNs', angle: -90, position: 'insideLeft', fontSize: 11 }} />
            <Tooltip />
            <Legend />
            {FAIXAS.map((f) => <Bar key={f.chave} dataKey={f.chave} name={f.rotulo} stackId="a" fill={f.cor} isAnimationActive={false} />)}
          </BarChart>
        </ResponsiveContainer>
        <VerDados dados={dadosPorUf(porUf) as unknown as Record<string, unknown>[]} />
      </div>
      <p className="text-xs text-gray-400">Fonte: {r.fontes.rov.fonte}, janela de {r.fontes.rov.janela_dias} dias até {r.fontes.rov.as_of} ({r.fontes.rov.copyright}). {r.limites}</p>
    </section>
  )
}
