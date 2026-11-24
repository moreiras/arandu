// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Kpi } from '../../../components/ui'
import { useGrupoMercado } from '../../../hooks/entidades/entidades'
import type { BlocoProps } from '../../entidade/registry'
import type { GrupoCtx } from '../contexto'
import type { GrupoMercadoFixo } from '../../../types/api'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
const mes = (m: string) => m.slice(2).replace('-', '/')
const FAIXA: Record<string, string> = { competitivo: 'competitivo', moderado: 'moderadamente concentrado', concentrado: 'concentrado' }
const GRAU_FAIXA: Record<string, number> = { competitivo: 0, moderado: 1, concentrado: 2 }

/** Tabela da série mensal (o "Ver dados" do gráfico); começa em ordem cronológica. */
function TabelaSerie({ serie }: { serie: GrupoMercadoFixo['serie'] }) {
  const { ordenados, props } = useOrdenacao(serie, { mes: { valor: (s) => s.mes, primeiro: 'asc' }, acessos: (s) => s.acessos, parcela: (s) => s.parcela })
  return (
    <div className="overflow-x-auto mt-2"><table className="text-xs min-w-full" aria-label="Série mensal de acessos do grupo" data-tabela="grade"><thead className="text-gray-500"><tr>
      <ThOrdenavel {...props('mes')} className="text-left px-2 py-1">Mês</ThOrdenavel><ThOrdenavel {...props('acessos')} alinhar="right" className="text-right px-2 py-1">Acessos</ThOrdenavel><ThOrdenavel {...props('parcela')} alinhar="right" className="text-right px-2 py-1">Parcela</ThOrdenavel></tr></thead>
      <tbody>{ordenados.map((s) => <tr key={s.mes} className="border-t border-gray-100"><td className="px-2 py-1">{s.mes}</td><td className="px-2 py-1 text-right tabular-nums">{n(s.acessos)}</td><td className="px-2 py-1 text-right tabular-nums">{pct(s.parcela)}</td></tr>)}</tbody></table></div>
  )
}

function TabelaUfs({ porUf }: { porUf: GrupoMercadoFixo['por_uf'] }) {
  const { ordenados, props } = useOrdenacao(porUf, {
    uf: (u) => u.uf, acessos: (u) => u.acessos, parcela_do_grupo: (u) => u.parcela_do_grupo, parcela_na_uf: (u) => u.parcela_na_uf,
    hhi_grupo: (u) => u.hhi_grupo, faixa: (u) => (u.faixa_grupo ? GRAU_FAIXA[u.faixa_grupo] : null),
  })
  return (
    <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="Acessos do grupo por UF" data-tabela="grade">
      <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><ThOrdenavel {...props('uf')} className="py-1 pr-3">UF</ThOrdenavel><ThOrdenavel {...props('acessos')} alinhar="right" className="pr-3 text-right">Acessos</ThOrdenavel><ThOrdenavel {...props('parcela_do_grupo')} alinhar="right" className="pr-3 text-right">% do grupo</ThOrdenavel><ThOrdenavel {...props('parcela_na_uf')} alinhar="right" className="pr-3 text-right">% da UF</ThOrdenavel><ThOrdenavel {...props('hhi_grupo')} alinhar="right" className="pr-3 text-right">HHI da UF (por grupo)</ThOrdenavel><ThOrdenavel {...props('faixa')}>Faixa da UF</ThOrdenavel></tr></thead>
      <tbody>{ordenados.map((u) => (
        <tr key={u.uf} className="border-b border-gray-100"><td className="py-1 pr-3"><Link to={`/uf/${u.uf}`} className="text-primario-600 hover:underline">{u.uf}</Link></td>
          <td className="pr-3 text-right tabular-nums">{n(u.acessos)}</td><td className="pr-3 text-right tabular-nums">{pct(u.parcela_do_grupo)}</td><td className="pr-3 text-right tabular-nums">{pct(u.parcela_na_uf)}</td>
          <td className="pr-3 text-right tabular-nums">{n(u.hhi_grupo)}</td><td className="text-gray-600">{u.faixa_grupo ? FAIXA[u.faixa_grupo] ?? u.faixa_grupo : '—'}</td></tr>))}</tbody></table></div>
  )
}

/** Carrega o bloco de mercado do grupo e mostra o estado (carregando, sem dado) antes de entregar o dado ao corpo. */
function ComMercado({ id, children }: { id: string; children: (m: GrupoMercadoFixo) => JSX.Element }) {
  const q = useGrupoMercado(id)
  if (q.isLoading) return <div className="h-32 bg-gray-50 rounded animate-pulse" role="status" aria-label="Carregando" />
  if (!q.data) return <p className="text-sm text-gray-500">Este grupo não tem acessos fixos declarados ao SICI no snapshot (ou o SICI não está publicado).</p>
  return children(q.data)
}

