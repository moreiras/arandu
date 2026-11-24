// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchAcessosMovelMunicipios, fetchAcessosMunicipios, fetchMunicipioAcessos, fetchMunicipioAcessosMovel } from '../../services/api'
import { AccessMunicipioMap } from '../../components/acessos/AccessMunicipioMap'
import type { Servico } from './servicos'
import { fmtCnpj, fmtNum } from './formato'

/**
 * Aba "Acessos (SICI)" — não é a sede das operadoras (isso é a aba "Sede"), é onde
 * estão os USUÁRIOS: uma bolha por município (todas as operadoras agregadas),
 * proporcional aos acessos declarados. Clicar abre o detalhe por operadora.
 */
export function MapaAcessos({ servico, date }: { servico: Servico; date?: string }) {
  const movel = servico.id === 'smp'
  const { data } = useQuery({
    queryKey: [movel ? 'acessos-movel-municipios-nacional' : 'acessos-municipios-nacional', date],
    queryFn: () => (movel ? fetchAcessosMovelMunicipios : fetchAcessosMunicipios)({ date, limit: 6000 }),
    staleTime: 5 * 60 * 1000,
  })
  const [selected, setSelected] = useState<string | null>(null)
  const { data: detalhe, isLoading: loadingDetalhe } = useQuery({
    queryKey: [movel ? 'municipio-acessos-movel-detalhe' : 'municipio-acessos-detalhe', selected, date],
    queryFn: () => (movel ? fetchMunicipioAcessosMovel : fetchMunicipioAcessos)(selected!, date),
    enabled: !!selected,
  })

  return (
    <>
      <AccessMunicipioMap
        municipios={data?.items ?? []}
        height={420}
        onMunicipioClick={setSelected}
      />
      {selected && (
        <div className="absolute top-3 right-3 bottom-3 w-72 bg-white rounded-lg border border-gray-200 shadow-lg overflow-y-auto z-10">
          <div className="sticky top-0 bg-white border-b border-gray-100 px-3 py-2 flex items-start justify-between gap-2">
            <div className="min-w-0">
              {loadingDetalhe || !detalhe ? (
                <div className="text-sm text-gray-400">Carregando…</div>
              ) : (
                <>
                  <div className="font-semibold text-sm text-gray-900 truncate">{detalhe.nome}/{detalhe.uf}</div>
                  <div className="text-xs text-gray-400">
                    {fmtNum(detalhe.acessos)} acessos · {detalhe.operadores_count} operadora{detalhe.operadores_count !== 1 ? 's' : ''} · HHI {detalhe.hhi}
                  </div>
                </>
              )}
            </div>
            <button type="button" aria-label="Fechar painel" onClick={() => setSelected(null)} className="text-gray-500 hover:text-gray-700 text-lg leading-none px-1"><span aria-hidden="true">×</span></button>
          </div>
          {detalhe && (
            <div className="divide-y divide-gray-50">
              {detalhe.operadores.map(op => (
                <Link key={op.cnpj} to={`/operadora/${op.cnpj}`}
                      className="block px-3 py-2 hover:bg-gray-50">
                  <div className="text-xs font-medium text-gray-800 truncate">{op.empresa || fmtCnpj(op.cnpj)}</div>
                  <div className="text-xs text-gray-400 flex justify-between">
                    <span>{fmtNum(op.acessos)} acessos</span>
                    <span>{op.share?.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</span>
                  </div>
                </Link>
              ))}
              {!movel && (
                <Link to={`/municipio/${selected}`} className="block px-3 py-2 text-xs text-primario-600 hover:underline">
                  Ver página completa do município →
                </Link>
              )}
            </div>
          )}
        </div>
      )}
      <div className="absolute bottom-3 left-3 text-xs bg-white/90 backdrop-blur px-3 py-2 rounded shadow-sm border border-gray-200">
        Bolha proporcional aos acessos{movel ? ' móveis' : ''} declarados no município{movel ? '' : ' (todas as operadoras)'}. Clique para ver o detalhe.
      </div>
    </>
  )
}
