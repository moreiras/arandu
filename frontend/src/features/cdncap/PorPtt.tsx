// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { Link } from '../../components/layout/LinkDatado'
import { ComoLer } from '../../components/ui/ComoLer'
import { LinhaProveniencia } from '../../components/ui/Kpi'
import { n0 } from '../../lib/sintese'
import { useActiveDate } from '../../hooks/useSnapshot'
import { fetchIXPs } from '../../services/api'
import type { CDNPresenceResponse } from '../../types/api'
import { pttsPorRegiao } from './pttsPorRegiao'

/**
 * "Por PTT" agrupado por região e UF (PT-22 / cdns 5.2): uma tabela de texto, sem ranking e sem cor de juízo, que responde onde ficam os PTTs sem provedor do
 * catálogo. A UF e os membros vêm da lista de PTTs (`/ixps`, aberta, a mesma chave da página de PTTs). O catálogo é curado e incompleto: zero não é ausência de conteúdo.
 */
export function PorPtt({ data }: { data: CDNPresenceResponse }) {
  const date = useActiveDate()
  const ixps = useQuery({ queryKey: ['ixps', date], queryFn: () => fetchIXPs(date ?? undefined), staleTime: Infinity, gcTime: Infinity, retry: false })
  const grupos = pttsPorRegiao(data, ixps.data?.ixps)
  if (grupos.length === 0) return null
  return (
    <section className="space-y-2" aria-labelledby="por-ptt-titulo" data-testid="cdns-por-ptt">
      <h2 id="por-ptt-titulo" className="text-base font-semibold text-gray-800">Por PTT do IX.br, agrupado por região e UF</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <caption className="sr-only">PTTs do IX.br por região e UF, com o número de ASNs participantes e o número de CDNs e CAPs do catálogo (contadas por empresa, não por ASN) no cadastro, com sessão no route server e só com prefixos vistos por outro participante</caption>
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-600">
              <th scope="col" className="py-1 pr-3 font-medium">UF</th>
              <th scope="col" className="py-1 pr-3 font-medium">PTT</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Participantes (ASNs)</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">CDNs e CAPs no cadastro (empresas)</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Dessas, com route server (empresas)</th>
              <th scope="col" className="py-1 pl-2 text-right font-medium">CDNs e CAPs só com prefixos vistos por outro participante (empresas)</th>
            </tr>
          </thead>
          {grupos.map((g) => (
            <tbody key={g.id} data-testid="cdns-por-ptt-grupo">
              <tr className="bg-gray-50">
                <th scope="rowgroup" colSpan={6} className="py-1 px-2 text-left text-xs font-semibold text-gray-700">
                  {g.nome}
                  {g.ufsSemCdn.length > 0 && <span className="ml-2 font-normal text-gray-600">UFs da região sem CDN ou CAP do catálogo em PTT local: {g.ufsSemCdn.join(', ')}</span>}
                </th>
              </tr>
              {g.ptts.map((p, i) => (
                  <tr key={p.code} className="border-b border-gray-100 text-gray-700">
                    <td className="py-1 pr-3">{i === 0 || g.ptts[i - 1].uf !== p.uf ? (p.uf ?? '—') : ''}</td>
                    <th scope="row" className="py-1 pr-3 text-left font-normal"><Link to={`/ixp/${p.code}`} className="text-primario-700 hover:underline">{p.nome}</Link></th>
                    <td className="py-1 px-2 text-right">{p.membros == null ? '—' : n0(p.membros)}</td>
                    <td className="py-1 px-2 text-right">{n0(p.cdnsMembro)}</td>
                    <td className="py-1 px-2 text-right">{n0(p.comRouteServer)}</td>
                    <td className="py-1 pl-2 text-right">{n0(p.soViaOutroAs)}</td>
                  </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <ComoLer>
        <p>Participantes é o número de ASNs do cadastro do PTT no IX.br. As CDNs e CAPs (redes de distribuição e grandes provedores de conteúdo) vêm de um catálogo mantido pelo projeto e incompleto, com classificação editorial do projeto. Cada uma é contada como uma empresa, mesmo quando tem vários ASNs: basta um deles no cadastro para contar, e por isso essas colunas não se comparam diretamente com a de participantes. Zero quer dizer nenhuma CDN ou CAP deste catálogo, não ausência de conteúdo no PTT.</p>
        <p>“Só prefixos vistos por outro participante” conta CDNs e CAPs do catálogo que não são participantes, mas cujos prefixos aparecem nas rotas do PTT; é inferência e não diz onde está o servidor nem quanto tráfego passa. A ordem é a da região do IBGE, da UF e do código do PTT, sem ranking.</p>
      </ComoLer>
      <LinhaProveniencia selo="inferido" fonte="catálogo curado do projeto, cadastro de participantes e looking glasses do IX.br" dataRef={data.snapshot_date} />
    </section>
  )
}