/** Posição do grupo, série de 24 meses e parcela do mercado fixo. É por acessos declarados, não receita; sem "melhor" nem "pior". */
export function SeriePosicaoBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <ComMercado id={dados.grupo.grupo_id}>{(m) => {
    const pontos = m.serie.map((s) => ({ mes: mes(s.mes), acessos: s.acessos, parcela: s.parcela }))
    const com = m.serie.filter((s) => s.acessos != null).length
    const dif = m.posicao.atual != null && m.posicao.ha_12_meses != null ? m.posicao.ha_12_meses - m.posicao.atual : null
    return (
      <div className="space-y-3" data-testid="grupo-serie">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Kpi rotulo={`Posição em ${m.mes_referencia ?? '—'}`} valor={m.posicao.atual != null ? `${n(m.posicao.atual)}º de ${n(m.posicao.unidades)}` : '—'} />
          <Kpi rotulo={`Posição há 12 meses${m.posicao.mes_ha_12_meses ? ` (${m.posicao.mes_ha_12_meses})` : ''}`} valor={m.posicao.ha_12_meses != null ? `${n(m.posicao.ha_12_meses)}º` : '—'} />
          <Kpi rotulo="Parcela dos acessos fixos" valor={pct(m.serie[m.serie.length - 1]?.parcela)} />
          <Kpi rotulo="CNPJs com acessos" valor={`${n(m.cnpjs_com_acessos)} de ${n(m.cnpjs_total)}`} />
        </div>
        {dif != null && dif !== 0 && <p className="text-sm text-gray-600">Em 12 meses o grupo {dif > 0 ? `subiu ${dif}` : `desceu ${-dif}`} {Math.abs(dif) === 1 ? 'posição' : 'posições'} na lista por acessos declarados.</p>}
        {com < 2 ? <p className="text-sm text-gray-500">Só há {com} mês com declaração do grupo na janela; a série precisa de ao menos dois.</p> : (
          <div role="img" aria-label={`Acessos fixos declarados pelo grupo em ${m.meses.length} meses`}>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={pontos} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} width={56} domain={['auto', 'auto']} tickFormatter={(v: number) => (v >= 1e6 ? `${(v / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi` : v >= 1e3 ? `${Math.round(v / 1e3)} mil` : String(v))} />
                <Tooltip formatter={(v: number) => n(v)} />
                <Line type="monotone" dataKey="acessos" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} name="Acessos" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        <p className="text-xs text-gray-500">{m.limites}</p>
        <details className="text-sm"><summary className="cursor-pointer text-primario-600 hover:underline">Ver dados (tabela)</summary>
          <TabelaSerie serie={m.serie} />
        </details>
      </div>
    )
  }}</ComMercado>
}

/** Onde o grupo atua e a concentração do mercado em cada UF (HHI por grupo); faixas em texto, sem cor de veredito. */
export function UfsBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <ComMercado id={dados.grupo.grupo_id}>{(m) => (
    <div className="space-y-2" data-testid="grupo-ufs">
      <TabelaUfs porUf={m.por_uf} />
      <p className="text-xs text-gray-500">Acessos fixos declarados pelas empresas do grupo, por UF. O HHI e a faixa são do mercado inteiro da UF (CNPJs do mesmo grupo contam como um) e dizem quão concentrado é o mercado, não se o grupo é o responsável. Faixas: competitivo (HHI até 1.500), moderado (1.500 a 2.500), concentrado (acima).</p>
    </div>
  )}</ComMercado>
}

/** Presença conjunta nos mesmos municípios: dentro do grupo (CNPJs que atuam no mesmo município) e com outras empresas. Não é rivalidade. */
export function ConcorrentesBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <ComMercado id={dados.grupo.grupo_id}>{(m) => (
    <div className="space-y-3" data-testid="grupo-concorrentes">
      <p className="text-sm text-gray-700">O grupo declara acessos em <strong>{n(m.sobreposicao_interna.municipios)}</strong> municípios; em <strong>{n(m.sobreposicao_interna.com_mais_de_um_cnpj)}</strong> deles mais de um CNPJ do grupo atua ao mesmo tempo (é onde juntar os CNPJs muda a concentração).</p>
      {m.concorrentes.length === 0 ? <p className="text-sm text-gray-500">Sem outras empresas com presença conjunta registrada.</p> : (
        <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="Empresas presentes nos mesmos municípios" data-tabela="grade">
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><th scope="col" className="py-1 pr-3">Empresa</th><th scope="col" className="pr-3 text-right">Municípios em comum</th><th scope="col" className="text-right">Acessos dela nesses municípios</th></tr></thead>
          <tbody>{m.concorrentes.map((c) => <tr key={c.cnpj} className="border-b border-gray-100"><td className="py-1 pr-3"><Link to={`/operadora/${c.cnpj}`} className="text-primario-600 hover:underline">{c.empresa || c.cnpj}</Link></td><td className="pr-3 text-right tabular-nums">{n(c.municipios_em_comum)}</td><td className="text-right tabular-nums">{n(c.acessos_dele_nos_comuns)}</td></tr>)}</tbody></table></div>
      )}
      <p className="text-xs text-gray-500">Presença nos mesmos municípios, não rivalidade: a lista mostra quem mais aparece junto, em ordem de municípios em comum (sem ranking de desempenho). Para cada empresa vale a maior sobreposição com um CNPJ do grupo, não a união. Natureza: {m.natureza}.</p>
    </div>
  )}</ComMercado>
}
