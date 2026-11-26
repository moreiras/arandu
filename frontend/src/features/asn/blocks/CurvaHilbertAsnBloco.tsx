// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { V6_BLOCKS } from '../../../components/hilbert/hilbert'
import { HilbertAs, QUADRO_V4, ladoQuadrante, type CamadaCurva } from '../../../components/hilbert/HilbertAs'
import { cruza, intervaloDe, rotuloQuadranteV6, semCobertura, type Intervalo } from '../../../components/hilbert/prefixosAs'
import { n0, palavra } from '../../../lib/sintese'
import type { ASNDocument } from '../../../types/api'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

type Familia = 'v4' | 'v6'
type IdCamada = 'rir' | 'global' | 'ptt'

/** Mesmas cores das camadas dos mapas nacionais (Registro.br, tabela global, PTT). */
const COR: Record<IdCamada, string> = { rir: '#3b82f6', global: '#10b981', ptt: '#8b5cf6' }
const ordem: IdCamada[] = ['rir', 'global', 'ptt']
const MAX_LISTA = 200
const MAX_QUADRANTES = 80

interface Item { prefixo: string; camadas: IdCamada[]; iv: Intervalo | null }

/** Prefixos do AS por camada; "só tabela global" exclui o que está dentro de um prefixo alocado pelo Registro.br. */
function prefixosPorCamada(doc: ASNDocument, fam: Familia, ptt: string | null): Record<IdCamada, string[]> {
  const rir = (fam === 'v4' ? doc.rir_prefixes_v4 : doc.rir_prefixes_v6) ?? []
  const glob = (fam === 'v4' ? doc.global_prefixes_v4 : doc.global_prefixes_v6) ?? []
  return { rir, global: semCobertura(glob, rir), ptt: (ptt && doc.ixp_presence?.[ptt]?.[fam]?.prefixes) || [] }
}

export const temPrefixos = (doc: ASNDocument, fam: Familia) =>
  (fam === 'v4' ? doc.rir_prefixes_v4?.length || doc.global_prefixes_v4?.length : doc.rir_prefixes_v6?.length || doc.global_prefixes_v6?.length) ? true
    : Object.values(doc.ixp_presence ?? {}).some((p) => (p?.[fam]?.prefixes?.length ?? 0) > 0)

