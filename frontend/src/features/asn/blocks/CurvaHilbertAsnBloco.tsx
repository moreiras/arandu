// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { HilbertMap16, type LayerMeta } from '../../../components/hilbert/HilbertMap16'
import { HilbertMapV6 } from '../../../components/hilbert/HilbertMapV6'
import { LEGENDA_MARCADOR } from '../../../components/hilbert/isoladas'
import { COR_ALOCADO_VISIVEL, V6_BLOCKS, type V6BlockConfig } from '../../../components/hilbert/hilbert'
import { celulasV6, cruza, densidadeV4, intervaloDe, interseccao, rotuloQuadranteV6, type Intervalo } from '../../../components/hilbert/prefixosAs'
import { corLegivel } from '../../../lib/contraste'
import { n0, palavra } from '../../../lib/sintese'
import type { ASNDocument } from '../../../types/api'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

type Familia = 'v4' | 'v6'
type IdCamada = 'rir' | 'global' | 'visivel' | 'ptt'
type IdOrigem = 'rir' | 'global' | 'ptt'

/** Cores das camadas, as dos mapas nacionais (Registro.br, tabela global, PTT, alocado e visível em ciano, sem vermelho). */
const COR: Record<IdCamada, string> = { rir: '#3b82f6', global: '#10b981', visivel: COR_ALOCADO_VISIVEL, ptt: '#8b5cf6' }
const ORDEM: IdCamada[] = ['rir', 'global', 'visivel', 'ptt']
const ORIGENS: IdOrigem[] = ['rir', 'global', 'ptt']
const MAX_LISTA = 200
const MAX_QUADRANTES = 80
/** Células de /16 por quadrante /8 (IPv4) e de /32 por quadrante /20 (IPv6): o que as chaves de filtro agrupam. */
const CELULAS_POR_QUADRANTE: Record<Familia, number> = { v4: 256, v6: 4096 }

interface Item { prefixo: string; origens: IdOrigem[]; iv: Intervalo | null }

export const temPrefixos = (doc: ASNDocument, fam: Familia) =>
  (fam === 'v4' ? doc.rir_prefixes_v4?.length || doc.global_prefixes_v4?.length : doc.rir_prefixes_v6?.length || doc.global_prefixes_v6?.length) ? true
    : Object.values(doc.ixp_presence ?? {}).some((p) => (p?.[fam]?.prefixes?.length ?? 0) > 0)

/** Prefixos do AS por camada; `ptt` vazio reúne todos os PTTs. */
function prefixosPorCamada(doc: ASNDocument, fam: Familia, ptt: string): Record<IdCamada, string[]> {
  const rir = (fam === 'v4' ? doc.rir_prefixes_v4 : doc.rir_prefixes_v6) ?? []
  const global = (fam === 'v4' ? doc.global_prefixes_v4 : doc.global_prefixes_v6) ?? []
  const pres = doc.ixp_presence ?? {}
  const codigos = ptt ? [ptt] : Object.keys(pres)
  const noPtt = [...new Set(codigos.flatMap((c) => pres[c]?.[fam]?.prefixes ?? []))]
  return { rir, global, visivel: interseccao(rir, global), ptt: noPtt }
}

