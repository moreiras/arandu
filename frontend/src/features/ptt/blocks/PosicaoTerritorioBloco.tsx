// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { Link } from '../../../components/layout/LinkDatado'
import { ComoLer } from '../../../components/ui/ComoLer'
import { n0, palavra } from '../../../lib/sintese'
import { fetchIXPs } from '../../../services/api'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'
import { outrosPttsNaUf, posicaoEntrePttsDoIxbr } from '../posicaoPtt'

/** A lista dos PTTs (`/ixps`, aberta): a mesma chave da síntese e do destaque, uma busca só. */
function useListaPtts(date: string | null) {
  return useQuery({ queryKey: ['ixps', date], queryFn: () => fetchIXPs(date ?? undefined), staleTime: Infinity, gcTime: Infinity, retry: false })
}

/**
 * "Este PTT entre os PTTs do IX.br" (PT-22 / ixp 5.4): cada medida com o valor do PTT, a mediana e a posição (1 = maior valor). A barra é só um reforço visual de uma tabela
 * de texto: o valor está escrito. Tamanho não mede relevância regional, e a posição não é juízo.
 */
export function PosicaoPttBloco({ dados }: BlocoProps<PttCtx>) {
  const lista = useListaPtts(dados.date)
  const linhas = posicaoEntrePttsDoIxbr(dados.code, lista.data?.ixps)
  if (linhas.length === 0) return null
  return (
    <div className="space-y-2" data-testid="posicao-ptt">
      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <caption className="sr-only">Medidas deste PTT, a mediana dos PTTs do IX.br e a posição pelo maior valor</caption>
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-600">
              <th scope="col" className="py-1 pr-3 font-medium">Medida</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Este PTT</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Mediana dos PTTs</th>
              <th scope="col" className="py-1 pl-2 text-right font-medium">Posição (1 = maior valor)</th>
              <th scope="col" className="py-1 pl-3 font-medium"><span className="sr-only">Barra proporcional ao maior valor</span></th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.id} className="border-b border-gray-100 text-gray-700">
                <th scope="row" className="py-1 pr-3 text-left font-normal">{l.rotulo}</th>
                <td className="py-1 px-2 text-right">{l.valor == null ? 'sem dado' : n0(l.valor)}</td>
                <td className="py-1 px-2 text-right">{l.mediana == null ? '—' : n0(l.mediana)}</td>
                <td className="py-1 pl-2 text-right">{l.posicao == null ? '—' : `${n0(l.posicao)} de ${n0(l.de)}`}</td>
                <td className="py-1 pl-3 w-28" aria-hidden="true">
                  {l.valor != null && l.maximo ? <div className="h-2 rounded bg-gray-100"><div className="h-2 rounded bg-tecnico-600" style={{ width: `${Math.max(2, (100 * l.valor) / l.maximo)}%` }} /></div> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-600">
        As medidas vêm do cadastro do IX.br e dos looking glasses de cada PTT, no mesmo snapshot. Família sem coleta fica sem valor e fora da mediana. Tamanho em ASNs não mede a relevância regional do PTT.
      </p>
    </div>
  )
}

/** Sentença curta do que é um PTT, para quem chega sem o vocabulário (jornalista, gestor público). */
export const O_QUE_E_UM_PTT = 'Um PTT (ponto de troca de tráfego) é o local onde redes diferentes se interligam para trocar tráfego diretamente. No IX.br, cada PTT tem route servers, que '
  + 'distribuem as rotas entre os participantes que escolhem usá-los; participantes também podem se interligar por acordos bilaterais, que a coleta do site não vê.'

/**
 * "No território" (PT-22 / ixp 5.4): a UF do PTT como link, os outros PTTs do IX.br na mesma UF e o parágrafo "O que é um PTT". Os municípios dos participantes e dos
 * alcançados ficam nos mapas e na tabela de participantes; esta lista não os repete.
 */
export function TerritorioPttBloco({ dados }: BlocoProps<PttCtx>) {
  const lista = useListaPtts(dados.date)
  const uf: string | undefined = dados.ixp?.uf
  const outros = outrosPttsNaUf(dados.code, uf, lista.data?.ixps)
  return (
    <div className="space-y-2 text-sm text-gray-700" data-testid="territorio-ptt">
      {uf && (
        <p>
          UF do PTT: <Link to={`/uf/${uf}`} className="text-primario-700 hover:underline">{uf}</Link>.{' '}
          {outros.length > 0
            ? <>Outros {palavra(outros.length, 'PTT', 'PTTs')} do IX.br nesta UF:{' '}
                {outros.map((o, i) => <span key={o.code}>{i > 0 && ', '}<Link to={`/ixp/${o.code}`} className="text-primario-700 hover:underline">{o.code}</Link> ({o.name})</span>)}.</>
            : lista.data ? 'Não há outro PTT do IX.br nesta UF.' : null}
        </p>
      )}
      <ComoLer titulo="O que é um PTT">
        <p>{O_QUE_E_UM_PTT}</p>
      </ComoLer>
    </div>
  )
}
