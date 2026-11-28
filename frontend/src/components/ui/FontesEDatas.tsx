// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { createContext, useContext, useEffect, useId, useMemo, useState, type ReactNode } from 'react'
import { formatarReferencia, type Selo } from '../entidade/proveniencia'
import { ComoLer } from './ComoLer'
import { SeloMarca } from './SeloMarca'

/** Uma fonte de um número ou de uma frase: o que o leitor consulta no bloco recolhido da seção. */
export interface ItemFonte { selo?: Selo; fonte?: string; dataRef?: string | null }

type Registro = { definir: (chave: string, itens: ItemFonte[]) => void; remover: (chave: string) => void }
const RegistroCtx = createContext<Registro | null>(null)
const RecolhidaCtx = createContext(false)

/**
 * Modo de apresentação do PT-30: dentro dele, a proveniência dos blocos (`ProvenienciaCompacta`) mostra só "Fonte e data" e o resto
 * abre com um clique. As páginas do piloto (Home, AS e operadora) o ligam; as demais seguem como antes até a replicação.
 */
export function ApresentacaoRecolhida({ children }: { children: ReactNode }) {
  return <RecolhidaCtx.Provider value>{children}</RecolhidaCtx.Provider>
}
export const useApresentacaoRecolhida = () => useContext(RecolhidaCtx)

/** Há um `GrupoFontes` acima? Os `Kpi` dentro dele mostram só o selo e entregam fonte e data ao bloco recolhido da seção. */
export const useEmGrupoFontes = () => useContext(RegistroCtx) !== null

/** Entrega ao `GrupoFontes` mais próximo as fontes de um cartão ou de uma frase; sem grupo, não faz nada. */
export function useRegistrarFontes(itens: ItemFonte[]) {
  const reg = useContext(RegistroCtx)
  const chave = useId()
  const assinatura = JSON.stringify(itens)
  useEffect(() => { reg?.definir(chave, JSON.parse(assinatura) as ItemFonte[]) }, [reg, chave, assinatura])
  useEffect(() => () => reg?.remover(chave), [reg, chave])
}

const textoItem = (i: ItemFonte) => [i.selo ?? '', i.fonte ?? '', i.dataRef ?? ''].join('|')

/** Agrega e deduplica (selo, fonte e data) mantendo a ordem em que aparecem. */
export function deduplicar(itens: ItemFonte[]): ItemFonte[] {
  const vistos = new Set<string>()
  return itens.filter((i) => {
    if (!i.fonte && !i.dataRef) return false
    const k = textoItem(i)
    if (vistos.has(k)) return false
    vistos.add(k)
    return true
  })
}

/** Data na lista: dia ou mês, sem o horário de um carimbo ISO. */
function dataVisivel(v: string): string {
  const m = /^(\d{4}-\d{2}(?:-\d{2})?)(?:$|T)/.exec(v)
  return formatarReferencia(m ? m[1] : v)
}

export const TITULO_FONTES = 'Fontes e datas'
export const TITULO_COMO_LER_E_FONTES = 'Como ler e de onde vêm estes números'

/**
 * Bloco recolhido único de uma seção: o "Como ler" (se houver) em cima e, embaixo, uma lista sem repetição com o selo, a fonte e a
 * data de referência de cada cartão ou frase. Tem a aparência do `ComoLer`, para todos os recolhidos do site terem um formato só.
 * O conteúdo fica no DOM (`<details>`), então leitor de tela e busca na página o alcançam.
 */
export function FontesEDatas({ itens, comoLer, titulo, snapshot, className = '' }: { itens: ItemFonte[]; comoLer?: ReactNode; titulo?: string; snapshot?: string | null; className?: string }) {
  const temFontes = deduplicar(itens).length > 0
  if (!temFontes && !comoLer) return null
  return (
    <ComoLer testId="fontes-e-datas" className={className} titulo={titulo ?? (comoLer ? TITULO_COMO_LER_E_FONTES : TITULO_FONTES)}>
      {comoLer && <div className="space-y-2" data-testid="como-ler-texto">{comoLer}</div>}
      {temFontes && (
        <div className={comoLer ? 'border-t border-gray-200 pt-2' : undefined}>
          <ListaFontes itens={itens} snapshot={snapshot} />
        </div>
      )}
    </ComoLer>
  )
}

/** A lista de fontes sem o recolhido: selo, fonte e data de referência de cada item, sem repetição, e o snapshot. */
export function ListaFontes({ itens, snapshot, className = '' }: { itens: ItemFonte[]; snapshot?: string | null; className?: string }) {
  const lista = deduplicar(itens)
  if (lista.length === 0) return null
  return (
    <ul className={`space-y-1 text-xs text-gray-700 ${className}`} data-testid="lista-fontes">
      {lista.map((i) => (
        <li key={textoItem(i)} className="flex flex-wrap items-center gap-x-2 gap-y-0.5" data-fonte-item>
          {i.selo && <SeloMarca selo={i.selo} legivel />}
          {i.fonte && <span>{i.fonte}</span>}
          {i.dataRef && <span className="text-gray-600">referência: {dataVisivel(i.dataRef)}</span>}
        </li>
      ))}
      {snapshot && <li className="text-gray-600">Snapshot de {formatarReferencia(snapshot)}.</li>}
    </ul>
  )
}

/**
 * Seção cujos cartões e frases entregam fonte e data a um único bloco recolhido, colocado depois do conteúdo. `comoLer` entra no
 * mesmo bloco, acima da lista de fontes.
 * Os `Kpi` e o `ResumoEmTexto` dentro dela mostram só o selo (cartão) ou nada (frase).
 */
export function GrupoFontes({ children, comoLer, titulo, snapshot, className = '' }: { children: ReactNode; comoLer?: ReactNode; titulo?: string; snapshot?: string | null; className?: string }) {
  const [mapa, setMapa] = useState<Map<string, ItemFonte[]>>(() => new Map())
  const registro = useMemo<Registro>(() => ({
    definir: (k, itens) => setMapa((m) => new Map(m).set(k, itens)),
    remover: (k) => setMapa((m) => { if (!m.has(k)) return m; const n = new Map(m); n.delete(k); return n }),
  }), [])
  return (
    <RegistroCtx.Provider value={registro}>
      {children}
      <FontesEDatas itens={[...mapa.values()].flat()} comoLer={comoLer} titulo={titulo} snapshot={snapshot} className={className} />
    </RegistroCtx.Provider>
  )
}
