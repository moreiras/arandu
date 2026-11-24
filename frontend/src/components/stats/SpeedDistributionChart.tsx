import { useMemo, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { DistribVelocidade } from '../../types/api'
import { UF_REGION, REGION_ORDER } from '../../utils/regioes'
import { VerDados } from '../ui/VerDados'

const fmt = (n: number) => n.toLocaleString('pt-BR')

type Tipo = 'todos' | 'pf' | 'pj'

/** Extrai o primeiro número da faixa e normaliza pra Mbps ("512kbps a 2Mbps" → 0.512,
 *  "12Mbps a 34Mbps" → 12) — a Anatel mistura Kbps/Mbps na mesma faixa e não garante
 *  ordem alfabética coerente com velocidade, então comparar os rótulos crus erra a
 *  posição de faixas como "512kbps a 2Mbps" (viria depois de "12Mbps a 34Mbps"). */
function faixaOrdem(label: string): number {
  const m = label.match(/([\d.,]+)\s*(k|m)?bps/i)
  if (!m) return Number.POSITIVE_INFINITY
  const valor = parseFloat(m[1].replace(/\./g, '').replace(',', '.'))
  return m[2]?.toLowerCase() === 'k' ? valor / 1000 : valor
}

export function SpeedDistributionChart({ distrib }: { distrib: DistribVelocidade | undefined }) {
  const [regiao, setRegiao] = useState<string>('Brasil')
  const [tipo, setTipo] = useState<Tipo>('todos')

  const ufsDaRegiao = useMemo(() => {
    if (regiao === 'Brasil') return null
    return new Set(Object.keys(UF_REGION).filter(uf => UF_REGION[uf] === regiao))
  }, [regiao])

  const data = useMemo(() => {
    if (!distrib) return []
    const totals: Record<string, number> = {}
    for (const [uf, porTipo] of Object.entries(distrib)) {
      if (ufsDaRegiao && !ufsDaRegiao.has(uf)) continue
      const fontes = tipo === 'todos' ? [porTipo.pf, porTipo.pj] : [porTipo[tipo]]
      for (const faixas of fontes) {
        for (const [faixa, acessos] of Object.entries(faixas ?? {})) {
          totals[faixa] = (totals[faixa] ?? 0) + acessos
        }
      }
    }
    return Object.entries(totals)
      .map(([faixa, acessos]) => ({ faixa, acessos }))
      .sort((a, b) => faixaOrdem(a.faixa) - faixaOrdem(b.faixa))
  }, [distrib, ufsDaRegiao, tipo])

  const semDados = !distrib || Object.keys(distrib).length === 0

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h3 className="text-sm font-medium text-gray-700">Distribuição de velocidade contratada</h3>
        <div className="flex items-center gap-2">
          <select
            aria-label="Região"
            value={regiao}
            onChange={e => setRegiao(e.target.value)}
            className="text-xs border border-gray-200 rounded-md px-2 py-1 text-gray-600"
          >
            <option value="Brasil">Brasil</option>
            {REGION_ORDER.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <div role="group" aria-label="Tipo de assinante" className="flex rounded-md border border-gray-200 overflow-hidden text-xs">
            {(['todos', 'pf', 'pj'] as Tipo[]).map(t => (
              <button
                key={t}
                type="button"
                aria-pressed={tipo === t}
                onClick={() => setTipo(t)}
                className={`px-2.5 py-1 ${tipo === t ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                {t === 'todos' ? 'Todos' : t.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {semDados ? (
        <div className="text-xs text-gray-400 py-8 text-center">
          Distribuição por faixa de velocidade ainda não disponível para este snapshot.
        </div>
      ) : (
        <>
<ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 40, left: 4 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="faixa" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={60} interval={0} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => [fmt(v), 'Acessos']} />
            <Bar dataKey="acessos" fill="#0891b2" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <VerDados dados={data as unknown as Record<string, unknown>[]} />
</>
      )}
    </div>
  )
}
