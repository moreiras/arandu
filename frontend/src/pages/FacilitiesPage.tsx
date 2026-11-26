// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { fetchFacilities } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { UFS } from '../lib/ufs'
import { AtribuicaoPeeringDb, LinkInstalacao, PttsDaInstalacao, SeloCadastro, localDe, n } from '../features/instalacoes/comum'
import { MapaInstalacoes } from '../features/instalacoes/MapaInstalacoes'
import { ThOrdenavel } from '../components/ui/ThOrdenavel'
import { EstadoDados } from '../components/ui/EstadoDados'
import type { Sentido } from '../lib/ordenacao'
import type { FacilitiesLista } from '../types/api'
import { palavra } from '../lib/sintese'

const POR_PAGINA = 100       // a prévia aberta: acima disso (ou página 2) a API exige login
// Ordens que a API aceita (`ordem`), cada uma num sentido só: o cabeçalho escolhe a ordem no servidor, que ordena a lista inteira antes de paginar.
const SENTIDO_ORDEM: Record<string, Sentido> = { nome: 'asc', redes: 'desc', ptts: 'desc', atualizado: 'desc' }

/** A cobertura de PTTs do IX.br, nomeada: quais aparecem em alguma instalação, quais não têm instalação cadastrada e quais o mapeamento com o PeeringDB não alcança. Fato do snapshot, sem adjetivo. */
function CoberturaPtts({ cob }: { cob: NonNullable<FacilitiesLista['cobertura']> }) {
  const nomes = cob.ptts_ixbr_nomes ?? {}
  const lista = (cs: string[]) => cs.map((c) => (nomes[c] ? `${nomes[c]} (${c.toUpperCase()})` : c.toUpperCase())).join(', ')
  const total = cob.ptts_ixbr_site ?? cob.ptts_ixbr
  return (
    <div className="text-xs text-gray-600 space-y-0.5" data-testid="cobertura-ptts">
      <p>PTTs do IX.br: {n(cob.ptts_ixbr_com_instalacao)} de {n(total)} aparecem em alguma instalação do PeeringDB.</p>
      {!!cob.ptts_ixbr_sem_instalacao?.length && <p>Sem instalação cadastrada no PeeringDB nesta coleta: {lista(cob.ptts_ixbr_sem_instalacao)}.</p>}
      {!!cob.ptts_ixbr_sem_mapeamento?.length && <p>Sem registro do PTT no PeeringDB ligado ao site: {lista(cob.ptts_ixbr_sem_mapeamento)}.</p>}
      {!!cob.ptts_ixbr_fora_do_site?.length && <p>Códigos do cadastro que não são PTT do site: {cob.ptts_ixbr_fora_do_site.join(', ')}.</p>}
    </div>
  )
}

/**
 * `/instalacoes` — datacenters e pontos de interconexão cadastrados no PeeringDB no Brasil, com mapa e filtros.
 * Cadastro autodeclarado; o selo de cadastro (recente, parado, antigo) é inferido da data de atualização do registro e não diz nada da operação da instalação nem da empresa.
 */
