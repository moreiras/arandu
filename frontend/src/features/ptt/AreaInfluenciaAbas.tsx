// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ComoLer } from '../../components/ui/ComoLer'
import { IXPVoronoiMap } from '../../components/maps/IXPVoronoiMap'
import { useAreaInfluenciaNacional } from '../../hooks/entidades'
import { corPtt, expressaoPrincipal, formatarKm, matizesPorPtt, ROTULO_FAIXA, ROTULO_FAIXA_CURTO, ROTULO_VISAO, type Faixa } from '../../lib/areaInfluencia'
import { palavra } from '../../lib/sintese'
import type { IXPIndexEntry } from '../../types/api'
import type { AreaInfluenciaNacional, VisaoArea } from '../../types/areaInfluencia'

const Coropletico = lazy(() => import('../../components/maps/Coropletico').then((m) => ({ default: m.Coropletico })))
const n = (v: number) => v.toLocaleString('pt-BR')

export type AbaMapa = 'todos' | 'diretos' | 'voronoi'
/** As abas na ordem de exibição; a primeira é a que abre. */
export const ABAS_MAPA: Array<{ id: AbaMapa; rotulo: string }> = [
  { id: 'todos', rotulo: 'Área de influência total' },
  { id: 'diretos', rotulo: 'Só diretamente conectados' },
  { id: 'voronoi', rotulo: 'Áreas geométricas (Voronoi)' },
]
const TONS_LEGENDA: Record<Faixa, string> = { 1: 'hsl(0, 0%, 30%)', 2: 'hsl(0, 0%, 55%)', 3: 'hsl(0, 0%, 80%)' }

/**
 * Bloco do mapa da página /ixps com três abas: a área de influência observada com todos os ASNs que anunciam no PTT, só com os diretamente conectados,
 * e as áreas geométricas (Voronoi, o PTT mais próximo em linha reta). Só a aba aberta monta o mapa. Teclado: setas, Home e End movem o foco e abrem a aba.
 */
export function AreaInfluenciaAbas({ ixps, date }: { ixps: IXPIndexEntry[]; date?: string }) {
  const [aba, setAba] = useState<AbaMapa>('todos')
  const base = useId()
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})

  const aoTecla = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const destino = e.key === 'ArrowRight' ? (i + 1) % ABAS_MAPA.length : e.key === 'ArrowLeft' ? (i + ABAS_MAPA.length - 1) % ABAS_MAPA.length : e.key === 'Home' ? 0 : e.key === 'End' ? ABAS_MAPA.length - 1 : null
    if (destino === null) return
    e.preventDefault()
    const id = ABAS_MAPA[destino].id
    setAba(id)
    refs.current[id]?.focus()
  }

  return (
    <div className="space-y-3" data-testid="mapa-ptts-abas">
      <div role="tablist" aria-label="Mapa das áreas dos PTTs" className="flex flex-wrap gap-1 border-b border-gray-200">
        {ABAS_MAPA.map((a, i) => (
          <button key={a.id} id={`${base}-aba-${a.id}`} ref={(el) => { refs.current[a.id] = el }} type="button" role="tab" aria-selected={aba === a.id} aria-controls={`${base}-painel-${a.id}`}
            tabIndex={aba === a.id ? 0 : -1} onClick={() => setAba(a.id)} onKeyDown={(e) => aoTecla(e, i)}
            className={`-mb-px border-b-2 px-3 py-1.5 text-sm ${aba === a.id ? 'border-primario-600 font-medium text-primario-700' : 'border-transparent text-gray-600 hover:text-gray-900'}`}>
            {a.rotulo}
          </button>
        ))}
      </div>
      {ABAS_MAPA.map((a) => aba === a.id && (
        <div key={a.id} id={`${base}-painel-${a.id}`} role="tabpanel" aria-labelledby={`${base}-aba-${a.id}`} tabIndex={0} className="space-y-2">
          {a.id === 'voronoi'
            ? (
              <>
                <p className="text-xs text-gray-600">PTT mais próximo (distância geográfica) · grade 0,12°</p>
                <IXPVoronoiMap ixps={ixps} date={date} />
              </>
            )
            : <AreaInfluenciaNacionalMapa visao={a.id} />}
        </div>
      ))}
    </div>
  )
}

function AreaInfluenciaNacionalMapa({ visao }: { visao: VisaoArea }) {
  const navigate = useNavigate()
  const q = useAreaInfluenciaNacional(visao)
  if (q.isLoading) return <div className="h-[520px] animate-pulse rounded-lg bg-gray-100" role="status" aria-label="Carregando o mapa" />
  if (q.isError || !q.data) return <p className="text-sm text-gray-600" data-testid="area-nacional-vazia">A área de influência observada não foi calculada para este snapshot.</p>
  return <Mapa d={q.data} navegar={(ibge) => navigate(`/municipio/${ibge}`)} />
}

