// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, type ComponentType, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BarraDeAbas } from '../entidade/EntityPage'
import type { AbaDef } from '../entidade/registry'
import { useActiveDate } from '../../hooks/useSnapshot'

export interface AbaPanorama extends AbaDef {
  /** O conteúdo da aba. Só é montado quando a aba está aberta, então o que ele busca só é buscado ao abrir. */
  Conteudo: ComponentType
}

/**
 * Página de panorama: um tema com abas por lente (estado em `?aba=`, como as páginas de entidade) e carga por aba. Reúne o conteúdo de Visão geral e
 * Estatísticas (que viraram aliases), agrupado por tema.
 */
export function PaginaPanorama({ titulo, descricao, abas, rodape, aliases = {} }: {
  titulo: string; descricao: string; abas: AbaPanorama[]; rodape?: ReactNode
  /** Abas que mudaram de nome ou foram fundidas: `?aba=antiga` abre a nova e a URL é reescrita (regra 8 do AGENTS.md: nada some sem alias). */
  aliases?: Record<string, string>
}) {
  const [params, setParams] = useSearchParams()
  const date = useActiveDate()
  const pedida = params.get('aba')
  const alvo = pedida != null && aliases[pedida] != null ? aliases[pedida] : pedida
  const ativa = abas.find((a) => a.id === alvo) ?? abas[0]
  useEffect(() => {
    if (pedida == null || aliases[pedida] == null) return
    setParams((anterior) => {
      const novo = new URLSearchParams(anterior)
      if (ativa.id === abas[0].id) novo.delete('aba'); else novo.set('aba', ativa.id)
      return novo
    }, { replace: true })
  }, [pedida, aliases, ativa.id, abas, setParams])
  const abrir = (id: string) => setParams((anterior) => {
    const novo = new URLSearchParams(anterior)
    if (id === abas[0].id) novo.delete('aba'); else novo.set('aba', id)
    return novo
  })
  return (
    <div className="space-y-5" data-testid="panorama">
      <div>
        <h1 className="text-titulo-1 text-gray-900">{titulo}</h1>
        <p className="mt-1 text-sm text-gray-500 max-w-3xl">{descricao}{date ? <> Snapshot <span className="font-mono">{date}</span>.</> : null}</p>
      </div>
      <BarraDeAbas abas={abas} ativa={ativa.id} aoEscolher={abrir} />
      <div role="tabpanel" id={`painel-${ativa.id}`} aria-labelledby={`aba-${ativa.id}`} tabIndex={-1} className="space-y-8">
        <p className="text-sm text-gray-500">{ativa.descricao}</p>
        <ativa.Conteudo />
      </div>
      {rodape}
    </div>
  )
}
