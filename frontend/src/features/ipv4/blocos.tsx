// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchIpv4Asn, fetchIpv4Espaco, fetchIpv4UsoPorTerceiros } from '../../services/api'
import type { BlocoProps } from '../entidade/registry'
import type { AsnCtx } from '../asn/contexto'
import type { OperadoraCtx } from '../operadora/contexto'
import type { Ipv4EspacoLinha, Ipv4UsoItem } from '../../types/api'
import { useOrdenacao } from '../../lib/ordenacao'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'

export const CLASSES_ESPACO: Record<string, string> = { nao_anunciado: 'não anunciado', roa_sem_anuncio: 'ROA sem anúncio', parcial: 'anunciado em parte', em_recuperacao: 'em recuperação' }
const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const AVISO = 'Não anunciado não é sem uso (rede interna, enlace, reserva técnica e CGNAT não aparecem na tabela global). Sinal de terceiros é hipótese, com falsos positivos conhecidos: o caso comum é o provedor que anuncia o bloco do cliente.'

/** `ordenavel` só quando a lista está inteira no navegador: com a página da API (total maior que os itens), reordenar o recorte esconderia
 * quem lidera a coluna, e `/ipv4/espaco` ainda não aceita ordem. */
function ListaEspaco({ itens, ordenavel = true }: { itens: Ipv4EspacoLinha[]; ordenavel?: boolean }) {
  const { ordenados, props } = useOrdenacao(itens, {
    bloco: { valor: (b) => b.inicio, primeiro: 'asc' }, quantidade: (b) => b.quantidade, classe: (b) => CLASSES_ESPACO[b.classe] ?? b.classe,
    anunciado: (b) => b.anunciado_pct, sem_anuncio: (b) => b.tabelas_sem_anuncio || null,
  })
  if (itens.length === 0) return null
  const th = (campo: Parameters<typeof props>[0]) => (ordenavel ? props(campo) : { campo, ordem: null })
  return (
    <table className="text-xs min-w-full">
      <thead className="text-gray-500"><tr><ThOrdenavel {...th('bloco')} className="text-left px-2 py-1">Bloco</ThOrdenavel><ThOrdenavel {...th('quantidade')} alinhar="right" className="text-right px-2 py-1">Endereços</ThOrdenavel><ThOrdenavel {...th('classe')} className="text-left px-2 py-1">Situação</ThOrdenavel><ThOrdenavel {...th('anunciado')} alinhar="right" className="text-right px-2 py-1">Anunciado</ThOrdenavel><ThOrdenavel {...th('sem_anuncio')} className="text-left px-2 py-1">Sem anúncio</ThOrdenavel></tr></thead>
      <tbody>
        {(ordenavel ? ordenados : itens).map((b) => (
          <tr key={b.inicio} className="border-t border-gray-100">
            <td className="px-2 py-1"><Link to={`/prefixo/${encodeURIComponent(`${b.inicio}/${32 - Math.ceil(Math.log2(b.quantidade))}`)}`} className="text-primario-600 hover:underline">{b.inicio}</Link></td>
            <td className="px-2 py-1 text-right tabular-nums">{inteiro(b.quantidade)}</td><td className="px-2 py-1">{CLASSES_ESPACO[b.classe] ?? b.classe}</td>
            <td className="px-2 py-1 text-right tabular-nums">{b.anunciado_pct.toLocaleString('pt-BR')}%</td>
            <td className="px-2 py-1 text-gray-500">{b.tabelas_sem_anuncio ? `${b.tabelas_sem_anuncio} tabela${b.tabelas_sem_anuncio > 1 ? 's' : ''} de origem (desde ${b.sem_anuncio_desde})` : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ListaSinais({ itens }: { itens: Ipv4UsoItem[] }) {
  if (itens.length === 0) return null
  return (
    <ul className="text-xs divide-y divide-gray-50">
      {itens.map((i) => (
        <li key={i.inicio} className="py-1.5">
          <span className="font-medium">{i.inicio}</span> <span className="text-gray-500">({inteiro(i.quantidade)} endereços)</span> · hipótese de uso por terceiros, confiança <strong>{i.confianca}</strong>
          <ul className="text-gray-600 list-disc ml-5">{i.sinais.map((s) => <li key={s.id}><span className="font-medium">{s.id}</span> {s.evidencia}</li>)}</ul>
        </li>
      ))}
    </ul>
  )
}

/** Recursos IPv4 do ASN: blocos, os não plenamente anunciados e os sinais de uso por terceiros, como titular e como origem de bloco alheio. */
export function RecursosIpv4AsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const q = useQuery({ queryKey: ['ipv4-asn', dados.doc.asn], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4Asn(dados.doc.asn) })
  const r = q.data
  if (!r) return null
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-700">{inteiro(r.blocos)} blocos IPv4 alocados ao ASN ({inteiro(r.enderecos)} endereços). {r.nao_plenamente_anunciados.length > 0 && `${r.nao_plenamente_anunciados.length} não estão plenamente anunciados.`}</p>
      <ListaEspaco itens={r.nao_plenamente_anunciados} />
      {r.sinais_como_titular.length > 0 && <div><h3 className="text-sm font-medium text-gray-800">Blocos do ASN com sinais de uso por terceiros</h3><ListaSinais itens={r.sinais_como_titular} /></div>}
      {r.sinais_como_origem.length > 0 && <div><h3 className="text-sm font-medium text-gray-800">Blocos de outro titular que o ASN anuncia</h3><ListaSinais itens={r.sinais_como_origem} /></div>}
      <p className="text-xs text-gray-500">{r.aviso} <Link to="/mercado-ipv4?aba=espaco" className="text-primario-600 hover:underline">Mercado de IPv4</Link>.</p>
    </div>
  )
}

/** Recursos IPv4 da operadora: blocos não plenamente anunciados e sinais de terceiros dos ASNs do CNPJ. */
export function RecursosIpv4OperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const cnpj = dados.cnpjFinal
  const e = useQuery({ queryKey: ['ipv4-espaco-cnpj', cnpj], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4Espaco({ cnpj, limit: 25 }) })
  const u = useQuery({ queryKey: ['ipv4-uso-cnpj', cnpj], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4UsoPorTerceiros({ cnpj, limit: 25 }) })
  if (!e.data && !u.data) return null
  const nE = e.data?.total ?? 0
  const nU = u.data?.total ?? 0
  if (nE === 0 && nU === 0) return null
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-700">{inteiro(nE)} blocos não plenamente anunciados · {inteiro(nU)} blocos com sinais de uso por terceiros.</p>
      <ListaEspaco itens={e.data?.items ?? []} ordenavel={(e.data?.items.length ?? 0) >= nE} />
      <ListaSinais itens={u.data?.items ?? []} />
      <p className="text-xs text-gray-500">{AVISO} <Link to="/mercado-ipv4?aba=espaco" className="text-primario-600 hover:underline">Mercado de IPv4</Link>.</p>
    </div>
  )
}
