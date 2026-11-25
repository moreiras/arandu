// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchCDNPresence } from '../../../services/api'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'

const slug = (nome: string) => nome.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

/**
 * Conteúdo no PTT: quais CDNs e provedores de conteúdo constam como membros deste PTT e se o ASN deles tem sessão com o route server (IPv6 e IPv4).
 * A presença vem da lista de membros do IX.br cruzada com a matriz de CDNs; a sessão com o route server vem das rotas coletadas. Sessões bilaterais
 * não são observáveis aqui, e estar na lista não diz quanto tráfego a CDN entrega ali.
 */
export function ConteudoBloco({ dados }: BlocoProps<PttCtx>) {
  const { code, date, mergedV4, mergedV6 } = dados
  const q = useQuery({ queryKey: ['cdn-presence', date], queryFn: () => fetchCDNPresence(date ?? undefined), staleTime: 10 * 60 * 1000 })
  const diretosV4 = new Set(mergedV4?.asn_direct ?? [])
  const diretosV6 = new Set(mergedV6?.asn_direct ?? [])
  const aqui = (q.data?.cdns ?? []).filter((c) => c.ixbr.includes(code))
  const { ordenados, props } = useOrdenacao(aqui, {
    cdn: (c) => c.name,
    diretos: (c) => new Set(c.asns.filter((a) => diretosV4.has(a) || diretosV6.has(a))).size,
    outros: (c) => c.ixbr_count - 1,
  })
  if (q.isLoading) return <div className="h-20 bg-gray-50 rounded animate-pulse" />
  if (aqui.length === 0) return <p className="text-sm text-gray-500">Nenhuma CDN da matriz consta como membro deste PTT no snapshot.</p>
  return (
    <div className="space-y-2" data-testid="conteudo-ptt">
      <p className="text-sm text-gray-600">{aqui.length} CDN{aqui.length === 1 ? '' : 's'}/provedores de conteúdo membros deste PTT pela lista do IX.br (de {q.data!.cdns.length} na matriz).</p>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><ThOrdenavel {...props('cdn')} className="py-1 pr-3 font-medium">CDN</ThOrdenavel><ThOrdenavel {...props('diretos')} className="py-1 pr-3 font-medium">ASNs com sessão no route server aqui</ThOrdenavel><ThOrdenavel {...props('outros')} className="py-1 pr-3 font-medium">Outros PTTs do IX.br</ThOrdenavel></tr></thead>
          <tbody>
            {ordenados.map((c) => {
              const v4 = c.asns.filter((a) => diretosV4.has(a)); const v6 = c.asns.filter((a) => diretosV6.has(a))
              return (
                <tr key={c.name} className="border-b border-gray-100">
                  <td className="py-1.5 pr-3"><Link to={`/cdncap/${slug(c.name)}`} className="text-primario-700 hover:underline">{c.name}</Link></td>
                  <td className="py-1.5 pr-3 text-xs text-gray-600">
                    {v4.length || v6.length ? <>
                      {v6.length > 0 && <span>IPv6: {v6.map((a) => 'AS' + a).join(', ')}</span>}{v4.length > 0 && v6.length > 0 && ' · '}
                      {v4.length > 0 && <span>IPv4: {v4.map((a) => 'AS' + a).join(', ')}</span>}
                    </> : 'membro sem sessão no route server nas rotas coletadas'}
                  </td>
                  <td className="py-1.5 pr-3 text-xs text-gray-500 tabular-nums">{c.ixbr_count - 1}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
