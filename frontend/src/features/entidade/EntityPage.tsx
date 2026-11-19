// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useRef } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { EmptyState, Section } from '../../components/entidade'
import type { FonteEntrada } from '../../components/entidade'
import { abasDe, blocosDe, type AbaDef, type BlocoDef, type Entidade } from './registry'
import { SumarioBlocos } from './SumarioBlocos'

interface Props {
  entidade: Entidade
  dados: unknown
  snapshot: string | null
  fontes?: FonteEntrada[] | null
  /** Como a entidade se chama na citação ("AS15169 · Google LLC"); sem ele os blocos não oferecem "Citar este dado". */
  rotulo?: string
  /** Classe de espaçamento vertical entre blocos (a página de ASN usa `space-y-8`, como antes da migração). */
  espacamento?: string
}

/**
 * Renderiza os blocos registrados de uma entidade, cada um numa `Section` com proveniência. Entidade com abas registradas (`registrarAbas`) mostra
 * **uma lente por vez**, com o estado em `?aba=` (link compartilhável; o botão Voltar desfaz a troca) e só monta os blocos da aba ativa, então o que
 * cada bloco busca por conta própria só é buscado quando a aba abre. `?versao=1` mostra a página sem abas, com todos os blocos.
 */
export function EntityPage(props: Props) {
  const temAbas = abasDe(props.entidade).length > 0
  return temAbas ? <PaginaComAbas {...props} /> : <ListaDeBlocos {...props} blocos={aplicaveis(props.entidade, props.dados)} />
}

function aplicaveis(entidade: Entidade, dados: unknown): BlocoDef[] {
  return blocosDe(entidade).filter((b) => !b.aplicavel || b.aplicavel(dados))
}

function ListaDeBlocos({ blocos, dados, snapshot, fontes, rotulo, espacamento = 'space-y-4' }: Props & { blocos: BlocoDef[] }) {
  return (
    <div className={espacamento}>
      <SumarioBlocos itens={blocos.map((b) => ({ id: `bloco-${b.id}`, titulo: b.titulo }))} />
      {blocos.map((b) => (
        <Section key={b.id} id={`bloco-${b.id}`} titulo={b.titulo} subtitulo={b.subtitulo}
          proveniencia={{ fontes: b.fontes, selo: b.selo, nota: b.nota }} fontes={fontes} snapshot={snapshot}
          semTitulo={b.semTitulo} plana={b.plana} comoLer={b.comoLer} recolhido={b.recolhido}
          citacao={rotulo ? { entidade: rotulo, bloco: b.titulo, blocoId: b.id } : undefined}>
          {b.vazio?.(dados) ? <EmptyState mensagem={b.mensagemVazio} snapshot={snapshot} /> : <b.Componente dados={dados} snapshot={snapshot} />}
        </Section>
      ))}
    </div>
  )
}

/** A aba de um bloco; bloco sem `aba` cai na primeira (o teste do registro exige `aba` em toda entidade com abas). */
const abaDoBloco = (b: BlocoDef, abas: AbaDef[]) => (b.aba && abas.some((a) => a.id === b.aba) ? b.aba : abas[0].id)

/** Aba ativa: a do `?aba=` se existir e tiver blocos; senão a do bloco de `#bloco-…` na URL; senão a primeira com blocos. */
export function abaAtiva(abas: AbaDef[], porAba: Map<string, BlocoDef[]>, pedida: string | null, hash: string): string {
  const visiveis = abas.filter((a) => (porAba.get(a.id)?.length ?? 0) > 0)
  if (pedida && visiveis.some((a) => a.id === pedida)) return pedida
  const alvo = hash.startsWith('#bloco-') ? hash.slice(7) : null
  const achada = alvo ? visiveis.find((a) => porAba.get(a.id)!.some((b) => b.id === alvo)) : undefined
  return (achada ?? visiveis[0] ?? abas[0]).id
}

function PaginaComAbas(props: Props) {
  const { entidade, dados } = props
  const [params, setParams] = useSearchParams()
  const { hash } = useLocation()
  const todos = aplicaveis(entidade, dados)
  if (params.get('versao') === '1') return <ListaDeBlocos {...props} blocos={todos} />

  const abas = abasDe(entidade)
  const porAba = new Map<string, BlocoDef[]>(abas.map((a) => [a.id, []]))
  for (const b of todos) porAba.get(abaDoBloco(b, abas))!.push(b)
  const visiveis = abas.filter((a) => porAba.get(a.id)!.length > 0)
  const ativa = abaAtiva(abas, porAba, params.get('aba'), hash)
  const aba = abas.find((a) => a.id === ativa)!

  const abrir = (id: string) => setParams((anterior) => {
    const novo = new URLSearchParams(anterior)
    if (id === visiveis[0].id) novo.delete('aba'); else novo.set('aba', id)
    return novo
  })

  return (
    <div className="space-y-4">
      {visiveis.length > 1 && <BarraDeAbas abas={visiveis} ativa={ativa} aoEscolher={abrir} />}
      <div role="tabpanel" id={`painel-${ativa}`} aria-labelledby={`aba-${ativa}`} tabIndex={-1}>
        {visiveis.length > 1 && <p className="mb-3 text-sm text-gray-500">{aba.descricao}</p>}
        <ListaDeBlocos {...props} blocos={porAba.get(ativa)!} />
      </div>
    </div>
  )
}

/** Abas (WAI-ARIA): ← → Home End movem o foco e ativam; só a aba ativa entra na ordem de Tab. Rola dentro do próprio contêiner no celular. */
export function BarraDeAbas({ abas, ativa, aoEscolher, rotulo = 'Lentes da página' }: { abas: ReadonlyArray<Pick<AbaDef, 'id' | 'rotulo'> & { descricao?: string }>; ativa: string; aoEscolher: (id: string) => void; rotulo?: string }) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})
  function aoTeclar(e: React.KeyboardEvent, i: number) {
    const mover = { ArrowRight: (i + 1) % abas.length, ArrowLeft: (i - 1 + abas.length) % abas.length, Home: 0, End: abas.length - 1 }[e.key]
    if (mover === undefined) return
    e.preventDefault()
    const alvo = abas[mover].id
    aoEscolher(alvo)
    refs.current[alvo]?.focus()
  }
  return (
    <div role="tablist" aria-label={rotulo} className="flex gap-1 overflow-x-auto border-b border-gray-200 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {abas.map((a, i) => (
        <button key={a.id} ref={(el) => { refs.current[a.id] = el }} type="button" role="tab" id={`aba-${a.id}`} aria-selected={a.id === ativa} aria-controls={a.id === ativa ? `painel-${a.id}` : undefined}
          tabIndex={a.id === ativa ? 0 : -1} title={a.descricao} onClick={() => aoEscolher(a.id)} onKeyDown={(e) => aoTeclar(e, i)}
          className={`flex-shrink-0 whitespace-nowrap px-3 py-2 text-sm -mb-px border-b-2 ${a.id === ativa ? 'border-primario-600 text-primario-700 font-medium' : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'}`}>
          {a.rotulo}
        </button>
      ))}
    </div>
  )
}