function CurvaAsn({ doc, fam }: { doc: ASNDocument; fam: Familia }) {
  const v6 = fam === 'v6'
  const nomeFam = v6 ? 'IPv6' : 'IPv4'
  const ptts = useMemo(
    () => Object.entries(doc.ixp_presence ?? {}).filter(([, p]) => (p?.[fam]?.prefixes?.length ?? 0) > 0)
      .sort(([ca, a], [cb, b]) => (b[fam].prefixes.length - a[fam].prefixes.length) || ca.localeCompare(cb)).map(([c]) => c),
    [doc.ixp_presence, fam],
  )
  const [ptt, setPtt] = useState('')
  const pttAtual = ptts.includes(ptt) ? ptt : ''
  const [sel, setSel] = useState<{ bloco: string; quad: number } | null>(null)

  const camadas = useMemo(() => prefixosPorCamada(doc, fam, pttAtual), [doc, fam, pttAtual])
  const presentes = useMemo(() => ORDEM.filter((id) => camadas[id].length > 0), [camadas])
  const [camadaEstado, setCamada] = useState<IdCamada | null>(null)
  const camada: IdCamada | null = camadaEstado && presentes.includes(camadaEstado) ? camadaEstado : presentes[0] ?? null

  const rotuloPtt = pttAtual ? `PTT ${pttAtual.toUpperCase()}` : 'PTT do IX.br'
  const meta = useMemo(() => {
    const t = `${nomeFam} do AS${doc.asn}`
    const nomes: Record<IdCamada, Pick<LayerMeta, 'label' | 'description' | 'legend'>> = {
      rir: {
        label: 'Alocado pelo Registro.br', description: `Prefixos ${t} alocados pelo Registro.br`,
        legend: `Prefixos ${t} alocados pelo Registro.br. É o espaço delegado ao AS, esteja ou não anunciado na Internet.`,
      },
      global: {
        label: 'Visto na tabela global', description: `Prefixos ${t} vistos na tabela de roteamento global`,
        legend: `Prefixos ${t} observados na tabela de roteamento global, alocados pelo Registro.br ou não.`,
      },
      visivel: {
        label: 'Alocado e visível', description: 'Alocado pelo Registro.br e visto na tabela global',
        legend: `Prefixos ${t} que são ao mesmo tempo alocados pelo Registro.br e vistos na tabela global (um contido no outro, com precisão de prefixo): o espaço delegado que está anunciado.`,
      },
      ptt: {
        label: `Visto no ${rotuloPtt}`, description: `Prefixos ${t} vistos ${pttAtual ? `no ${rotuloPtt}` : 'em qualquer PTT do IX.br'}`,
        legend: `Prefixos ${t} que outros participantes veem ${pttAtual ? `no ${rotuloPtt}` : 'em algum PTT do IX.br (todos os PTTs)'}, isto é, o espaço do AS que aparece nas interligações do IX.br.`,
      },
    }
    return Object.fromEntries(presentes.map((id) => [id, { ...nomes[id], color: COR[id] }])) as Record<string, LayerMeta>
  }, [presentes, nomeFam, doc.asn, pttAtual, rotuloPtt])

  const dadosV4 = useMemo(() => (v6 ? null : Object.fromEntries(presentes.map((id) => [id, densidadeV4(camadas[id])]))), [v6, presentes, camadas])
  const dadosV6 = useMemo(() => {
    if (!v6) return null
    const porCamada = Object.fromEntries(presentes.map((id) => [id, celulasV6(camadas[id])]))
    const blocos: Record<string, Record<string, number[]>> = {}
    for (const id of presentes) {
      for (const b of Object.keys(porCamada[id])) {
        blocos[b] ??= Object.fromEntries(presentes.map((i) => [i, [] as number[]]))
        blocos[b][id] = porCamada[id][b]
      }
    }
    return blocos
  }, [v6, presentes, camadas])

  const itens = useMemo<Item[]>(() => {
    if (!camada) return []
    const conj = Object.fromEntries(ORIGENS.map((o) => [o, new Set(camadas[o])])) as Record<IdOrigem, Set<string>>
    return camadas[camada].map((prefixo) => ({ prefixo, origens: ORIGENS.filter((o) => conj[o].has(prefixo)), iv: intervaloDe(prefixo) }))
  }, [camada, camadas])

  const porQuad = CELULAS_POR_QUADRANTE[fam]
  const quadrantes = useMemo(() => {
    const cont = new Map<string, { bloco: string; quad: number; n: number }>()
    for (const it of itens) {
      if (!it.iv) continue
      for (let q = Math.floor(it.iv.ini / porQuad); q <= Math.floor((it.iv.fim - 1) / porQuad); q++) {
        const k = `${it.iv.bloco}|${q}`
        const c = cont.get(k) ?? { bloco: it.iv.bloco, quad: q, n: 0 }
        c.n++
        cont.set(k, c)
      }
    }
    return [...cont.values()].sort((a, b) => b.n - a.n || a.bloco.localeCompare(b.bloco) || a.quad - b.quad)
  }, [itens, porQuad])

  const rotuloQuad = (bloco: string, quad: number) =>
    v6 ? rotuloQuadranteV6(V6_BLOCKS.find((b) => b.id === bloco)!, quad) : `${quad}.0.0.0/8`
  const visiveis = useMemo(
    () => (sel ? itens.filter((i) => i.iv && i.iv.bloco === sel.bloco && cruza(i.iv, sel.quad * porQuad, (sel.quad + 1) * porQuad)) : itens),
    [itens, sel, porQuad],
  )
  const ordenados = useMemo(() => [...visiveis].sort((a, b) => (a.iv?.bloco ?? '').localeCompare(b.iv?.bloco ?? '') || (a.iv?.ini ?? 0) - (b.iv?.ini ?? 0) || a.prefixo.localeCompare(b.prefixo)), [visiveis])
  const foraDosBlocos = itens.filter((i) => !i.iv).length
  const nNoBloco = (id: string) => itens.filter((i) => i.iv?.bloco === id).length
  const nBlocos = v6 ? V6_BLOCKS.filter((b) => nNoBloco(b.id) > 0).length : 0

  const rotuloCamada = camada ? meta[camada].label : ''
  const resumo = camada
    ? `${n0(itens.length)} ${palavra(itens.length, 'prefixo', 'prefixos')} ${nomeFam} na camada "${rotuloCamada}", em ${n0(quadrantes.length)} ${palavra(quadrantes.length, 'quadrante', 'quadrantes')} ${v6 ? '/20' : '/8'}`
      + (v6 && nBlocos ? `, em ${n0(nBlocos)} ${palavra(nBlocos, 'bloco de RIR', 'blocos de RIR')}` : '') + '.'
    : ''
  const mostrados = ordenados.slice(0, MAX_LISTA)
  const rotuloLista: Record<IdOrigem, string> = { rir: 'alocado pelo Registro.br', global: 'visto na tabela global', ptt: pttAtual ? `visto no PTT ${pttAtual.toUpperCase()}` : 'visto em PTT do IX.br' }
  const nomeCanvas = (extra: string, n: number) =>
    `Curva de Hilbert ${nomeFam} do AS${doc.asn}, camada "${rotuloCamada}"${extra}: ${n0(n)} ${palavra(n, 'prefixo', 'prefixos')}. A lista de prefixos abaixo traz o mesmo conteúdo em texto.`
  const trocar = (k: string) => { setCamada(k as IdCamada); setSel(null) }

  return (
    <div>
      {ptts.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <label className="text-xs text-gray-600 flex items-center gap-1.5">
            PTT da camada de PTT
            <select value={pttAtual} onChange={(e) => { setPtt(e.target.value); setSel(null) }} className="min-h-[28px] border border-gray-300 rounded px-1.5 text-xs bg-white text-gray-800">
              <option value="">Todos os PTTs</option>
              {ptts.map((c) => <option key={c} value={c}>{c.toUpperCase()}</option>)}
            </select>
          </label>
        </div>
      )}

      {!camada ? (
        <p className="text-sm text-gray-500">Nenhum prefixo {nomeFam} para desenhar.</p>
      ) : v6 ? (
        <HilbertMapV6
          data={dadosV6}
          blockWidth={260}
          layerMeta={meta}
          camadaInicial={camada}
          onCamada={trocar}
          dualLayers={[]}
          rotuloBloco={(cfg: V6BlockConfig) => nomeCanvas(`, bloco ${cfg.label} (${cfg.rir})`, nNoBloco(cfg.id))}
          rodape={`Os seis blocos de RIR aparecem sempre, como no panorama técnico; só os prefixos do AS são coloridos. Cada célula é um /32; um prefixo menor que o /32 marca o /32 que o contém. Passe o mouse para ver o prefixo. Clique em blocos destacados para ampliar. ${LEGENDA_MARCADOR}`}
        />
      ) : (
        <CurvaV4 dados={dadosV4!} meta={meta} camada={camada} onCamada={trocar} rotulo={nomeCanvas(', grade de /16 com /8 numerados', itens.length)} />
      )}

      {camada && <p className="text-xs text-gray-600 mt-2 mb-2" data-testid={`resumo-curva-${fam}`}>{resumo}{foraDosBlocos > 0 && ` ${n0(foraDosBlocos)} ${palavra(foraDosBlocos, 'prefixo fica', 'prefixos ficam')} fora dos blocos de RIR desenhados e só ${palavra(foraDosBlocos, 'aparece', 'aparecem')} na lista.`}</p>}

      {quadrantes.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-1">Filtrar a lista por quadrante {v6 ? '/20' : '/8'}:</p>
          <div className="flex flex-wrap gap-1.5">
            {quadrantes.slice(0, MAX_QUADRANTES).map((q) => {
              const on = sel?.bloco === q.bloco && sel.quad === q.quad
              return (
                <button key={`${q.bloco}|${q.quad}`} type="button" aria-pressed={on} onClick={() => setSel(on ? null : { bloco: q.bloco, quad: q.quad })}
                  className={`min-h-[28px] min-w-[28px] font-mono text-xs px-2 rounded border focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700 ${on ? 'bg-gray-800 border-gray-800 text-white' : 'bg-white border-gray-300 text-gray-700'}`}>
                  {rotuloQuad(q.bloco, q.quad)} ({n0(q.n)})
                </button>
              )
            })}
          </div>
          {quadrantes.length > MAX_QUADRANTES && <p className="text-xs text-gray-400 mt-1">Mostrando os {MAX_QUADRANTES} quadrantes com mais prefixos de {n0(quadrantes.length)}.</p>}
        </div>
      )}

      {itens.length > 0 && (
        <div className="mt-3">
          <h3 className="text-sm font-semibold text-gray-800 mb-1.5">
            Prefixos {nomeFam} da camada "{rotuloCamada}"{sel ? ` em ${rotuloQuad(sel.bloco, sel.quad)}` : ''} ({n0(visiveis.length)})
            {sel && <button type="button" onClick={() => setSel(null)} className="ml-2 min-h-[24px] text-xs font-normal text-primario-700 underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700">limpar filtro</button>}
          </h3>
          <ul className="bg-gray-50 rounded border border-gray-200 p-3 max-h-48 overflow-y-auto font-mono text-xs space-y-0.5" aria-label={`Prefixos ${nomeFam} do AS${doc.asn}`}>
            {mostrados.map((i) => (
              <li key={i.prefixo} className="flex flex-wrap gap-x-2">
                <span className="text-gray-900">{i.prefixo}</span>
                <span className="font-sans text-gray-500">
                  {i.origens.map((c, k) => (
                    <span key={c}>
                      {k > 0 && ', '}
                      <span aria-hidden="true" className="inline-block w-2 h-2 rounded-sm mr-1" style={{ backgroundColor: COR[c] }} />
                      {rotuloLista[c]}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
          {ordenados.length > MAX_LISTA && <p className="text-xs text-gray-400 mt-1">Mostrando {MAX_LISTA} de {n0(ordenados.length)} prefixos; filtre por quadrante para ver os demais.</p>}
        </div>
      )}
    </div>
  )
}

/** Curva IPv4 do AS: o seletor de camada, a legenda e o mapa do panorama técnico (mesma disposição de `SecaoHilbertV4`). */
function CurvaV4({ dados, meta, camada, onCamada, rotulo }: { dados: Record<string, number[]>; meta: Record<string, LayerMeta>; camada: string; onCamada: (k: string) => void; rotulo: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const [largura, setLargura] = useState(380)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver((e) => setLargura(Math.min(Math.floor(e[0].contentRect.width), 380)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {Object.keys(meta).map((key) => {
          const m = meta[key]
          const active = camada === key
          return (
            <button key={key} type="button" onClick={() => onCamada(key)} title={m.description} aria-pressed={active}
              className={`min-h-[28px] text-xs px-2.5 py-1 rounded-full border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700 ${active ? 'text-white border-transparent' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'}`}
              style={active ? { backgroundColor: corLegivel(m.color), borderColor: corLegivel(m.color) } : undefined}>
              {m.label}
            </button>
          )
        })}
      </div>
      <p className="text-xs text-gray-500 mb-3 leading-relaxed border-l-2 pl-2" style={{ borderColor: meta[camada].color }}>{meta[camada].legend}</p>
      <div ref={ref}>
        <HilbertMap16 data={dados} activeLayer={camada} width={largura} layerMeta={meta} dualLayers={[]} semDetalhe rotuloCanvas={rotulo} />
      </div>
      <p className="text-xs text-gray-400 mt-1.5">Cada célula é um bloco /16; a intensidade cresce com o número de /24 do AS no /16 (todo /16 com dado aparece, mesmo com um só /24), e um prefixo menor que o /24 conta o /24 que o contém. Clique em um bloco /8 destacado para ampliar.</p>
    </div>
  )
}

export function HilbertIpv6Bloco({ dados }: BlocoProps<AsnCtx>) { return <CurvaAsn doc={dados.doc} fam="v6" /> }
export function HilbertIpv4Bloco({ dados }: BlocoProps<AsnCtx>) { return <CurvaAsn doc={dados.doc} fam="v4" /> }
