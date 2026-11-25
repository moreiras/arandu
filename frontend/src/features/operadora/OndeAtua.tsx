// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useMemo, useState } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { HhiLocal } from '../../components/ui/HhiLocal'
import { LinhaProveniencia } from '../../components/ui/Kpi'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../lib/ordenacao'
import { NOTA_FAIXAS_HHI } from '../../lib/referencias'
import { comMaisDaMetade, comUmSoDeclarante, resumoPorUf, semAcento, type MunicipioOperadora } from './resumoOndeAtua'

const POR_PAGINA = 100
const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

/**
 * "Onde atua" da operadora (PT-23): resumo por UF e tabela de todos os municípios com acessos, parcela no município, número de declarantes e HHI local. Tudo sobre acessos fixos
 * declarados ao SICI no mês de referência (que não é a data do snapshot); a sede do CNPJ não diz onde estão os clientes. A tabela é também a alternativa textual do mapa.
 * Os municípios vêm todos no documento: filtro, busca, ordem e página são do navegador, e nenhuma linha é suprimida.
 */
export function OndeAtua({ municipios, mesReferencia, snapshot }: { municipios: readonly MunicipioOperadora[]; mesReferencia?: string | null; snapshot?: string | null }) {
  const [uf, setUf] = useState('')
  const [busca, setBusca] = useState('')
  const [pagina, setPagina] = useState(1)
  const porUf = useMemo(() => resumoPorUf(municipios), [municipios])
  const filtrados = useMemo(() => {
    const alvo = semAcento(busca.trim())
    return municipios.filter((m) => (!uf || m.uf === uf) && (!alvo || semAcento(m.nome).includes(alvo)))
  }, [municipios, uf, busca])
  const { ordenados, props } = useOrdenacao(filtrados, {
    nome: (m) => m.nome, uf: (m) => m.uf, acessos: (m) => m.acessos, pf: (m) => m.pf, pj: (m) => m.pj,
    share: (m) => m.share, operadores: (m) => m.municipio_operadores, hhi: (m) => m.municipio_hhi,
  })
  if (municipios.length === 0) return null
  const quando = `SICI ${mesReferencia ?? 'mês de referência não informado'}${snapshot ? ` · snapshot ${snapshot}` : ''}`
  const paginas = Math.max(1, Math.ceil(ordenados.length / POR_PAGINA))
  const p = Math.min(pagina, paginas)
  const ini = (p - 1) * POR_PAGINA
  const total = municipios.reduce((s, m) => s + m.acessos, 0)

  if (municipios.length === 1) {
    const m = municipios[0]
    return (
      <section aria-labelledby="onde-atua-t" className="bg-white rounded-lg border border-gray-200 p-4 space-y-2" data-testid="onde-atua">
        <h3 id="onde-atua-t" className="text-sm font-semibold text-gray-700">Onde atua ({quando})</h3>
        <p className="text-sm text-gray-700">
          Declara acessos em um município: <Link to={`/municipio/${m.ibge}`} className="text-primario-700 underline">{m.nome}/{m.uf}</Link>, com {n(m.acessos)} acessos
          {m.share != null && <> ({pct(m.share)} dos acessos declarados no município, {n(m.municipio_operadores)} {m.municipio_operadores === 1 ? 'declarante' : 'declarantes'}, HHI local {n(m.municipio_hhi)})</>}.
        </p>
        <LinhaProveniencia selo="fato" fonte="Anatel (SICI), acessos declarados por município" dataRef={mesReferencia} />
      </section>
    )
  }

  return (
    <section aria-labelledby="onde-atua-t" className="bg-white rounded-lg border border-gray-200 p-4 space-y-4" data-testid="onde-atua">
      <div>
        <h3 id="onde-atua-t" className="text-sm font-semibold text-gray-700">Onde atua ({quando})</h3>
        <p className="mt-1 text-sm text-gray-700">
          Declara acessos em <strong>{n(municipios.length)}</strong> municípios de <strong>{n(porUf.length)}</strong> {porUf.length === 1 ? 'UF' : 'UFs'}. Em <strong>{n(comMaisDaMetade(municipios))}</strong> deles tem mais da metade dos acessos declarados
          no município e em <strong>{n(comUmSoDeclarante(municipios))}</strong> é a única declarante.
        </p>
        <LinhaProveniencia selo="fato" fonte="Anatel (SICI), acessos declarados por município" dataRef={mesReferencia} />
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm" data-testid="onde-atua-uf">
          <caption className="text-left text-xs font-semibold text-gray-700 pb-1">Acessos declarados por UF</caption>
          <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200">
            <th scope="col" className="py-1 pr-3 font-medium">UF</th>
            <th scope="col" className="py-1 pr-3 text-right font-medium">Municípios</th>
            <th scope="col" className="py-1 pr-3 text-right font-medium">Acessos</th>
            <th scope="col" className="py-1 pr-3 text-right font-medium">% da operadora</th>
            <th scope="col" className="py-1 pr-3 text-right font-medium">B2C</th>
            <th scope="col" className="py-1 text-right font-medium">B2B</th>
          </tr></thead>
          <tbody>
            {porUf.map((u) => (
              <tr key={u.uf} className="border-b border-gray-100 hover:bg-gray-50">
                <th scope="row" className="py-1 pr-3 text-left font-normal"><Link to={`/uf/${u.uf}`} className="text-primario-700 underline">{u.uf}</Link></th>
                <td className="py-1 pr-3 text-right tabular-nums">{n(u.municipios)}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{n(u.acessos)}</td>
                <td className="py-1 pr-3 text-right tabular-nums">
                  {pct(u.pct)}
                  <span aria-hidden="true" className="ml-2 inline-block h-1.5 rounded bg-primario-400 align-middle" style={{ width: `${Math.max(2, Math.round((u.pct ?? 0) * 0.8))}px` }} />
                </td>
                <td className="py-1 pr-3 text-right tabular-nums text-gray-600">{n(u.pf)}</td>
                <td className="py-1 text-right tabular-nums text-gray-600">{n(u.pj)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr className="text-xs text-gray-600"><th scope="row" className="pt-1 pr-3 text-left font-medium">Total</th><td className="pt-1 pr-3 text-right tabular-nums">{n(municipios.length)}</td><td className="pt-1 pr-3 text-right tabular-nums">{n(total)}</td><td colSpan={3} /></tr></tfoot>
        </table>
      </div>

      <div>
        <div className="flex flex-wrap items-end gap-3 text-xs text-gray-600 mb-2">
          <label className="flex flex-col">UF
            <select value={uf} onChange={(e) => { setUf(e.target.value); setPagina(1) }} className="border border-gray-300 rounded px-2 py-1 text-sm min-h-[24px]">
              <option value="">todas</option>{porUf.map((u) => <option key={u.uf} value={u.uf}>{u.uf}</option>)}
            </select>
          </label>
          <label className="flex flex-col">Buscar município
            <input type="search" value={busca} onChange={(e) => { setBusca(e.target.value); setPagina(1) }} className="border border-gray-300 rounded px-2 py-1 text-sm w-56 min-h-[24px]" placeholder="parte do nome" />
          </label>
        </div>
        <p className="text-xs text-gray-600 mb-1" role="status" aria-live="polite">
          {ordenados.length === 0 ? 'Nenhum município com estes filtros.' : `Mostrando ${n(ini + 1)} a ${n(Math.min(ini + POR_PAGINA, ordenados.length))} de ${n(ordenados.length)} municípios.`}
        </p>
        <div className="max-h-[32rem] overflow-auto border border-gray-100 rounded">
          <table className="min-w-full text-sm">
            <caption className="sr-only">Municípios com acessos fixos declarados pela operadora, com a parcela dela nos acessos do município, o número de empresas declarantes e o HHI local. Ordem inicial: acessos da operadora, do maior para o menor.</caption>
            <thead className="sticky top-0 bg-gray-50">
              <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                <ThOrdenavel {...props('nome')} className="px-3 py-1.5 font-medium">Município</ThOrdenavel>
                <ThOrdenavel {...props('uf')} className="px-3 py-1.5 font-medium w-14">UF</ThOrdenavel>
                <ThOrdenavel {...props('acessos')} alinhar="right" className="px-3 py-1.5 font-medium text-right">Acessos</ThOrdenavel>
                <ThOrdenavel {...props('pf')} alinhar="right" className="px-3 py-1.5 font-medium text-right">B2C</ThOrdenavel>
                <ThOrdenavel {...props('pj')} alinhar="right" className="px-3 py-1.5 font-medium text-right">B2B</ThOrdenavel>
                <ThOrdenavel {...props('share')} alinhar="right" className="px-3 py-1.5 font-medium text-right">Parcela no município</ThOrdenavel>
                <ThOrdenavel {...props('operadores')} alinhar="right" className="px-3 py-1.5 font-medium text-right">Operadoras no município</ThOrdenavel>
                <ThOrdenavel {...props('hhi')} alinhar="right" className="px-3 py-1.5 font-medium text-right">HHI local</ThOrdenavel>
              </tr>
            </thead>
            <tbody>
              {ordenados.slice(ini, ini + POR_PAGINA).map((m) => (
                <tr key={m.ibge} className="border-b border-gray-100 hover:bg-gray-50 align-top">
                  <th scope="row" className="px-3 py-1 text-left font-normal"><Link to={`/municipio/${m.ibge}`} className="text-primario-700 underline">{m.nome}</Link></th>
                  <td className="px-3 py-1 text-gray-600">{m.uf}</td>
                  <td className="px-3 py-1 text-right tabular-nums">{n(m.acessos)}</td>
                  <td className="px-3 py-1 text-right tabular-nums text-gray-600">{n(m.pf)}</td>
                  <td className="px-3 py-1 text-right tabular-nums text-gray-600">{n(m.pj)}</td>
                  <td className="px-3 py-1 text-right tabular-nums">{pct(m.share)}</td>
                  <td className="px-3 py-1 text-right tabular-nums">{n(m.municipio_operadores)}</td>
                  <td className="px-3 py-1 text-right"><HhiLocal valor={m.municipio_hhi} avisos={m.avisos_hhi} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {paginas > 1 && (
          <nav aria-label="Páginas da tabela de municípios" className="mt-2 flex items-center gap-3 text-sm">
            <button type="button" disabled={p <= 1} onClick={() => setPagina(p - 1)} className="min-h-[24px] min-w-[24px] px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Anterior</button>
            <span className="text-xs text-gray-600">página {n(p)} de {n(paginas)}</span>
            <button type="button" disabled={p >= paginas} onClick={() => setPagina(p + 1)} className="min-h-[24px] min-w-[24px] px-2 py-1 border border-gray-300 rounded disabled:opacity-40">Próxima</button>
          </nav>
        )}
      </div>

      <div className="space-y-1 text-xs text-gray-600">
        <p><b>Como ler.</b> Acessos fixos declarados pela empresa ao SICI no mês {mesReferencia ?? 'de referência'}. A sede do CNPJ não indica onde estão os clientes. Parcela no município: acessos desta operadora ÷ acessos declarados por todas as operadoras no município. HHI local: soma do quadrado da parcela de cada declarante (0 a 10.000), por CNPJ. Parcela e HHI medem acessos declarados, não domicílios nem receita; município com poucos acessos pode refletir declaração pontual, e parcela alta num município pequeno não indica o tamanho da operação. Operadora de satélite declara em quase todos os municípios.</p>
        <p>{NOTA_FAIXAS_HHI}</p>
      </div>
    </section>
  )
}