export function Mapa({ d, navegar }: { d: AreaInfluenciaNacional; navegar: (ibge: string) => void }) {
  const matizes = useMemo(() => matizesPorPtt(Object.fromEntries(Object.entries(d.ptts).map(([c, p]) => [c, { ponto: p.ponto, municipios: p.municipios }]))), [d.ptts])
  const cor = useMemo(() => expressaoPrincipal(d.municipios, matizes), [d.municipios, matizes])
  const pontos = useMemo(() => Object.values(d.ptts).filter((p) => p.ponto).map((p) => ({ lat: p.ponto![0], lon: p.ponto![1] })), [d.ptts])
  const lista = useMemo(() => Object.entries(d.ptts).sort((a, b) => b[1].acessos - a[1].acessos), [d.ptts])
  const mesSici = d.fontes.sici
  return (
    <div className="space-y-3">
      <div className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <Suspense fallback={<div className="h-[520px] animate-pulse rounded-lg bg-gray-100" role="status" aria-label="Carregando o mapa" />}>
          <Coropletico cor={cor} nivel="municipio" altura={520} pontos={pontos}
            descricao={`Mapa dos municípios do Brasil na visão ${ROTULO_VISAO[d.visao].toLowerCase()}. Cada município tem a cor do PTT que recebe mais acessos dele, em tom mais escuro quando está perto desse PTT e mais claro quando está longe. Os números por PTT estão na tabela abaixo.`}
            rotulo={(ibge, nome, uf) => {
              const m = d.municipios[ibge]
              return m ? `${nome}/${uf}: PTT principal ${d.ptts[m[0]]?.nome ?? m[0]}, ${ROTULO_FAIXA_CURTO[m[1] as Faixa]}` : `${nome}/${uf}: sem acessos atribuídos a PTT nesta visão`
            }}
            aoClicar={(codigo, nivel) => { if (nivel === 'municipio') navegar(codigo) }} />
        </Suspense>
        <figure aria-label="Legenda do mapa" className="space-y-2 text-xs text-gray-600" data-testid="legenda-area-nacional">
          <figcaption className="font-medium text-gray-800">Como ler as cores</figcaption>
          <p>O matiz é o do PTT principal do município (o que recebe mais acessos dele). O tom é a faixa do município nesse PTT.</p>
          <ul className="space-y-0.5" aria-label="Tons da faixa">
            {([1, 2, 3] as Faixa[]).map((f) => (
              <li key={f} className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: TONS_LEGENDA[f] }} aria-hidden="true" />{ROTULO_FAIXA[f]}</li>
            ))}
          </ul>
          <ul className="grid grid-cols-1 gap-0.5" aria-label="PTTs e suas cores" data-testid="legenda-ptts">
            {lista.map(([c, p]) => (
              <li key={c} className="flex items-center gap-2">
                <span className="inline-block h-3 w-5 shrink-0 rounded-sm border border-gray-300" style={{ background: corPtt(matizes[c] ?? 0, 2) }} aria-hidden="true" />
                <span>{p.nome}/{p.uf}</span>
              </li>
            ))}
          </ul>
          <p className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-full border-2 border-gray-900 bg-white" aria-hidden="true" />Ponto do PTT (média dos PIX)</p>
        </figure>
      </div>
      <p className="max-w-[80ch] text-sm text-gray-700">
        Inferido dos acessos de banda larga fixa do SICI (mês {mesSici ?? 'de referência'}): cada acesso vai para o PTT mais próximo entre os que a operadora enxerga na visão “{ROTULO_VISAO[d.visao]}”.
        Isto não é cobertura de rede. {d.ptts_com_pix_aproximado.length > 0 && `${n(d.ptts_com_pix_aproximado.length)} ${palavra(d.ptts_com_pix_aproximado.length, 'PTT tem', 'PTTs têm')} PIX sem coordenada no cadastro, posicionado pelo centroide do município.`}
      </p>
      <details className="text-sm text-gray-700" data-testid="tabela-ptts-area">
        <summary className="cursor-pointer select-none text-xs font-medium text-primario-700 hover:text-primario-900">Números por PTT, em tabela ({n(lista.length)})</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full text-sm">
            <caption className="sr-only">Área de influência por PTT na visão {ROTULO_VISAO[d.visao]}</caption>
            <thead className="text-xs text-gray-600"><tr>
              <th scope="col" className="px-2 py-1 text-left">PTT</th>
              <th scope="col" className="px-2 py-1 text-right">Operadoras</th>
              <th scope="col" className="px-2 py-1 text-right">Municípios</th>
              <th scope="col" className="px-2 py-1 text-right">Acessos atribuídos</th>
              <th scope="col" className="px-2 py-1 text-right">P50</th>
              <th scope="col" className="px-2 py-1 text-right">P80</th>
              <th scope="col" className="px-2 py-1 text-right">P90</th>
              <th scope="col" className="px-2 py-1 text-right">Mediana por operadora</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {lista.map(([c, p]) => (
                <tr key={c}>
                  <th scope="row" className="px-2 py-1 text-left font-normal">{p.nome}/{p.uf}</th>
                  <td className="px-2 py-1 text-right tabular-nums">{n(p.operadoras)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(p.municipios)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(p.acessos)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{formatarKm(p.p50_km)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{formatarKm(p.p80_km)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{formatarKm(p.p90_km)}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{formatarKm(p.mediana_operadora_km)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <ComoLer titulo="Como ler este mapa">
        <p>
          A operadora (CNPJ do SICI) enxerga os PTTs onde algum ASN ligado a ela aparece. Os acessos de cada município e operadora vão para o PTT mais próximo entre eles, em linha reta do centroide do município ao PIX mais próximo, e cada acesso conta uma vez.
          Na visão “{ROTULO_VISAO.diretos}” entram os ASNs com sessão própria no PTT e prefixo próprio visto nele; na visão “{ROTULO_VISAO.todos}”, também os que anunciam prefixo próprio pelo PTT sem sessão. Não há exclusão de operadoras.
        </p>
        <p>
          A faixa de cada município vem do P50 e do P80 da distância, pesados por acessos, do PTT principal dele. O mês do SICI difere da data do snapshot ({d.snapshot_date}). A página de cada PTT traz o mapa próprio, as frases e as tabelas.
        </p>
      </ComoLer>
    </div>
  )
}
