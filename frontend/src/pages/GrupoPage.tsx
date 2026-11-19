// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../components/entidade/AcoesEntidade'
import { Link, useParams } from 'react-router-dom'
import { EntityHeader } from '../components/entidade'
import { Migalhas } from '../components/layout/Migalhas'
import { EntityPage } from '../features/entidade/EntityPage'
import { useFontes, useGrupoDetalhe } from '../hooks/entidades'
import type { GrupoCtx } from '../features/grupo/contexto'
import '../features/grupo'

const ROTULO: Record<string, string> = { total: 'correspondência total', misto: 'misto', parcial: 'correspondência parcial', individual: 'empresa individual' }

/**
 * `/grupo/:id` — o grupo econômico como entidade: composição das empresas (CNPJs, serviços, ASNs), mercado e rede consolidados e as somas de crédito
 * público, sanções e contratos. **Só estrutura entre empresas (PJ):** não há sócio pessoa física, nome de sócio nem CPF na página nem na API.
 */
export function GrupoPage() {
  const { id } = useParams<{ id: string }>()
  const { fontes } = useFontes()
  const q = useGrupoDetalhe(id)
  if (q.isLoading) return <div className="text-sm text-gray-400" role="status">Carregando…</div>
  const g = q.data
  if (!g) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Grupo não encontrado</h1>
        <p className="text-sm text-gray-500">Não há um grupo com esse identificador neste snapshot.</p>
        <Link to="/grupos" className="text-sm text-primario-600 hover:underline mt-3 inline-block">← Voltar para os grupos de empresas</Link>
      </div>
    )
  }
  const nome = g.cnpjs[0]?.empresa || g.grupo_id
  const ctx: GrupoCtx = { grupo: g }
  return (
    <div className="space-y-5">
      <EntityHeader
        trilha={<Migalhas grupo="mercado" itens={[{ rotulo: 'Grupos', to: '/grupos' }, { rotulo: nome }]} />}
        nome={g.tamanho > 1 ? `Grupo de ${nome}` : nome}
        ladoDoNome={<span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">{g.empresas} {g.empresas === 1 ? 'empresa' : 'empresas'} · {ROTULO[g.classificacao]}</span>}
        snapshot={g.snapshot_date}
        acoes={<AcoesEntidade tipo="grupo" id={g.grupo_id} />}
      />
      <EntityPage entidade="grupo" rotulo={g.tamanho > 1 ? `Grupo de ${nome}` : nome} dados={ctx} snapshot={g.snapshot_date} fontes={fontes} espacamento="space-y-5" />
    </div>
  )
}