function CurvaAsn({ doc, fam }: { doc: ASNDocument; fam: Familia }) {
  const v6 = fam === 'v6'
  const nomeFam = v6 ? 'IPv6' : 'IPv4'
  const ptts = useMemo(
    () => Object.entries(doc.ixp_presence ?? {}).filter(([, p]) => (p?.[fam]?.prefixes?.length ?? 0) > 0)
      .sort(([ca, a], [cb, b]) => (b[fam].prefixes.length - a[fam].prefixes.length) || ca.localeCompare(cb)).map(([c]) => c),   // o PTT com mais prefixos do AS vem primeiro
    [doc.ixp_presence, fam],
  )
  const [ptt, setPtt] = useState<string | null>(ptts[0] ?? null)
  const pttAtual = ptt && ptts.includes(ptt) ? ptt : ptts[0] ?? null
  const [ativas, setAtivas] = useState<Record<IdCamada, boolean>>({ rir: true, global: true, ptt: true })
  const [sel, setSel] = useState<{ bloco: string; quad: number } | null>(null)

  const camadas = useMemo(() => prefixosPorCamada(doc, fam, pttAtual), [doc, fam, pttAtual])
  const rotuloLista: Record<IdCamada, string> = { rir: 'alocado pelo Registro.br', global: 'só na tabela global', ptt: pttAtual ? `visto no PTT ${pttAtual.toUpperCase()}` : 'visto no PTT' }
  const rotulos: Record<IdCamada, string> = {
    rir: 'Alocado pelo Registro.br',
    global: 'Só na tabela global',
    ptt: pttAtual ? `Visto no PTT ${pttAtual.toUpperCase()}` : 'Visto no PTT',
  }

  const itens = useMemo(() => {
    const m = new Map<string, Item>()
    for (const id of ordem) {
      if (!ativas[id]) continue
      for (const p of camadas[id]) {
        const it = m.get(p) ?? { prefixo: p, camadas: [], iv: intervaloDe(p) }
        it.camadas.push(id)
        m.set(p, it)
      }
    }
    return [...m.values()]
  }, [camadas, ativas])

  const lado = ladoQuadrante(v6 ? V6_BLOCKS[0] : QUADRO_V4)
  const porQuad = lado * lado
  const blocos = useMemo(() => {
    const cfgs = v6 ? V6_BLOCKS.filter((b) => itens.some((i) => i.iv?.bloco === b.id)) : [QUADRO_V4]
    return cfgs
  }, [itens, v6])

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

  const rotuloQuad = (bloco: string, quad: number) => {
    if (!v6) return `${quad}.0.0.0/8`
    return rotuloQuadranteV6(V6_BLOCKS.find((b) => b.id === bloco)!, quad)
  }
  const visiveis = useMemo(
    () => (sel ? itens.filter((i) => i.iv && i.iv.bloco === sel.bloco && cruza(i.iv, sel.quad * porQuad, (sel.quad + 1) * porQuad)) : itens),
    [itens, sel, porQuad],
  )
  const ordenados = useMemo(() => [...visiveis].sort((a, b) => (a.iv?.bloco ?? '').localeCompare(b.iv?.bloco ?? '') || (a.iv?.ini ?? 0) - (b.iv?.ini ?? 0) || a.prefixo.localeCompare(b.prefixo)), [visiveis])
  const foraDosBlocos = itens.filter((i) => !i.iv).length
  const nNoBloco = (id: string) => itens.filter((i) => i.iv?.bloco === id).length

  const faixasDe = (bloco: string): CamadaCurva[] =>
    ordem.filter((id) => ativas[id]).map((id) => ({
      id, cor: COR[id],
      faixas: camadas[id].map(intervaloDe).filter((iv): iv is Intervalo => !!iv && iv.bloco === bloco),
    }))

  const nCam = (id: IdCamada) => camadas[id].length
  const resumo = `${n0(itens.length)} ${palavra(itens.length, 'prefixo', 'prefixos')} ${nomeFam} nas camadas ligadas, em ${n0(quadrantes.length)} ${palavra(quadrantes.length, 'quadrante', 'quadrantes')} ${v6 ? '/20' : '/8'}`
    + (v6 && blocos.length ? `, em ${n0(blocos.length)} ${palavra(blocos.length, 'bloco de RIR', 'blocos de RIR')}` : '') + '.'
  const mostrados = ordenados.slice(0, MAX_LISTA)

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        {ordem.map((id) => {
          if (id === 'ptt' && ptts.length === 0) return null
          const n = nCam(id)
          const lig = ativas[id]
          return (
            <button key={id} type="button" aria-pressed={lig} disabled={n === 0}
              onClick={() => { setAtivas((a) => ({ ...a, [id]: !a[id] })); setSel(null) }}
              className={`inline-flex items-center gap-1.5 min-h-[28px] text-xs px-2.5 py-1 rounded-full border focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700 disabled:opacity-50 ${lig ? 'bg-gray-100 border-gray-500 text-gray-900 font-medium' : 'bg-white border-gray-300 text-gray-600'}`}>
              <span aria-hidden="true" className="inline-block w-3 h-3 rounded-sm border border-white shadow-sm" style={{ backgroundColor: COR[id] }} />
              {rotulos[id]} ({n0(n)})
            </button>
          )
        })}
        {ptts.length > 1 && (
          <label className="text-xs text-gray-600 flex items-center gap-1.5">
            PTT
            <select value={pttAtual ?? ''} onChange={(e) => { setPtt(e.target.value); setSel(null) }} className="min-h-[28px] border border-gray-300 rounded px-1.5 text-xs bg-white text-gray-800">
              {ptts.map((c) => <option key={c} value={c}>{c.toUpperCase()}</option>)}
            </select>
          </label>
        )}
      </div>

      <p className="text-xs text-gray-600 mb-2" data-testid={`resumo-curva-${fam}`}>{resumo}{foraDosBlocos > 0 && ` ${n0(foraDosBlocos)} ${palavra(foraDosBlocos, 'prefixo fica', 'prefixos ficam')} fora dos blocos de RIR desenhados e só ${palavra(foraDosBlocos, 'aparece', 'aparecem')} na lista.`}</p>

      {itens.length === 0 ? (
        <p className="text-sm text-gray-500">Nenhuma camada ligada com prefixos {nomeFam}.</p>
      ) : (
        <div className="flex flex-wrap gap-4 items-start">
          {blocos.map((cfg) => (
            <figure key={cfg.id} className="m-0 flex-1 min-w-[220px]" style={{ maxWidth: 360 }}>
              <HilbertAs
                config={cfg}
                camadas={faixasDe(cfg.id)}
                selecionado={sel && sel.bloco === cfg.id ? sel.quad : null}
                onSelecionar={(q) => setSel(q == null || !quadrantes.some((x) => x.bloco === cfg.id && x.quad === q) ? null : { bloco: cfg.id, quad: q })}
                rotulo={`Curva de Hilbert ${nomeFam} do AS${doc.asn}${v6 ? `, bloco ${cfg.label} (${cfg.rir})` : ', grade de /16 com /8 numerados'}: ${n0(nNoBloco(cfg.id))} ${palavra(nNoBloco(cfg.id), 'prefixo', 'prefixos')}. A lista de prefixos abaixo traz o mesmo conteúdo em texto.`}
              />
              <figcaption className="text-xs text-gray-500 mt-1">{v6 ? `${cfg.label} (${cfg.rir}), uma célula por /32` : 'Uma célula por /16; os números são os /8'}</figcaption>
            </figure>
          ))}
        </div>
      )}

      {quadrantes.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-gray-500 mb-1">Filtrar a lista por quadrante {v6 ? '/20' : '/8'} (ou clique no quadro):</p>
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
            Prefixos {nomeFam}{sel ? ` em ${rotuloQuad(sel.bloco, sel.quad)}` : ''} ({n0(visiveis.length)})
            {sel && <button type="button" onClick={() => setSel(null)} className="ml-2 min-h-[24px] text-xs font-normal text-primario-700 underline">limpar filtro</button>}
          </h3>
          <ul className="bg-gray-50 rounded border border-gray-200 p-3 max-h-48 overflow-y-auto font-mono text-xs space-y-0.5" aria-label={`Prefixos ${nomeFam} do AS${doc.asn}`}>
            {mostrados.map((i) => (
              <li key={i.prefixo} className="flex flex-wrap gap-x-2">
                <span className="text-gray-900">{i.prefixo}</span>
                <span className="font-sans text-gray-500">
                  {i.camadas.map((c, k) => (
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

export function HilbertIpv6Bloco({ dados }: BlocoProps<AsnCtx>) { return <CurvaAsn doc={dados.doc} fam="v6" /> }
export function HilbertIpv4Bloco({ dados }: BlocoProps<AsnCtx>) { return <CurvaAsn doc={dados.doc} fam="v4" /> }
