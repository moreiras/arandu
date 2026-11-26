// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../layout/LinkDatado'
import type { BgpStabilityCarga, CargaFamilia, CargaSemana } from '../../types/bgpStability'
import { Tip } from './BgpShared'
import { palavra } from '../../lib/sintese'

// Cinco faixas em escala logarítmica do maior valor da grade. O número está sempre escrito na célula: a cor só reforça.
// Texto escuro nas três claras e branco nas duas escuras, todos com contraste ≥ 4,5:1.
const FAIXAS = [
  { fundo: '#eff6ff', texto: '#1f2937' },
  { fundo: '#bfdbfe', texto: '#1f2937' },
  { fundo: '#60a5fa', texto: '#111827' },
  { fundo: '#2563eb', texto: '#ffffff' },
  { fundo: '#1e3a8a', texto: '#ffffff' },
]

const compacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })
const inteiro = (v: number) => v.toLocaleString('pt-BR')
const pct = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + '%')
const diaMes = (iso: string | null) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}` : '?')

/** Faixa de cor (0..4) de `v` na escala log de 0 a `max`; null para zero (célula sem cor). */
export function faixaCarga(v: number, max: number): number | null {
  if (v <= 0 || max <= 0) return null
  const t = Math.log10(v + 1) / Math.log10(max + 1)
  return Math.min(FAIXAS.length - 1, Math.floor(t * FAIXAS.length))
}

/** A semana precisa de nota: janela sobreposta à anterior, dias de fora ou arquivos do coletor faltando. */
function avisoSemana(s: CargaSemana): string | null {
  const partes = []
  if (s.sobreposicao_dias > 0) partes.push(`${s.sobreposicao_dias} ${palavra(s.sobreposicao_dias, 'dia', 'dias')} em comum com a semana anterior`)
  if (s.lacuna_dias > 0) partes.push(`${s.lacuna_dias} ${palavra(s.lacuna_dias, 'dia', 'dias')} sem cobertura antes desta semana`)
  if ((s.arquivos_faltando ?? 0) > 0) partes.push(`${s.arquivos_faltando} ${palavra(s.arquivos_faltando, 'arquivo do coletor faltando', 'arquivos do coletor faltando')} (volume subcontado)`)
  return partes.length ? partes.join('; ') : null
}

function Grade({ rotulo, fam, semanas }: { rotulo: string; fam: CargaFamilia; semanas: CargaSemana[] }) {
  if (!fam.ases.length) return <p className="text-xs text-gray-500">Nenhum update {rotulo} visto no período.</p>
  const max = Math.max(...fam.ases.flatMap((a) => a.semanas))
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold text-gray-700">{rotulo}</h4>
      <div className="overflow-x-auto">
        <table className="text-xs border-collapse min-w-full" data-tabela="grade" aria-label={`Updates ${rotulo} por semana dos ${fam.ases.length} ASes com mais updates no período`}>
          <thead>
            <tr className="text-gray-500 border-b border-gray-200">
              <th scope="col" className="py-1 pr-2 text-left font-medium sticky left-0 bg-white">AS</th>
              {semanas.map((s) => {
                const aviso = avisoSemana(s)
                return (
                  <th key={s.date} scope="col" className="px-1 py-1 text-center font-medium whitespace-nowrap" title={aviso ?? undefined}>
                    {diaMes(s.inicio)} a {diaMes(s.ultimo_dia)}{aviso && <span aria-label={`: ${aviso}`}>*</span>}
                  </th>
                )
              })}
              <th scope="col" className="px-2 py-1 text-right font-medium">Total</th>
              <th scope="col" className="px-2 py-1 text-right font-medium whitespace-nowrap">Prefixos<span className="sr-only"> com update, máximo semanal</span></th>
            </tr>
          </thead>
          <tbody>
            {fam.ases.map((a) => (
              <tr key={a.asn} className="border-t border-gray-100">
                <th scope="row" className="py-1 pr-2 text-left font-normal sticky left-0 bg-white max-w-[14rem]">
                  <Link to={`/asn/${a.asn}`} className="font-mono text-primario-700 hover:underline">AS{a.asn}</Link>
                  {a.nome && <span className="text-gray-600 truncate block">{a.nome}</span>}
                </th>
                {a.semanas.map((v, i) => {
                  const f = faixaCarga(v, max)
                  const cor = f == null ? undefined : FAIXAS[f]
                  return (
                    <td key={semanas[i]?.date ?? i} className="px-1 py-1 text-center tabular-nums whitespace-nowrap"
                      style={cor ? { background: cor.fundo, color: cor.texto } : { color: '#6b7280' }}
                      title={`${inteiro(v)} updates · ${inteiro(a.prefixos[i] ?? 0)} prefixos com update`}>
                      {v > 0 ? compacto.format(v) : '0'}
                    </td>
                  )
                })}
                <td className="px-2 py-1 text-right tabular-nums font-medium" title={`${inteiro(a.total)} updates`}>{compacto.format(a.total)}</td>
                <td className="px-2 py-1 text-right tabular-nums text-gray-600">{inteiro(Math.max(0, ...a.prefixos))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-gray-200 text-gray-600">
              <th scope="row" className="py-1 pr-2 text-left font-normal sticky left-0 bg-white">Parcela dos {fam.ases.length} no total</th>
              {fam.parcela_top_semana_pct.map((p, i) => <td key={semanas[i]?.date ?? i} className="px-1 py-1 text-center tabular-nums">{pct(p)}</td>)}
              <td className="px-2 py-1 text-right tabular-nums font-medium">{pct(fam.parcela_top_pct)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

/** Grade AS × semana dos ASes com mais updates BGP no período do gráfico de atividade, uma por família (IPv6 antes de IPv4). */
export function CargaBgpSemanas({ data }: { data: BgpStabilityCarga }) {
  const avisos = data.semanas.map((s) => ({ s, aviso: avisoSemana(s) })).filter((x) => x.aviso)
  return (
    <div className="space-y-3" data-testid="carga-bgp">
      <h3 className="text-sm font-semibold text-gray-700">
        ASes com mais updates BGP nas últimas {data.semanas.length} semanas
        <Tip text="Volume absoluto: anúncios + retiradas + mudanças de atributo de cada AS, somados nas semanas do gráfico de atividade, em separado por família. É a carga que o AS colocou na tabela. A tabela abaixo usa outra métrica, updates por prefixo por dia, que favorece ASes pequenos; aqui pesam os grandes." />
      </h3>
      <Grade rotulo="IPv6" fam={data.v6} semanas={data.semanas} />
      <Grade rotulo="IPv4" fam={data.v4} semanas={data.semanas} />
      <p className="text-xs text-gray-500">
        Os {data.top} ASes brasileiros com a maior soma de updates no período, por família; cada coluna é uma semana (janela de 7 dias de um
        snapshot). Linha cheia indica volume constante; célula isolada, um pico. Cor em escala logarítmica do maior valor da grade; o valor
        exato aparece ao passar o ponteiro. Semana sem update visto conta 0. Visto pelo coletor {data.coletor ?? '—'}; medido, não indica causa.
        Snapshot {data.snapshot_date}.
      </p>
      {avisos.length > 0 && (
        <ul className="text-xs text-gray-500 list-none">
          {avisos.map(({ s, aviso }) => <li key={s.date}>* {diaMes(s.inicio)} a {diaMes(s.ultimo_dia)}: {aviso}.</li>)}
        </ul>
      )}
    </div>
  )
}
