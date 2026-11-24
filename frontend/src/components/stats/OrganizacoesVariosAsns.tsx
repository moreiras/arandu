import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AccessError, fetchAsnsPorOrganizacao } from '../../services/api'
import { useOrcamentoAvancado } from '../../auth/AuthContext'
import type { OrganizacaoVariosAsns, AsnsPorOrganizacaoResponse } from '../../types/api'
import { ThOrdenavel } from '../ui/ThOrdenavel'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../ui/EstadoDados'
import { useOrdenacao } from '../../lib/ordenacao'

const SECTION_COLOR = '#0e7490'

function fmtN(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('pt-BR')
}
function fmtPct(n: number | null | undefined): string {
  return n == null ? '—' : `${n.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`
}
function fmtCnpj(c: string): string {
  const d = (c ?? '').replace(/\D/g, '')
  if (d.length !== 14) return c
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

function YesNo({ v }: { v: boolean | null }) {
  if (v == null) return <span className="text-gray-300">—</span>
  return v
    ? <span className="inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-ok-100 text-ok-700">sim</span>
    : <span className="inline-block px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-400">não</span>
}

function LinhaOrganizacao({ group, rank }: { group: OrganizacaoVariosAsns; rank: number }) {
  const [open, setOpen] = useState(false)
  const idDetalhe = useId()
  const { ordenados: asns, props } = useOrdenacao(group.asns, {
    asn: { valor: (a) => a.asn, primeiro: 'asc' },
    nome: (a) => a.name || null,
    usuarios: (a) => a.apnic_users,
    pct_v6: (a) => a.pct_v6,
    v6: (a) => a.rir_prefixes_v6_count,
    v4: (a) => a.rir_prefixes_v4_count,
    rpki: (a) => (a.has_rpki == null ? null : Number(a.has_rpki)),
    aspa: (a) => (a.has_aspa == null ? null : Number(a.has_aspa)),
    ixps: (a) => a.ixps_direct_count || null,
  })
  return (
    <>
      <tr
        onClick={() => setOpen(o => !o)}
        className="hover:bg-tecnico-100 transition-colors cursor-pointer border-t border-gray-100"
      >
        <td className="px-3 py-1.5 text-gray-400 tabular-nums w-8 text-right">{rank}</td>
        <td className="px-3 py-1.5">
          <div className="flex items-center gap-1.5">
            {/* o clique na linha não chega ao teclado: o botão faz o mesmo, com o estado anunciado */}
            <button type="button" aria-expanded={open} aria-controls={open ? idDetalhe : undefined}
              onClick={e => { e.stopPropagation(); setOpen(o => !o) }}
              className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-gray-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500">
              <span aria-hidden="true" className={`inline-block transition-transform ${open ? 'rotate-90' : ''}`}>▸</span>
              <span className="sr-only">{`ASNs de ${group.razao_social || fmtCnpj(group.cnpj)}`}</span>
            </button>
            <div className="min-w-0">
              <div className="font-medium text-gray-900 truncate">{group.razao_social || '—'}</div>
              <div className="text-xs text-gray-400 font-mono">
                <Link to={`/operadora/${group.cnpj}`} className="hover:text-primario-600 hover:underline"
                      onClick={e => e.stopPropagation()}>
                  {fmtCnpj(group.cnpj)}
                </Link>
                {group.uf ? ` · ${group.uf}` : ''}
              </div>
            </div>
          </div>
        </td>
        <td className="px-3 py-1.5 text-right tabular-nums font-semibold" style={{ color: SECTION_COLOR }}>{group.asn_count}</td>
        <td className="px-3 py-1.5 text-right tabular-nums text-gray-700">{fmtN(group.total_apnic_users)}</td>
        <td className="px-3 py-1.5 text-right tabular-nums text-gray-600">{fmtN(group.total_v6_blocks)}</td>
        <td className="px-3 py-1.5 text-right tabular-nums text-gray-600">{fmtN(group.total_v4_blocks)}</td>
      </tr>
      {open && (
        <tr className="bg-gray-50/60" id={idDetalhe}>
          <td />
          <td colSpan={5} className="px-3 py-2">
            <table className="w-full text-xs">
              <caption className="sr-only">{`ASNs de ${group.razao_social || fmtCnpj(group.cnpj)}`}</caption>
              <thead>
                <tr className="text-gray-400">
                  <ThOrdenavel {...props('asn')} className="text-left font-medium py-1 pr-2">ASN</ThOrdenavel>
                  <ThOrdenavel {...props('nome')} className="text-left font-medium py-1 pr-2">Nome</ThOrdenavel>
                  <ThOrdenavel {...props('usuarios')} alinhar="right" className="text-right font-medium py-1 px-2">Usuários</ThOrdenavel>
                  <ThOrdenavel {...props('pct_v6')} alinhar="right" className="text-right font-medium py-1 px-2">%IPv6</ThOrdenavel>
                  <ThOrdenavel {...props('v6')} alinhar="right" className="text-right font-medium py-1 px-2">Blocos v6</ThOrdenavel>
                  <ThOrdenavel {...props('v4')} alinhar="right" className="text-right font-medium py-1 px-2">Blocos v4</ThOrdenavel>
                  <ThOrdenavel {...props('rpki')} alinhar="center" className="text-center font-medium py-1 px-2">RPKI</ThOrdenavel>
                  <ThOrdenavel {...props('aspa')} alinhar="center" className="text-center font-medium py-1 px-2">ASPA</ThOrdenavel>
                  <ThOrdenavel {...props('ixps')} alinhar="right" className="text-right font-medium py-1 pl-2">IXes</ThOrdenavel>
                </tr>
              </thead>
              <tbody>
                {asns.map(a => (
                  <tr key={a.asn} className="border-t border-gray-100">
                    <td className="py-1 pr-2 font-mono whitespace-nowrap">
                      <Link to={`/asn/${a.asn}`} className="text-primario-600 hover:underline" onClick={e => e.stopPropagation()}>
                        AS{a.asn}
                      </Link>
                    </td>
                    <td className="py-1 pr-2 text-gray-700 truncate max-w-[260px]" title={a.name}>{a.name || '—'}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-700">{fmtN(a.apnic_users)}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-600">{fmtPct(a.pct_v6)}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-600">{fmtN(a.rir_prefixes_v6_count)}</td>
                    <td className="py-1 px-2 text-right tabular-nums text-gray-600">{fmtN(a.rir_prefixes_v4_count)}</td>
                    <td className="py-1 px-2 text-center"><YesNo v={a.has_rpki} /></td>
                    <td className="py-1 px-2 text-center"><YesNo v={a.has_aspa} /></td>
                    <td className="py-1 pl-2 text-right tabular-nums text-gray-600">{a.ixps_direct_count || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </td>
        </tr>
      )}
    </>
  )
}

/**
 * Organizações (mesmo CNPJ no Registro.br) com mais de um ASN. Não é grupo econômico: é uma só pessoa jurídica que separa serviços, regiões ou
 * redes incorporadas em ASNs diferentes; grupos de empresas estão em /grupos. Bloco degradável de /ases (rota `metered`): com o orçamento anônimo
 * esgotado não chama a API e avisa. `ancorar`: rola até a seção (redirecionamento da antiga aba "Grupos econômicos" do Panorama de mercado).
 */
export function OrganizacoesVariosAsns({ date, ancorar = false }: { date?: string; ancorar?: boolean }) {
  const { pronto, esgotado } = useOrcamentoAvancado()
  const { data, isError, error } = useQuery<AsnsPorOrganizacaoResponse>({
    queryKey: ['asns-por-organizacao', date],
    queryFn: () => fetchAsnsPorOrganizacao(date, 50),
    enabled: pronto && !esgotado,
    staleTime: 10 * 60 * 1000,
    retry: false,
  })
  const secao = useRef<HTMLElement>(null)
  useEffect(() => { if (ancorar && data) secao.current?.scrollIntoView({ block: 'start' }) }, [ancorar, data])
  const bloqueado = esgotado || (error instanceof AccessError && error.kind === 'limit')
  // Login, taxa ou falha de rede: avisa em vez de sumir (sumir parece "nenhuma organização com vários ASNs").
  const outroErro = !bloqueado && isError && ehErroDeAcessoOuFalha(error) ? error : null

  if (!bloqueado && !outroErro && (isError || !data || data.groups.length === 0)) return null

  return (
    <section ref={secao} id="organizacoes" className="space-y-3 scroll-mt-4" aria-labelledby="organizacoes-titulo">
      <h2 id="organizacoes-titulo" className="text-sm font-semibold uppercase tracking-widest border-t border-gray-100 pt-8" style={{ color: SECTION_COLOR }}>
        Organizações com vários ASNs
      </h2>
      <p className="text-xs text-gray-500">
        Mesmo CNPJ no Registro.br com dois ou mais ASNs; as 50 primeiras por número de ASNs. Os motivos variam (separação de serviços,
        regiões, redes incorporadas) e não indicam grupo econômico: empresas ligadas por sócios ou controle estão
        em <Link to="/grupos" className="text-primario-600 hover:underline">Grupos econômicos</Link>. Clique numa linha para ver os ASNs.
      </p>
      {bloqueado ? (
        <p className="text-sm text-aviso-700 bg-aviso-50 border border-aviso-200 rounded px-3 py-2" role="status">
          Esta lista usa páginas avançadas e o tempo de uso sem login acabou. Entre para ver.
        </p>
      ) : outroErro ? <EstadoDados erro={outroErro} oQue="a lista de organizações" /> : data && (
      <div className="overflow-x-auto lg:overflow-x-clip rounded-lg border border-gray-200 bg-white">
        <table className="w-full table-fixed text-xs min-w-[680px]">
          <caption className="sr-only">Organizações com vários ASNs</caption>
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-gray-500">
              <th scope="col" className="px-3 py-1.5 text-right font-medium w-8">#</th>
              <th scope="col" className="px-3 py-1.5 text-left font-medium">Organização (CNPJ)</th>
              <th scope="col" className="px-3 py-1.5 text-right font-medium w-20">ASNs</th>
              <th scope="col" className="px-3 py-1.5 text-right font-medium w-28">Usuários</th>
              <th scope="col" className="px-3 py-1.5 text-right font-medium w-24">Blocos v6</th>
              <th scope="col" className="px-3 py-1.5 text-right font-medium w-24">Blocos v4</th>
            </tr>
          </thead>
          <tbody>
            {data.groups.map((g, i) => <LinhaOrganizacao key={g.cnpj} group={g} rank={i + 1} />)}
          </tbody>
        </table>
      </div>
      )}
    </section>
  )
}
