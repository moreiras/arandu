// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { HQ_COLOR, SCM_HQ_COLOR, SICI_COLOR, V4_STRONG, V4_WEAK, V6_STRONG, V6_WEAK } from './tipos'

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-500">
      <span
        className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
        style={{ background: color }}
      />
      {label}
    </div>
  )
}

export interface CamadasLigadas { asns: boolean; prefixes: boolean; scms: boolean; sici: boolean }

/** Painel esquerdo: busca por município, raio, camadas e legenda. */
export function PainelControles({ className, search, setSearch, searching, onSearch, radius, setRadius, show, setShow, aoDefinirCoordenadas }: {
  className: string
  search: string; setSearch: (v: string) => void; searching: boolean; onSearch: () => void
  radius: number; setRadius: (v: number) => void
  show: CamadasLigadas; setShow: (p: Partial<CamadasLigadas>) => void
  /** Define o ponto por coordenadas digitadas (alternativa ao clique no mapa). */
  aoDefinirCoordenadas?: (lat: number, lon: number) => void
}) {
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const latN = Number(lat.replace(',', '.')), lonN = Number(lon.replace(',', '.'))
  const coordValida = lat.trim() !== '' && lon.trim() !== '' && Number.isFinite(latN) && Number.isFinite(lonN) && Math.abs(latN) <= 90 && Math.abs(lonN) <= 180
  const { asns: showAsns, prefixes: showPrefixes, scms: showScms, sici: showSici } = show
  return (
    <div className={className}>
      <div className="flex gap-1.5">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onSearch()}
          aria-label="Município (nome, ou nome/UF)"
          placeholder="Nome do município…"
          className="flex-1 min-w-0 rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primario-500 bg-white"
        />
        <button
          onClick={onSearch}
          disabled={searching}
          className="px-2.5 py-1.5 rounded-lg bg-primario-600 text-white text-sm hover:bg-primario-700 disabled:opacity-50 whitespace-nowrap flex-shrink-0"
        >
          {searching ? <span aria-hidden="true">…</span> : 'Ir'}
          <span className="sr-only">{searching ? 'Buscando o município' : ' ao município'}</span>
        </button>
      </div>

      {aoDefinirCoordenadas && (
        <form className="space-y-1" aria-label="Ponto por coordenadas" onSubmit={(e) => { e.preventDefault(); if (coordValida) aoDefinirCoordenadas(latN, lonN) }}>
          <div className="flex gap-1.5">
            <label className="flex-1 min-w-0 text-xs text-gray-600">Latitude
              <input type="text" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} placeholder="-9,40" className="mt-0.5 w-full rounded-lg border border-gray-300 px-2 py-1 text-sm bg-white" />
            </label>
            <label className="flex-1 min-w-0 text-xs text-gray-600">Longitude
              <input type="text" inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} placeholder="-40,50" className="mt-0.5 w-full rounded-lg border border-gray-300 px-2 py-1 text-sm bg-white" />
            </label>
          </div>
          <button type="submit" disabled={!coordValida} className="min-h-6 text-xs text-primario-700 hover:underline disabled:text-gray-500 disabled:no-underline">Usar estas coordenadas</button>
        </form>
      )}

      {/* Radius slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">Raio</span>
          <span className="text-xs font-mono font-semibold text-gray-700">{radius} km</span>
        </div>
        <input
          type="range"
          aria-label="Raio da busca, em quilômetros"
          min={0}
          max={500}
          step={5}
          value={radius}
          onChange={e => setRadius(Number(e.target.value))}
          className="w-full accent-primario-600"
        />
        <div className="flex justify-between text-xs text-gray-400">
          <span>0</span>
          <span>250</span>
          <span>500 km</span>
        </div>
      </div>

      {/* Overlay checkboxes */}
      <div className="space-y-1.5 pt-1 border-t border-gray-100">
        <span className="text-xs text-gray-500">Exibir na área de busca</span>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showAsns}
            onChange={e => setShow({ asns: e.target.checked })}
            className="rounded accent-slate-600"
          />
          <span
            className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 border border-white"
            style={{ background: HQ_COLOR }}
          />
          <span className="text-sm text-gray-700">Sedes de AS</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showPrefixes}
            onChange={e => setShow({ prefixes: e.target.checked })}
            className="rounded accent-primario-600"
          />
          <span className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 bg-primario-500" />
          <span className="text-sm text-gray-700">Prefixos geolocalizados</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showScms}
            onChange={e => setShow({ scms: e.target.checked })}
            className="rounded accent-v6-600"
          />
          <span className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0 bg-v6-500" />
          <span className="text-sm text-gray-700">Outorgas SCM (Anatel)</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showSici}
            onChange={e => setShow({ sici: e.target.checked })}
            className="rounded accent-perigo-600"
          />
          <span
            className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ background: SICI_COLOR }}
          />
          <span className="text-sm text-gray-700">Usuários informados no SICI (Anatel)</span>
        </label>
      </div>

      {/* Legend */}
      <div className="space-y-1 pt-1 border-t border-gray-100">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <span
            className="inline-block w-3 h-3 rounded-full flex-shrink-0"
            style={{ background: '#fbbf24', border: '1.5px solid #92400e' }}
          />
          PIX (PTT do IX.br)
        </div>
        {showPrefixes && (
          <>
            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 pt-0.5">
              <LegendDot color={V4_STRONG} label="IPv4 · sede aqui" />
              <LegendDot color={V4_WEAK} label="IPv4 · sede fora" />
              <LegendDot color={V6_STRONG} label="IPv6 · sede aqui" />
              <LegendDot color={V6_WEAK} label="IPv6 · sede fora" />
            </div>
            <p className="text-xs text-gray-400 leading-tight pt-0.5">
              Bolha = prefixos do AS numa cidade · tamanho ∝ nº de prefixos.
            </p>
          </>
        )}
        {showScms && (
          <div className="flex gap-3">
            <LegendDot color={SCM_HQ_COLOR} label="SCM com AS" />
            <LegendDot color="#a855f7" label="SCM sem AS" />
          </div>
        )}
        {showSici && (
          <p className="text-xs text-gray-400 leading-tight pt-0.5">
            Ponto = município com acessos declarados ao SICI, no centróide do IBGE.
          </p>
        )}
        <p className="text-xs text-gray-400 leading-tight pt-0.5">
          Clique no mapa ou busque para definir o ponto central. Arraste o marcador para mover.
        </p>
      </div>
    </div>
  )
}
