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
import { LinhaProveniencia } from '../../components/ui/Kpi'
import type { MunicipiosPorFaixa } from '../../types/api'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const soma = (f: MunicipiosPorFaixa | undefined) => (f ? f.competitivo + f.moderado + f.concentrado + f.sem_dado : 0)

/**
 * Municípios por faixa de HHI local, por UF (PT-23): o HHI da UF soma operadoras de todos os municípios, e é no município que o cliente escolhe a operadora. Cada município está em uma faixa
 * (ou "sem dado"), por CNPJ e por grupo inferido; a soma por UF é o número de municípios da UF. Contagem, sem lista nominal de líderes: a lista municipal, com a regra e o denominador, fica em `/municipios`.
 */
export function MunicipiosPorFaixaUf({ ufs, resumo }: { ufs: [string, { municipios?: number; municipios_por_faixa_cnpj?: MunicipiosPorFaixa; municipios_por_faixa_grupo?: MunicipiosPorFaixa }][]; resumo: { por_faixa_cnpj?: MunicipiosPorFaixa; por_faixa_grupo?: MunicipiosPorFaixa; municipios: number } }) {
  const { ordenados, props } = useOrdenacao(ufs, {
    uf: ([uf]) => uf, municipios: ([, v]) => v.municipios,
    c0: ([, v]) => v.municipios_por_faixa_cnpj?.competitivo, c1: ([, v]) => v.municipios_por_faixa_cnpj?.moderado, c2: ([, v]) => v.municipios_por_faixa_cnpj?.concentrado,
    g0: ([, v]) => v.municipios_por_faixa_grupo?.competitivo, g1: ([, v]) => v.municipios_por_faixa_grupo?.moderado, g2: ([, v]) => v.municipios_por_faixa_grupo?.concentrado,
  })
  const c = resumo.por_faixa_cnpj, g = resumo.por_faixa_grupo
  const cel = (f: MunicipiosPorFaixa | undefined, k: keyof MunicipiosPorFaixa, tot: number | undefined) => (
    <td className="px-2 py-1 text-right tabular-nums">{n(f?.[k])}{f && tot ? <span className="block text-xs text-gray-600">{(100 * f[k] / tot).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%</span> : null}</td>
  )
  return (
    <div className="space-y-2" data-testid="municipios-por-faixa">
      <p className="text-sm text-gray-700">
        Nos <strong>{n(resumo.municipios)}</strong> municípios, <strong>{n(c?.concentrado)}</strong> têm HHI local de 2.500 ou mais por CNPJ e <strong>{n(g?.concentrado)}</strong> por grupo (inferido);
        {' '}<strong>{n(c?.competitivo)}</strong> e <strong>{n(g?.competitivo)}</strong> ficam abaixo de 1.500.{(c?.sem_dado ?? 0) > 0 && <> {n(c?.sem_dado)} sem dado.</>} O HHI da UF, na tabela acima, soma as operadoras de todos os municípios e não substitui este retrato.
      </p>
      <div className="overflow-x-auto">
        <table className="text-xs min-w-full" data-tabela="grade">
          <caption className="text-left text-xs font-semibold text-gray-700 pb-1">Municípios por faixa de HHI local, por UF (por CNPJ declarado e por grupo inferido)</caption>
          <thead className="text-gray-500">
            <tr><td /><td /><th scope="colgroup" colSpan={3} className="px-2 py-1 text-center border-b border-gray-200">Por CNPJ (declarado)</th><th scope="colgroup" colSpan={3} className="px-2 py-1 text-center border-b border-gray-200">Por grupo (inferido)</th></tr>
            <tr>
              <ThOrdenavel {...props('uf')} className="px-2 py-1 text-left">UF</ThOrdenavel>
              <ThOrdenavel {...props('municipios')} alinhar="right" className="px-2 py-1 text-right">Municípios</ThOrdenavel>
              <ThOrdenavel {...props('c0')} alinhar="right" className="px-2 py-1 text-right">Abaixo de 1.500</ThOrdenavel>
              <ThOrdenavel {...props('c1')} alinhar="right" className="px-2 py-1 text-right">1.500 a 2.499</ThOrdenavel>
              <ThOrdenavel {...props('c2')} alinhar="right" className="px-2 py-1 text-right">2.500 ou mais</ThOrdenavel>
              <ThOrdenavel {...props('g0')} alinhar="right" className="px-2 py-1 text-right">Abaixo de 1.500</ThOrdenavel>
              <ThOrdenavel {...props('g1')} alinhar="right" className="px-2 py-1 text-right">1.500 a 2.499</ThOrdenavel>
              <ThOrdenavel {...props('g2')} alinhar="right" className="px-2 py-1 text-right">2.500 ou mais</ThOrdenavel>
            </tr>
          </thead>
          <tbody>
            {ordenados.map(([uf, v]) => (
              <tr key={uf} className="border-t border-gray-100">
                <th scope="row" className="px-2 py-1 text-left font-normal"><Link to={`/uf/${uf}`} className="text-primario-700 underline">{uf} ({nomeUf(uf)})</Link></th>
                <td className="px-2 py-1 text-right tabular-nums">{n(v.municipios)}</td>
                {cel(v.municipios_por_faixa_cnpj, 'competitivo', v.municipios)}{cel(v.municipios_por_faixa_cnpj, 'moderado', v.municipios)}{cel(v.municipios_por_faixa_cnpj, 'concentrado', v.municipios)}
                {cel(v.municipios_por_faixa_grupo, 'competitivo', v.municipios)}{cel(v.municipios_por_faixa_grupo, 'moderado', v.municipios)}{cel(v.municipios_por_faixa_grupo, 'concentrado', v.municipios)}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-gray-300 text-gray-700">
              <th scope="row" className="px-2 py-1 text-left font-medium">Brasil</th><td className="px-2 py-1 text-right tabular-nums">{n(resumo.municipios)}</td>
              {cel(c, 'competitivo', resumo.municipios)}{cel(c, 'moderado', resumo.municipios)}{cel(c, 'concentrado', resumo.municipios)}{cel(g, 'competitivo', resumo.municipios)}{cel(g, 'moderado', resumo.municipios)}{cel(g, 'concentrado', resumo.municipios)}
            </tr>
          </tfoot>
        </table>
      </div>
      {soma(c) !== resumo.municipios && <p className="text-xs text-gray-600">As faixas não somam o total de municípios neste snapshot; confira o documento.</p>}
    </div>
  )
}

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
          <tbody>{ufs.map(([uf, v]) => <tr key={uf} className="border-t border-gray-100"><td className="px-2 py-1"><Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf} ({nomeUf(uf)})</Link></td><td className="px-2 py-1 text-right tabular-nums">{v.hhi_cnpj?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{v.hhi_grupo?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1">{rotuloFaixaHhi(v.faixa_grupo)}</td><td className="px-2 py-1 text-right tabular-nums">{v.acessos?.toLocaleString('pt-BR') ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{v.n_cnpjs ?? '—'} · {v.n_grupos ?? '—'}</td><td className="px-2 py-1 text-right tabular-nums">{v.lider_grupo_share == null ? '—' : `${v.lider_grupo_share.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`}</td><td className="px-2 py-1"><AvisosRecorte avisos={[...new Set([...(v.avisos_cnpj ?? []), ...(v.avisos_grupo ?? [])])]} /></td></tr>)}</tbody></table>
      )} />
      {d.resumo.por_faixa_cnpj && (
        <MunicipiosPorFaixaUf ufs={porUf} resumo={{ ...d.resumo, por_faixa_cnpj: d.resumo.por_faixa_cnpj, por_faixa_grupo: d.resumo.por_faixa_grupo }} />
      )}
      {d.brasil?.hhi_cnpj != null && (
        <p className="text-sm text-gray-700" data-testid="hhi-nacional">
          Como contraste, o HHI do mercado fixo do país inteiro é <strong>{n(d.brasil.hhi_cnpj)}</strong> por CNPJ ({n(d.brasil.n_cnpjs)} empresas, {n(d.brasil.acessos)} acessos). {d.brasil.nota}
        </p>
      )}
      <LinhaProveniencia selo="inferido" fonte="Anatel (SICI), acessos fixos declarados; grupo inferido do quadro societário (Receita Federal)" dataRef={d.mes_referencia} />
      <p className="text-xs text-gray-500">{d.limites} Fonte: {d.fonte}. Mês de referência {d.mes_referencia}; snapshot {d.snapshot_date}.</p>
    </div>
  )
}