export function FacilitiesPage() {
  const date = useActiveDate()
  // Os filtros vivem na URL (link compartilhável, Voltar desfaz): `q`, `uf`, `cadastro`, `ptt`, `carrier`, `so_ptt`, `ordem` e `pagina`.
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const uf = params.get('uf') ?? ''
  const cadastro = params.get('cadastro') ?? ''
  const ptt = params.get('ptt') ?? ''
  const comCarrier = params.get('carrier') === '1'
  const comPtt = params.get('so_ptt') === '1'
  const ordem = params.get('ordem') && SENTIDO_ORDEM[params.get('ordem')!] ? params.get('ordem')! : 'redes'
  const pagina = Math.max(1, Number(params.get('pagina')) || 1)
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['facilities', date, q, uf, cadastro, ptt, comCarrier, comPtt, ordem, pagina],
    queryFn: () => fetchFacilities({ date: date ?? undefined, q: q || undefined, uf: uf || undefined, cadastro: cadastro || undefined, ptt: ptt || undefined, com_carrier: comCarrier || undefined, com_ptt: comPtt || undefined, ordem, limit: POR_PAGINA, page: pagina }),
    staleTime: 5 * 60 * 1000, placeholderData: (anterior) => anterior,
  })
  const mudarParam = (chave: string, valor: string | null, resetaPagina = true) => setParams((ant) => {
    const p = new URLSearchParams(ant)
    if (valor) p.set(chave, valor); else p.delete(chave)
    if (resetaPagina) p.delete('pagina')
    return p
  }, { replace: true })
  const setPagina = (v: number) => mudarParam('pagina', v > 1 ? String(v) : null, false)
  const total = data?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const th = (campo: string) => ({ campo, ordem: { campo: ordem, dir: SENTIDO_ORDEM[ordem] ?? 'desc' }, onOrdenar: (c: string) => mudarParam('ordem', c === 'redes' ? null : c) })

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
          <input value={q} onChange={(e) => mudarParam('q', e.target.value || null)} className="border border-gray-200 rounded px-2 py-1 text-sm w-56" placeholder="ex.: Equinix, Barueri" />
        </label>
        <label className="flex flex-col text-xs text-gray-500">UF
          <select value={uf} onChange={(e) => mudarParam('uf', e.target.value || null)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="">todas</option>
            {Object.keys(UFS).map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </label>
        <label className="flex flex-col text-xs text-gray-500">Cadastro
          <select value={cadastro} onChange={(e) => mudarParam('cadastro', e.target.value || null)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="">todos</option><option value="recente">atualizado (até 12 meses)</option><option value="parado">parado (1 a 3 anos)</option><option value="antigo">antigo (mais de 3 anos)</option>
          </select>
        </label>
        <label className="flex flex-col text-xs text-gray-500">Ordem
          <select value={ordem} onChange={(e) => mudarParam('ordem', e.target.value === 'redes' ? null : e.target.value)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="redes">mais redes</option><option value="ptts">mais PTTs</option><option value="nome">nome</option><option value="atualizado">atualização mais recente</option>
          </select>
        </label>
        <label className="flex flex-col text-xs text-gray-500">PTT do IX.br
          <select value={ptt} onChange={(e) => mudarParam('ptt', e.target.value || null)} className="border border-gray-200 rounded px-2 py-1 text-sm">
            <option value="">todos</option>
            {Object.entries(data?.cobertura?.ptts_ixbr_nomes ?? {}).map(([c, nome]) => <option key={c} value={c}>{nome} ({c.toUpperCase()})</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-sm text-gray-600">
          <input type="checkbox" checked={comPtt} onChange={(e) => mudarParam('so_ptt', e.target.checked ? '1' : null)} /> só com PTT
        </label>
        <label className="flex items-center gap-1.5 text-sm text-gray-600">
          <input type="checkbox" checked={comCarrier} onChange={(e) => mudarParam('carrier', e.target.checked ? '1' : null)} /> só com carrier
        </label>
      </div>

      {isLoading && <p className="text-sm text-gray-400">Carregando…</p>}
      {isError && <EstadoDados erro={error} oQue="as instalações do PeeringDB" mensagem="Instalações do PeeringDB indisponíveis neste snapshot." />}
      {data && (
        <>
          <p className="text-xs text-gray-500" data-testid="total-instalacoes">
            {n(total)} {palavra(total, 'instalação', 'instalações')}{total > POR_PAGINA ? ` · mapa e lista mostram a página ${pagina} de ${paginas}` : ''}
          </p>
          {data.cobertura && <CoberturaPtts cob={data.cobertura} />}
          <MapaInstalacoes itens={data.items} />
          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
                  <ThOrdenavel {...th('nome')} className="px-3 py-2 font-medium">Instalação</ThOrdenavel><th scope="col" className="px-3 py-2 font-medium">Organização</th><th scope="col" className="px-3 py-2 font-medium">Local</th>
                  <ThOrdenavel {...th('redes')} alinhar="right" className="px-3 py-2 font-medium text-right">Redes</ThOrdenavel><ThOrdenavel {...th('ptts')} className="px-3 py-2 font-medium">PTTs</ThOrdenavel><th scope="col" className="px-3 py-2 font-medium text-right">Carriers</th><ThOrdenavel {...th('atualizado')} className="px-3 py-2 font-medium">Cadastro</ThOrdenavel>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((f) => (
                  <tr key={f.id} className="hover:bg-gray-50">
                    <td className="px-3 py-1.5"><LinkInstalacao f={f} /></td>
                    <td className="px-3 py-1.5 text-gray-600">{f.org_nome ?? '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600">{localDe(f)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{n(f.n_redes ?? f.redes_declaradas)}</td>
                    <td className="px-3 py-1.5"><PttsDaInstalacao f={f} nomes={data.cobertura?.ptts_ixbr_nomes} /></td>
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
