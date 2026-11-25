// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../components/entidade/AcoesEntidade'
import { Link, Navigate, useLocation, useParams } from 'react-router-dom'
import { EntityHeader } from '../components/entidade'
import { Migalhas } from '../components/layout/Migalhas'
import { EntityPage } from '../features/entidade/EntityPage'
import { useFontes, useGrupoDetalhe } from '../hooks/entidades'
import { AccessPanel } from '../components/AccessPanel'
import { AccessError } from '../services/api'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'
import type { GrupoCtx } from '../features/grupo/contexto'
import '../features/grupo'

const ROTULO: Record<string, string> = { total: 'correspondência total', misto: 'misto', parcial: 'correspondência parcial', individual: 'empresa individual' }

/**
 * `/grupo/:id` — o grupo econômico como entidade: composição das empresas (CNPJs, serviços, ASNs), mercado e rede consolidados e as somas de crédito
 * público, sanções e contratos. **Só estrutura entre empresas (PJ):** não há sócio pessoa física, nome de sócio nem CPF na página nem na API.
 */
export function GrupoPage() {
  const { id } = useParams<{ id: string }>()
  const { search } = useLocation()
  const { fontes } = useFontes()
  const q = useGrupoDetalhe(id)
  if (q.isLoading) return <div className="text-sm text-gray-400" role="status">Carregando…</div>
  const g = q.data
  // 401/403 da política não é "grupo inexistente": mostra o painel de login (o <P> da rota cobre a carga inicial)
  if (q.error instanceof AccessError && q.error.kind !== 'taxa') return <AccessPanel reason={q.error.kind === 'limit' ? 'esgotado' : 'geral'} />
  // 429 e falha de rede também não são "grupo inexistente"
  if (q.isError && ehErroDeAcessoOuFalha(q.error)) return <EstadoDados variante="pagina" erro={q.error} oQue="o grupo" aoTentarDeNovo={() => void q.refetch()} />
  if (!g) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Grupo não encontrado</h1>
        <p className="text-sm text-gray-500">Não há um grupo com esse identificador neste snapshot.</p>
        <Link to="/grupos" className="text-sm text-primario-600 hover:underline mt-3 inline-block">← Voltar para os grupos de empresas</Link>
      </div>
    )
  }
  // link antigo (o id era a raiz da union-find e mudava entre snapshots): a API devolve o grupo com o id estável e a página vai para ele (GRUPO-E14)
  if (g.redirecionado_de && g.grupo_id !== id) return <Navigate to={`/grupo/${encodeURIComponent(g.grupo_id)}${search}`} replace />
  const nome = g.nome || g.cnpjs[0]?.empresa || g.grupo_id
  const ctx: GrupoCtx = { grupo: g }
  return (
    <div className="space-y-5">
      <EntityHeader
        trilha={<Migalhas grupo="mercado" itens={[{ rotulo: 'Grupos', to: '/grupos' }, { rotulo: nome }]} />}
        nome={g.tamanho > 1 ? `Grupo de ${nome}` : nome}
        ladoDoNome={<span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">{g.empresas} {g.empresas === 1 ? 'empresa' : 'empresas'} · {ROTULO[g.classificacao]}</span>}
        snapshot={g.snapshot_date}
        acoes={<AcoesEntidade tipo="grupo" id={g.grupo_id} />}
      >
        {g.nome_regra_texto && (
          <p className="text-xs text-gray-500 mt-1" data-testid="grupo-nome-regra">
            Nome do grupo: {g.nome_regra_texto}. É um rótulo de navegação do conjunto inferido, não indica quem controla quem. Identificador estável: {g.grupo_id}.
          </p>
        )}
      </EntityHeader>
      <EntityPage entidade="grupo" rotulo={g.tamanho > 1 ? `Grupo de ${nome}` : nome} dados={ctx} snapshot={g.snapshot_date} fontes={fontes} espacamento="space-y-5" />
    </div>
  )
}
