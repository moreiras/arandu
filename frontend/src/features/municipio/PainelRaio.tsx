// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Suspense, lazy, useEffect, useState } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { fmtKm, type LonLat } from '../../lib/geo'
import type { PerfilMunicipio } from '../../types/api'
import { fmt } from './ui'
import { MAX_MUNICIPIOS_RAIO, RAIO_MAX_KM, RAIO_PASSO_KM, type ConjuntoRaio } from './raio'

const MapaRaio = lazy(() => import('./MapaRaio').then((m) => ({ default: m.MapaRaio })))

/** Texto que diz quantos municípios entram nas somas e por quê (o teto corta antes do raio pedido). */
export function resumoConjunto(c: ConjuntoRaio): string {
  const n = c.selecionados.length
  if (c.raioKm === 0) return 'Só o município (raio 0 km). Aumente o raio para somar os municípios vizinhos.'
  if (c.cortado) return `Há ${fmt(c.dentroDoRaio)} municípios em ${fmt(c.raioKm)} km; as somas cobrem os ${fmt(n)} mais próximos, até ${fmtKm(c.raioEfetivoKm)} (teto de ${MAX_MUNICIPIOS_RAIO}).`
  return `${fmt(n)} ${n === 1 ? 'município' : 'municípios'} num raio de ${fmt(c.raioKm)} km.`
}

/**
 * Raio da página de município: o slider (0–500 km, o valor sobe na URL depois de uma pausa), o resumo do conjunto, o mapa e a lista.
 * O trilho fica cheio até o raio efetivo e hachurado depois: arrastar além dele não acrescenta município (teto).
 */
export function PainelRaio({ conjunto, raioKm, onRaio, centroides, perfis, prontos, total }: {
  conjunto: ConjuntoRaio
  raioKm: number
  onRaio: (km: number) => void
  centroides: Record<string, LonLat>
  perfis: Record<string, PerfilMunicipio | null | undefined>
  prontos: number
  total: number
}) {
  const [valor, setValor] = useState(raioKm)
  useEffect(() => setValor(raioKm), [raioKm])
  useEffect(() => {
    if (valor === raioKm) return
    const t = setTimeout(() => onRaio(valor), 300)
    return () => clearTimeout(t)
  }, [valor, raioKm, onRaio])

  const pctEfetivo = (100 * Math.min(conjunto.raioEfetivoKm, RAIO_MAX_KM)) / RAIO_MAX_KM
  const trilho = conjunto.cortado && valor > conjunto.raioEfetivoKm
    ? `linear-gradient(to right, #2563eb ${pctEfetivo}%, #e2e8f0 ${pctEfetivo}%)`
    : `linear-gradient(to right, #2563eb ${(100 * valor) / RAIO_MAX_KM}%, #e2e8f0 ${(100 * valor) / RAIO_MAX_KM}%)`
  const nomes: Record<string, string> = {}
  for (const v of conjunto.selecionados) { const p = perfis[v.ibge]; if (p) nomes[v.ibge] = `${p.nome} ${p.uf}` }

  return (
    <section className="bg-white rounded-lg border border-gray-200 p-4 space-y-3" data-testid="painel-raio" aria-label="Raio de municípios">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <label htmlFor="raio-km" className="text-sm font-medium text-gray-700">Raio em volta do município</label>
        <input id="raio-km" type="range" min={0} max={RAIO_MAX_KM} step={RAIO_PASSO_KM} value={valor} onChange={(e) => setValor(Number(e.target.value))}
          className="flex-1 min-w-[12rem] h-2 rounded-lg appearance-none cursor-pointer" style={{ background: trilho }} aria-valuetext={`${valor} quilômetros`} />
        <output htmlFor="raio-km" className="text-sm font-semibold tabular-nums w-16 text-right">{fmt(valor)} km</output>
      </div>
      <p className="text-sm text-gray-600" data-testid="resumo-raio">{resumoConjunto(conjunto)}</p>
      {raioKm > 0 && prontos < total && <p className="text-xs text-gray-500" role="status">Carregando os municípios: {fmt(prontos)} de {fmt(total)}…</p>}
      <Suspense fallback={<div className="h-80 rounded-lg bg-gray-50" />}>
        <MapaRaio conjunto={conjunto} centroides={centroides} nomes={nomes} />
      </Suspense>
      <p className="text-xs text-gray-500" data-testid="legenda-raio">
        Contornos dos municípios (Fonte: IBGE, Malha Municipal 2024): contorno escuro e área mais firme, o município da página; área clara, os municípios somados
        {conjunto.cortado ? '; contorno cinza tracejado, os que estão no raio pedido mas passaram do limite e não entram nas somas' : ''}. A lista dos municípios fica logo abaixo.
      </p>
      {raioKm > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-600">Municípios somados ({fmt(conjunto.selecionados.length)})</summary>
          <ul className="mt-2 grid sm:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-1">
            {conjunto.selecionados.map((v) => {
              const p = perfis[v.ibge]
              return (
                <li key={v.ibge} className="flex justify-between gap-2">
                  {p ? <Link to={`/municipio/${v.ibge}`} className="text-primario-600 hover:underline truncate">{p.nome} <span className="text-gray-400">{p.uf}</span></Link>
                    : <span className="text-gray-400 truncate" title="sem acesso declarado ou ainda carregando">IBGE {v.ibge}</span>}
                  <span className="tabular-nums text-gray-500">{v.km === 0 ? 'centro' : fmtKm(v.km)}</span>
                </li>
              )
            })}
          </ul>
        </details>
      )}
      <p className="text-xs text-gray-500">
        Distância em linha reta entre centróides: um município entra se o centróide dele está dentro do raio, não pela área. Somas de acessos, domicílios, estações e compromissos;
        participação, HHI, penetração e variação são refeitas sobre o total; a distância ao PTT continua a do município central.
      </p>
    </section>
  )
}
