// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchMercadoGrupos } from '../../services/api'
import { useResumo } from '../panorama/useResumo'
import { CartogramaIndicador } from '../estados/CartogramaIndicador'
import { nomeUf } from '../../lib/ufs'
import { useOrdenacao } from '../../lib/ordenacao'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { AvisosRecorte } from '../../components/ui/AvisoRecorte'
import { NOTA_FAIXAS_HHI, rotuloFaixaHhi } from '../../lib/referencias'

/** Concentração do mercado fixo por UF, por CNPJ e por grupo econômico (Panorama de mercado). O grupo é inferido e o HHI é sobre acessos declarados. */
export function ConcentracaoPanorama() {
  const { date } = useResumo()
  const q = useQuery({ queryKey: ['mercado-grupos', date], queryFn: () => fetchMercadoGrupos(date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
  const porUf = useMemo(() => Object.entries(q.data?.ufs ?? {}).sort(([a], [b]) => a.localeCompare(b)), [q.data])
  const { ordenados: ufs, props } = useOrdenacao(porUf, {
    uf: ([uf]) => uf,
    cnpj: ([, v]) => v.hhi_cnpj,
    grupo: ([, v]) => v.hhi_grupo,
    faixa: ([, v]) => v.faixa_grupo,
  })
  if (q.isLoading) return <div className="h-40 bg-gray-50 rounded animate-pulse" />
  if (!q.data) return <p className="text-sm text-gray-500">O cruzamento de concentração por grupo não está publicado neste snapshot.</p>
  const d = q.data; const r = d.resumo
  return (
    <div className="space-y-4" data-testid="concentracao">
      <p className="text-sm text-gray-700">
        Em <strong>{r.mudam_de_faixa.toLocaleString('pt-BR')}</strong> dos {r.municipios.toLocaleString('pt-BR')} municípios a faixa de concentração muda quando os CNPJs do mesmo grupo contam como um
        {Object.keys(r.transicoes).length > 0 && <> ({Object.entries(r.transicoes).map(([k, v]) => `${k}: ${v}`).join('; ')})</>}. {NOTA_FAIXAS_HHI}
      </p>
      <CartogramaIndicador titulo="HHI por grupo econômico, por UF" indicadores={[
        { id: 'grupo', rotulo: 'Por grupo (inferido)', valor: (uf) => d.ufs[uf]?.hhi_grupo ?? null, texto: (v) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }), maximo: 10000 },
        { id: 'cnpj', rotulo: 'Por CNPJ (declarado)', valor: (uf) => d.ufs[uf]?.hhi_cnpj ?? null, texto: (v) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }), maximo: 10000 },
      ]} verDados={(
        <table className="text-xs min-w-full" data-tabela="grade"><thead className="text-gray-500"><tr><ThOrdenavel {...props('uf')} className="px-2 py-1 text-left">UF</ThOrdenavel><ThOrdenavel {...props('cnpj')} alinhar="right" className="px-2 py-1 text-right">HHI por CNPJ</ThOrdenavel><ThOrdenavel {...props('grupo')} alinhar="right" className="px-2 py-1 text-right">HHI por grupo</ThOrdenavel><ThOrdenavel {...props('faixa')} className="px-2 py-1 text-left">Faixa por grupo</ThOrdenavel><th scope="col" className="px-2 py-1 text-right">Acessos</th><th scope="col" className="px-2 py-1 text-right">CNPJs · grupos</th><th scope="col" className="px-2 py-1 text-right">Maior grupo ou operadora</th><th scope="col" className="px-2 py-1 text-left">Aviso</th></tr></thead>
          <tbody>{ufs.map(([uf, v]) => <tr key={uf} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf} — {nomeUf(uf)}</Link></td><td className="px-2 py-1 text-right tabular-nums">{v.hhi_cnpj?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{v.hhi_grupo?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1">{rotuloFaixaHhi(v.faixa_grupo)}</td><td className="px-2 py-1 text-right tabular-nums">{v.acessos?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{v.n_cnpjs ?? '—'} · {v.n_grupos ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{v.lider_grupo_share == null ? '—' : `${v.lider_grupo_share.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`}</td><td className="px-2 py-1"><AvisosRecorte avisos={[...new Set([...(v.avisos_cnpj ?? []), ...(v.avisos_grupo ?? [])])]} /></td></tr>)}</tbody></table>
      )} />
      <p className="text-xs text-gray-500">{d.limites} Fonte: {d.fonte}. Mês de referência {d.mes_referencia}; snapshot {d.snapshot_date}.</p>
    </div>
  )
}
