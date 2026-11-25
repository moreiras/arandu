// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { BlocoProps } from '../entidade/registry'
import type { FaixaHhi, MercadoGruposMunicipio, MercadoGruposUf, SobreposicaoOperadora } from '../../types/api'
import type { MunicipioCtx } from '../municipio/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import { AvisosRecorte } from '../../components/ui/AvisoRecorte'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }))
export const ROTULO_FAIXA: Record<FaixaHhi, string> = { competitivo: 'competitivo', moderado: 'moderado', concentrado: 'concentrado' }

function Faixa({ f }: { f: FaixaHhi | null }) { return <span className="text-xs text-gray-500">{f ? ROTULO_FAIXA[f] : '—'}</span> }

/** Duas leituras lado a lado: o HHI por CNPJ (declarado) e por grupo econômico (inferido). */
function Duas({ cnpj, grupo, faixaCnpj, faixaGrupo, extra, avisoCnpj, avisoGrupo }: { cnpj: number | null; grupo: number | null; faixaCnpj: FaixaHhi | null; faixaGrupo: FaixaHhi | null; extra?: React.ReactNode; avisoCnpj?: string[]; avisoGrupo?: string[] }) {
  const mudou = faixaCnpj !== faixaGrupo
  return (
    <div className="space-y-2 text-sm">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <div><dt className="text-xs text-gray-500">HHI por CNPJ <span className="text-gray-400">(declarado)</span></dt><dd className="text-lg font-semibold tabular-nums">{n(cnpj)} <Faixa f={faixaCnpj} /> <AvisosRecorte avisos={avisoCnpj} /></dd></div>
        <div><dt className="text-xs text-gray-500">HHI por grupo econômico <span className="text-gray-400">(inferido)</span></dt><dd className="text-lg font-semibold tabular-nums">{n(grupo)} <Faixa f={faixaGrupo} /> <AvisosRecorte avisos={avisoGrupo} /></dd></div>
        {extra}
      </dl>
      {mudou && <p className="rounded border border-aviso-200 bg-aviso-50 px-3 py-2 text-xs text-aviso-700" role="status">Ao juntar os CNPJs do mesmo grupo, a faixa muda de {faixaCnpj} para {faixaGrupo}.</p>}
    </div>
  )
}

/** Concentração do município por CNPJ e por grupo. O grupo é inferido do quadro societário em comum; sobre acessos declarados, não receita. */
export function MercadoGruposMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const m = dados.mercadoGrupos as MercadoGruposMunicipio
  return <Duas cnpj={m.hhi_cnpj} grupo={m.hhi_grupo} faixaCnpj={m.faixa_cnpj} faixaGrupo={m.faixa_grupo} avisoCnpj={m.avisos_cnpj} avisoGrupo={m.avisos_grupo}
    extra={<div><dt className="text-xs text-gray-500">Maior {m.lider_grupo.e_grupo ? 'grupo' : 'operadora'}</dt><dd className="font-medium">{m.lider_grupo.empresa}</dd><dd className="text-xs text-gray-500">{m.lider_grupo.share.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% dos acessos · {n(m.n_cnpjs)} CNPJs, {n(m.n_grupos)} entidades</dd></div>} />
}

export function MercadoGruposUfBloco({ dados }: BlocoProps<UfCtx>) {
  const m = dados.mercadoGrupos as MercadoGruposUf
  return <Duas cnpj={m.hhi_cnpj} grupo={m.hhi_grupo} faixaCnpj={m.faixa_cnpj} faixaGrupo={m.faixa_grupo} avisoCnpj={m.avisos_cnpj} avisoGrupo={m.avisos_grupo}
    extra={<><div><dt className="text-xs text-gray-500">Base do HHI</dt><dd className="text-xs text-gray-600">{n(m.acessos)} acessos · {n(m.n_cnpjs)} CNPJs, {n(m.n_grupos)} grupos{m.lider_grupo_share != null ? ` · maior grupo ou operadora: ${m.lider_grupo_share.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}% dos acessos` : ''}</dd></div><div><dt className="text-xs text-gray-500">Municípios que mudam de faixa</dt><dd className="text-lg font-semibold tabular-nums">{n(m.municipios_mudam_de_faixa)} <span className="text-xs font-normal text-gray-500">de {n(m.municipios)}</span></dd></div></>} />
}

/** Operadoras que mais aparecem nos mesmos municípios: presença conjunta, não rivalidade nem disputa de clientes. */
export function SobreposicaoBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const s = dados.sobreposicao as SobreposicaoOperadora
  if (s.concorrentes.length === 0) return <p className="text-sm text-gray-500">Nenhuma outra operadora declarou acessos nos mesmos municípios.</p>
  return (
    <div className="overflow-x-auto" data-testid="sobreposicao">
      <table className="min-w-full text-sm">
        <thead className="text-xs text-gray-500"><tr><th className="px-2 py-1 text-left">Operadora</th><th className="px-2 py-1 text-right">Municípios em comum</th><th className="px-2 py-1 text-right">Acessos dela nesses municípios</th><th className="px-2 py-1 text-right">Acessos desta operadora neles</th></tr></thead>
        <tbody>
          {s.concorrentes.map((c) => (
            <tr key={c.cnpj} className="border-t border-gray-100">
              <td className="px-2 py-1"><Link to={`/operadora/${c.cnpj}`} className="text-primario-700 hover:underline">{c.empresa || c.cnpj}</Link>{c.mesmo_grupo && <span className="ml-2 text-xs text-gray-500">(mesmo grupo, inferido)</span>}</td>
              <td className="px-2 py-1 text-right tabular-nums">{n(c.municipios_em_comum)}</td><td className="px-2 py-1 text-right tabular-nums">{n(c.acessos_dele_nos_comuns)}</td><td className="px-2 py-1 text-right tabular-nums">{n(c.acessos_dela_nos_comuns)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
