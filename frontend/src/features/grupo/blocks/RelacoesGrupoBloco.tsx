// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import { useGrupoBloco } from '../../../hooks/entidades/entidades'
import type { BlocoProps } from '../../entidade/registry'
import type { GrupoCtx } from '../contexto'
import type { GrupoRelacoes } from '../../../types/api'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const fmtCnpj = (c: string) => (c.length === 14 ? `${c.slice(0, 2)}.${c.slice(2, 5)}.${c.slice(5, 8)}/${c.slice(8, 12)}-${c.slice(12)}` : c)

function Empresa({ cnpj, nome }: { cnpj: string; nome: string }) {
  return <><Link to={`/operadora/${cnpj}`} className="text-primario-600 hover:underline">{nome}</Link> <span className="font-mono text-xs text-gray-500">{fmtCnpj(cnpj)}</span></>
}

/** Com que evidência as empresas do grupo estão ligadas: tipo da ligação e quantos sócios a sustentam. Sem nome nem CPF de sócio; é indício societário, não prova de operação conjunta. */
export function RelacoesGrupoBloco({ dados }: BlocoProps<GrupoCtx>) {
  const q = useGrupoBloco<GrupoRelacoes>(dados.grupo.grupo_id, 'relacoes')
  const { ordenados: ligacoes, props } = useOrdenacao(q.data?.ligacoes, {
    tipo: (l) => l.tipo_rotulo,
    de: (l) => l.de_nome,
    para: (l) => l.para_nome,
    socios: (l) => l.socios,
  })
  if (q.isLoading) return <div className="h-32 bg-gray-50 rounded animate-pulse" role="status" aria-label="Carregando" />
  const r = q.data
  if (!r) return <p className="text-sm text-gray-500">O cruzamento do quadro societário não está publicado neste snapshot.</p>
  return (
    <div className="space-y-4" data-testid="grupo-relacoes">
      <p className="text-sm text-gray-700">
        {r.ligacoes.length === 0
          ? <>As {n(r.empresas)} {r.empresas === 1 ? 'empresa' : 'empresas'} deste grupo não têm ligação societária registrada entre si{r.empresas === 1 ? ' (grupo de uma empresa só)' : ''}.</>
          : <>{n(r.ligacoes.length)} {r.ligacoes.length === 1 ? 'ligação' : 'ligações'} entre as {n(r.empresas)} empresas do grupo, na base da Receita Federal de {r.referencia_receita ?? 'data não informada'}.</>}
      </p>
      {r.ligacoes.length > 0 && (
        <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="Ligações entre as empresas do grupo" data-tabela="grade">
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200">
            <ThOrdenavel {...props('tipo')} className="py-1 pr-3">Tipo de ligação</ThOrdenavel>
            <ThOrdenavel {...props('de')} className="pr-3">Empresa</ThOrdenavel>
            <ThOrdenavel {...props('para')} className="pr-3">Empresa</ThOrdenavel>
            <ThOrdenavel {...props('socios')} alinhar="right" className="text-right">Sócios na evidência</ThOrdenavel>
          </tr></thead>
          <tbody>{ligacoes.map((l) => (
            <tr key={`${l.tipo}-${l.de}-${l.para}`} className="border-b border-gray-100 align-top">
              <td className="py-1 pr-3">{l.tipo_rotulo}</td>
              <td className="pr-3"><Empresa cnpj={l.de} nome={l.de_nome} />{l.tipo === 'controle_parcial' && <span className="block text-xs text-gray-500">controla parte de</span>}</td>
              <td className="pr-3"><Empresa cnpj={l.para} nome={l.para_nome} /></td>
              <td className="text-right tabular-nums">{n(l.socios)}</td>
            </tr>))}</tbody></table></div>
      )}
      {r.controladoras_externas.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-1">Controladoras externas (pessoas jurídicas fora do universo de telecomunicações)</h3>
          <ul className="text-sm space-y-0.5">{r.controladoras_externas.map((h) => <li key={h.cnpj_basico}>{h.razao_social ?? h.cnpj_basico} <span className="text-xs text-gray-500">(CNPJ básico {h.cnpj_basico}{h.situacao_cadastral ? ` · ${h.situacao_cadastral.toLowerCase()}` : ''}{h.natureza_juridica ? ` · ${h.natureza_juridica}` : ''})</span> · controla {n(h.controla.length)} {h.controla.length === 1 ? 'empresa' : 'empresas'} do grupo</li>)}</ul>
        </div>
      )}
      {r.fora_do_grupo.total > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-primario-600 hover:underline">{n(r.fora_do_grupo.total)} {r.fora_do_grupo.total === 1 ? 'empresa tem' : 'empresas têm'} ligação parcial com o grupo, mas não entram nele</summary>
          <ul className="mt-2 space-y-0.5">{r.fora_do_grupo.itens.map((f) => <li key={f.cnpj}><Empresa cnpj={f.cnpj} nome={f.empresa} /> <span className="text-xs text-gray-500">· {f.tipo_rotulo.toLowerCase()}{f.socios_em_comum != null ? ` (${n(f.socios_em_comum)} sócio${f.socios_em_comum === 1 ? '' : 's'})` : ''}</span></li>)}</ul>
          {r.fora_do_grupo.total > r.fora_do_grupo.itens.length && <p className="mt-1 text-xs text-gray-500">Mostrando as {n(r.fora_do_grupo.itens.length)} primeiras em ordem alfabética.</p>}
        </details>
      )}
      <p className="text-xs text-gray-500">{r.limites} {r.natureza}.</p>
    </div>
  )
}
