import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../store/app'
import { fetchExternalIXP, fetchIxpFacilities, fetchIxpPortas } from '../services/api'
import { InstalacoesPtt } from '../features/ptt/blocks/InstalacoesBloco'
import { useAsnNomes } from '../hooks/useAsnName'
import type { ExternalIXPMember } from '../types/api'
import { ExternalIXPRouteServer, type ExternalIXPComRouteServer } from './ExternalIXPRouteServer'

const FLAG: Record<string, string> = {
  BR: '🇧🇷', AR: '🇦🇷', CL: '🇨🇱', CO: '🇨🇴', PE: '🇵🇪',
  US: '🇺🇸', NL: '🇳🇱', DE: '🇩🇪', GB: '🇬🇧',
}

function speedLabel(mbps: number): string {
  if (!mbps) return '—'
  if (mbps >= 1000) return `${mbps / 1000} Gbps`
  return `${mbps} Mbps`
}

export function ExternalIXPPage() {
  const { code = '' } = useParams<{ code: string }>()
  const activeDate = useAppStore(s => s.activeDate)
  const [brOnly, setBrOnly] = useState(false)
  const [search, setSearch] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['external-ixp', code, activeDate],
    queryFn: () => fetchExternalIXP(code, activeDate ?? undefined),
    enabled: !!code,
    staleTime: Infinity, gcTime: Infinity,
  })

  // Instalações e portas do PeeringDB: opcionais (204 não existe aqui; 404 = sem dado), então um erro só esconde o bloco
  const { data: instalacoes } = useQuery({ queryKey: ['ixp-facilities', code, activeDate], queryFn: () => fetchIxpFacilities(code, activeDate ?? undefined), enabled: !!code, staleTime: Infinity, gcTime: Infinity, retry: false })
  const { data: portas } = useQuery({ queryKey: ['ixp-portas', code, activeDate], queryFn: () => fetchIxpPortas(code, activeDate ?? undefined), enabled: !!code, staleTime: Infinity, gcTime: Infinity, retry: false })

  // Membros visíveis (filtros aplicados) e os nomes só dos 500 que a tabela mostra (não o dicionário inteiro)
  const members: ExternalIXPMember[] = useMemo(() => (data?.members ?? []).filter(m => {
    if (brOnly && !m.is_br) return false
    if (search && !String(m.asn).includes(search) && !m.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  }), [data, brOnly, search])
  const nomes = useAsnNomes(useMemo(() => members.slice(0, 500).map(m => m.asn), [members]), activeDate)

  if (isLoading) return <div className="py-20 text-center text-gray-400 text-sm">Carregando...</div>
  if (error || !data) return (
    <div className="py-20 text-center text-gray-400 text-sm">
      IXP não encontrado ou dados não disponíveis.
    </div>
  )

  const flag = FLAG[data.country] ?? ''

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Cabeçalho */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-titulo-1 text-gray-900">{data.name}</h1>
          <span className="text-lg">{flag}</span>
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-aviso-100 text-aviso-800 border border-aviso-200">
            dados: PeeringDB
          </span>
        </div>
        <p className="text-sm text-gray-500">{data.city}{data.city && data.country ? ', ' : ''}{data.country}</p>
      </div>

      {/* Números */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total de membros', value: data.member_count.toLocaleString('pt-BR') },
          { label: 'Membros BR', value: data.br_member_count.toLocaleString('pt-BR') },
          { label: '% BR', value: data.member_count > 0 ? `${((data.br_member_count / data.member_count) * 100).toFixed(1)}%` : '—' },
          { label: 'Atualizado em', value: data.last_updated },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-lg border border-gray-200 px-4 py-3">
            <div className="text-xs text-gray-500 mb-1">{label}</div>
            <div className="text-xl font-semibold text-gray-900">{value}</div>
          </div>
        ))}
      </div>

      {/* Aviso */}
      <div className="bg-aviso-50 border border-aviso-200 rounded-lg px-4 py-3 text-xs text-aviso-800">
        Esta tabela lista membros autodeclarados no PeeringDB. Não inclui dados de roteamento{(data as ExternalIXPComRouteServer).route_server ? ' (os números do route server acima vêm do Alice-LG do DE-CIX)' : ''}.
        O PeeringDB pode subestimar a participação real — redes sem cadastro não aparecem aqui.
      </div>

      {(data as ExternalIXPComRouteServer).route_server && <ExternalIXPRouteServer rs={(data as ExternalIXPComRouteServer).route_server!} />}

      {(instalacoes || portas) && (
        <div className="bg-white rounded-lg border border-gray-200 px-4 py-3 space-y-2">
          <h2 className="text-base font-semibold text-gray-800">Instalações e portas (PeeringDB)</h2>
          <InstalacoesPtt facilities={instalacoes} portas={portas} />
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 flex-wrap">
          <input
            type="text"
            placeholder="Buscar ASN ou nome..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="border border-gray-200 rounded px-3 py-1.5 text-sm w-56 focus:outline-none focus:ring-1 focus:ring-primario-400"
          />
          <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
            <input type="checkbox" checked={brOnly} onChange={e => setBrOnly(e.target.checked)} className="rounded" />
            Apenas BR
          </label>
          <span className="ml-auto text-xs text-gray-400">{members.length.toLocaleString('pt-BR')} membros</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 font-medium">ASN</th>
                <th className="px-4 py-2 font-medium">Nome</th>
                <th className="px-4 py-2 font-medium">Velocidade</th>
                <th className="px-4 py-2 font-medium">BR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {members.slice(0, 500).map(m => (
                <tr key={m.asn} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <a href={`/asn/${m.asn}`} className="text-primario-600 hover:underline font-mono">
                      AS{m.asn}
                    </a>
                  </td>
                  <td className="px-4 py-2 text-gray-700 max-w-xs truncate">
                    {nomes[String(m.asn)] || m.name || '—'}
                  </td>
                  <td className="px-4 py-2 text-gray-500 tabular-nums">{speedLabel(m.speed)}</td>
                  <td className="px-4 py-2">
                    {m.is_br ? (
                      <span className="text-ok-600 font-medium text-xs">✓ BR</span>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {members.length > 500 && (
                <tr>
                  <td colSpan={4} className="px-4 py-3 text-xs text-gray-400 text-center">
                    Mostrando 500 de {members.length.toLocaleString('pt-BR')} membros. Use os filtros para refinar.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
