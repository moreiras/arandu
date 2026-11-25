// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ComoLer } from '../../components/ui/ComoLer'
import { EstadoDados } from '../../components/ui/EstadoDados'
import { LinhaProveniencia } from '../../components/ui/Kpi'
import { fmtKm } from '../../lib/geo'
import { fetchInfraProximos } from '../../services/api'
import type { CamadaInfra, InfraProximos } from '../../types/api'

const n = (v: number) => v.toLocaleString('pt-BR')
const MAXIMO_KM = 500
const ORDEM = ['enlaces', 'linhas_transmissao', 'cabos', 'pontos_aterrissagem'] as const
const ROTULO: Record<(typeof ORDEM)[number], string> = {
  enlaces: 'Enlaces terrestres de transmissão (UIT)', linhas_transmissao: 'Linhas de transmissão de energia (ONS/Aneel)',
  cabos: 'Cabos submarinos (TeleGeography)', pontos_aterrissagem: 'Pontos de aterrissagem de cabos submarinos (TeleGeography)',
}

const nomeDoItem = (i: { name?: string }) => (i.name && String(i.name).trim()) || 'sem nome no cadastro'
const statusEmTexto = (s?: Record<string, number>) => (s ? Object.entries(s).map(([k, v]) => `${n(v)} ${k}`).join(', ') : '')

/** Corpo do bloco: contagens por tipo, as mais próximas com distância, status e fonte, e a frase de ausência para as instalações. Puro, para teste. */
export function CorpoInfraFisica({ dados, raioKm }: { dados: InfraProximos; raioKm: number }) {
  const inst = dados.instalacoes
  return (
    <div className="space-y-3" data-testid="infra-corpo">
      <LinhaProveniencia selo="inferido" fonte="TeleGeography, UIT, ONS/Aneel (SIGEL) e PeeringDB; distância em linha reta até a geometria" dataRef={dados.snapshot_date} />
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <caption className="sr-only">Infraestrutura física a até {n(raioKm)} km do ponto: quantidade por tipo e as ocorrências mais próximas, com distância, status e fonte</caption>
          <thead className="text-xs text-gray-600">
            <tr><th scope="col" className="px-2 py-1 text-left">Tipo</th><th scope="col" className="px-2 py-1 text-right">No raio</th><th scope="col" className="px-2 py-1 text-left">Mais próximas (distância em linha reta; status)</th></tr>
          </thead>
          <tbody>
            {ORDEM.map((k) => {
              const c: CamadaInfra | undefined = dados.camadas[k]
              return (
                <tr key={k} className="border-t border-gray-100 align-top">
                  <th scope="row" className="px-2 py-1 text-left font-normal">{ROTULO[k]}</th>
                  {c ? (
                    <>
                      <td className="px-2 py-1 text-right tabular-nums">{n(c.total)}{c.por_status && <span className="block text-xs text-gray-600">{statusEmTexto(c.por_status)}</span>}</td>
                      <td className="px-2 py-1">
                        {c.itens.length === 0 ? <span className="text-gray-600">nenhuma a até {n(raioKm)} km</span> : (
                          <ul className="space-y-0.5">
                            {c.itens.map((i, ix) => (
                              <li key={`${k}-${ix}`}>{nomeDoItem(i)}: {fmtKm(i.distancia_km)}{i.status ? `; ${i.status}` : ''}</li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </>
                  ) : <td colSpan={2} className="px-2 py-1 text-gray-600">camada indisponível neste snapshot</td>}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="text-sm" data-testid="infra-instalacoes">
        <p className="font-medium text-gray-700">Instalações cadastradas no PeeringDB</p>
        {inst.total === 0
          ? <p>Nenhuma instalação cadastrada no PeeringDB a até {n(inst.raio_km)} km.</p>
          : (
            <>
              <p>{n(inst.total)} {inst.total === 1 ? 'instalação cadastrada' : 'instalações cadastradas'} a até {n(inst.raio_km)} km (cadastro autodeclarado).</p>
              <ul className="list-disc pl-5">
                {inst.itens.map((i, ix) => <li key={`${i.id ?? ix}`}>{i.nome ?? 'sem nome'}{i.cidade ? `, ${i.cidade}${i.uf ? `/${i.uf}` : ''}` : ''}: {fmtKm(i.distancia_km)}</li>)}
              </ul>
            </>
          )}
      </div>
      <ComoLer>
        <p>Enlaces da UIT e linhas da Aneel têm geometria aproximada e não informam capacidade disponível nem quem os opera. Instalações vêm de cadastro autodeclarado no PeeringDB. Planejado não é existente: o status de cada enlace está ao lado. Proximidade de um cabo, de um enlace ou de uma linha de energia não quer dizer que as redes locais o usam, e não mede viabilidade.</p>
        <p>Distância em linha reta do ponto até a geometria mais próxima (selo inferido); a distância pelo trajeto é maior. A tabela mostra as ocorrências mais próximas de cada tipo; o mapa tem as camadas completas.</p>
      </ComoLer>
    </div>
  )
}

/**
 * Infraestrutura física no raio (PT-25, localizador 5.5 e município 5.4). Recolhido: a rota é `metered`, de poucos URLs por ponto, e só é chamada quando o leitor abre o bloco
 * (mudar o ponto ou o raio com o bloco fechado não gera pedido). `raioKm` e as coordenadas já chegam estáveis (o Localizador passa o raio atrasado).
 */
export function InfraFisicaRaio({ lat, lon, raioKm, date, titulo = 'Infraestrutura física no raio', raioInstalacoesKm = 150, aberto = false }: {
  lat: number; lon: number; raioKm: number; date?: string; titulo?: string; raioInstalacoesKm?: number; aberto?: boolean
}) {
  const [aberta, setAberta] = useState(aberto)
  const raio = Math.max(1, Math.min(MAXIMO_KM, Math.round(raioKm)))
  const la = Math.round(lat * 1e4) / 1e4
  const lo = Math.round(lon * 1e4) / 1e4
  const q = useQuery({
    queryKey: ['infra-proximos', date ?? null, la, lo, raio, raioInstalacoesKm],
    queryFn: () => fetchInfraProximos({ lat: la, lon: lo, raio_km: raio, raio_instalacoes_km: raioInstalacoesKm, date }),
    enabled: aberta, staleTime: Infinity, gcTime: 10 * 60_000,
  })
  return (
    <details className="rounded-lg border border-gray-200 bg-white p-4" data-testid="infra-fisica" onToggle={(e) => setAberta((e.currentTarget as HTMLDetailsElement).open)} open={aberto || undefined}>
      <summary className="cursor-pointer text-titulo-3 text-gray-800">{titulo} <span className="text-xs font-normal text-gray-600">(até {n(raio)} km; abra para consultar)</span></summary>
      <div className="mt-3">
        {q.isLoading && <p className="text-sm text-gray-600" role="status">Consultando a infraestrutura no raio…</p>}
        {q.error && <EstadoDados erro={q.error} oQue="a infraestrutura física no raio" />}
        {q.data && <CorpoInfraFisica dados={q.data} raioKm={raio} />}
      </div>
    </details>
  )
}
