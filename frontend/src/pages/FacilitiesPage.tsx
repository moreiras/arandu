// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchFacilities } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { UFS } from '../lib/ufs'
import { AtribuicaoPeeringDb, LinkInstalacao, SeloCadastro, localDe, n } from '../features/instalacoes/comum'
import { MapaInstalacoes } from '../features/instalacoes/MapaInstalacoes'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados } from '../components/ui/EstadoDados'
import type { Sentido } from '../lib/ordenacao'

const POR_PAGINA = 100       // a prévia aberta: acima disso (ou página 2) a API exige login
// Ordens que a API aceita (`ordem`), cada uma num sentido só: o cabeçalho escolhe a ordem no servidor, que ordena a lista inteira antes de paginar.
const SENTIDO_ORDEM: Record<string, Sentido> = { nome: 'asc', redes: 'desc', ptts: 'desc', atualizado: 'desc' }

/**
 * `/instalacoes` — datacenters e pontos de interconexão cadastrados no PeeringDB no Brasil, com mapa e filtros.
 * Cadastro autodeclarado; o selo de cadastro (recente, parado, antigo) é inferido da data de atualização do registro e não diz nada da operação da instalação nem da empresa.
 */
export function FacilitiesPage() {
  const date = useActiveDate()
  const [q, setQ] = useState('')
  const [uf, setUf] = useState('')
  const [cadastro, setCadastro] = useState('')
  const [comPtt, setComPtt] = useState(false)
  const [ordem, setOrdem] = useState('redes')
  const [pagina, setPagina] = useState(1)
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['facilities', date, q, uf, cadastro, comPtt, ordem, pagina],
    queryFn: () => fetchFacilities({ date: date ?? undefined, q: q || undefined, uf: uf || undefined, cadastro: cadastro || undefined, com_ptt: comPtt || undefined, ordem, limit: POR_PAGINA, page: pagina }),
    staleTime: 5 * 60 * 1000, placeholderData: (anterior) => anterior,
  })
  const mudar = <T,>(set: (v: T) => void) => (v: T) => { set(v); setPagina(1) }
  const total = data?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const th = (campo: string) => ({ campo, ordem: { campo: ordem, dir: SENTIDO_ORDEM[ordem] ?? 'desc' }, onOrdenar: mudar(setOrdem) })

  return (
    <div className="space-y-4" data-testid="pagina-instalacoes">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Instalações (datacenters) do PeeringDB</h1>
        <p className="text-sm text-gray-500">
          Datacenters e pontos de interconexão cadastrados no Brasil, com as redes, PTTs e carriers que declaram estar neles.
          O selo de cadastro é <b>inferido</b> da data da última atualização do registro: mede a manutenção do cadastro, não a operação da instalação nem da empresa.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col text-xs text-gray-500">Nome, organização ou cidade
          <input value={q} onChange={(e) => mudar(setQ)(e.target.value)} className="border border-gray-200 rounded px-2 py-1 text-sm w-56" placeholder="ex.: Equinix, Barueri" />
        </label>
        <label className="flex flex-col text-xs text-gray-500">UF
          <select value={uf} onChange={(e) => mudar(setUf)(e.target.value)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="">todas</option>
            {Object.keys(UFS).map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </label>
        <label className="flex flex-col text-xs text-gray-500">Cadastro
          <select value={cadastro} onChange={(e) => mudar(setCadastro)(e.target.value)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="">todos</option><option value="recente">atualizado (até 12 meses)</option><option value="parado">parado (1 a 3 anos)</option><option value="antigo">antigo (mais de 3 anos)</option>
          </select>
        </label>
        <label className="flex flex-col text-xs text-gray-500">Ordem
          <select value={ordem} onChange={(e) => mudar(setOrdem)(e.target.value)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="redes">mais redes</option><option value="ptts">mais PTTs</option><option value="nome">nome</option><option value="atualizado">atualização mais recente</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-sm text-gray-600">
          <input type="checkbox" checked={comPtt} onChange={(e) => mudar(setComPtt)(e.target.checked)} /> só com PTT
        </label>
      </div>

      {isLoading && <p className="text-sm text-gray-400">Carregando…</p>}
      {isError && <EstadoDados erro={error} oQue="as instalações do PeeringDB" mensagem="Instalações do PeeringDB indisponíveis neste snapshot." />}
      {data && (
        <>
          <p className="text-xs text-gray-500" data-testid="total-instalacoes">
            {n(total)} instalação(ões){data.cobertura ? ` · ${n(data.cobertura.ptts_ixbr_com_instalacao)} de ${n(data.cobertura.ptts_ixbr)} PTTs do IX.br têm instalação cadastrada` : ''}
            {total > POR_PAGINA ? ` · mapa e lista mostram a página ${pagina} de ${paginas}` : ''}
          </p>
          <MapaInstalacoes itens={data.items} />
          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
                  <ThOrdenavel {...th('nome')} className="px-3 py-2 font-medium">Instalação</ThOrdenavel><th scope="col" className="px-3 py-2 font-medium">Organização</th><th scope="col" className="px-3 py-2 font-medium">Local</th>
                  <ThOrdenavel {...th('redes')} alinhar="right" className="px-3 py-2 font-medium text-right">Redes</ThOrdenavel><ThOrdenavel {...th('ptts')} alinhar="right" className="px-3 py-2 font-medium text-right">PTTs</ThOrdenavel><th scope="col" className="px-3 py-2 font-medium text-right">Carriers</th><ThOrdenavel {...th('atualizado')} className="px-3 py-2 font-medium">Cadastro</ThOrdenavel>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((f) => (
                  <tr key={f.id} className="hover:bg-gray-50">
                    <td className="px-3 py-1.5"><LinkInstalacao f={f} /></td>
                    <td className="px-3 py-1.5 text-gray-600">{f.org_nome ?? '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600">{localDe(f)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{n(f.n_redes ?? f.redes_declaradas)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{n(f.n_ptts)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{n(f.n_carriers)}</td>
                    <td className="px-3 py-1.5"><SeloCadastro c={f.cadastro} /></td>
                  </tr>
                ))}
                {data.items.length === 0 && <tr><td colSpan={7} className="px-3 py-4 text-center text-xs text-gray-400">Nenhuma instalação com esses filtros.</td></tr>}
              </tbody>
            </table>
          </div>
          {paginas > 1 && (
            <div className="flex items-center gap-3 text-sm">
              <button disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)} className="px-2 py-1 border border-gray-200 rounded disabled:opacity-40">Anterior</button>
              <span className="text-xs text-gray-500">página {pagina} de {paginas}</span>
              <button disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)} className="px-2 py-1 border border-gray-200 rounded disabled:opacity-40">Próxima</button>
            </div>
          )}
          <AtribuicaoPeeringDb meta={data} />
        </>
      )}
    </div>
  )
}
