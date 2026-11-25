// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** HTML dos balões (popups) do mapa: funções puras de propriedades da feição → string (testadas em popups.test.ts). */
import { escapar } from '../../../lib/html'
import { MAP_COLORS } from '../mapTheme'
import { colorValueLabel } from './estilo'
import { COLOR_SCM } from './tipos'

type Props = Record<string, unknown>

// Tooltips — mesma convenção do Localizador (CNPJ ciano monospace + badge SCM).
const CNPJ_COLOR = MAP_COLORS.cnpj
const SCM_BADGE = `<span style="background:${COLOR_SCM};color:white;font-size:10px;padding:0 5px;border-radius:9999px">SCM</span>`

export function formatCnpj(cnpj: string): string {
  const d = cnpj.replace(/\D/g, '')
  if (d.length !== 14) return cnpj
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

export function cnpjLine(cnpj?: string | null): string {
  return cnpj
    ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(cnpj))}</a><br/>`
    : ''
}

const lerLista = (v: unknown): number[] => {
  if (v == null) return []
  try { return JSON.parse(v as string) } catch { return [] }
}

export function htmlPix(p: Props): string {
  return `<strong>PIX ${escapar(p.ixp_name ?? p.ixp_code ?? '')}</strong>` +
    (p.name ? `<br/><span style="font-size:.88em;color:#555">${escapar(p.name)}</span>` : '')
}

export function htmlAsn(p: Props, colorBy: string): string {
  const loc = [p.city, p.uf].filter(Boolean).join('/')
  const name = (p.name as string) || ''
  const razao = p.razao_social as string | undefined
  const fantasia = p.nome_fantasia as string | undefined
  const cnpj = p.cnpj as string | undefined
  const badge = p.has_scm ? ` ${SCM_BADGE}` : ''
  const cvLabel = colorValueLabel(p.color_value, colorBy)
  return `<strong>AS${escapar(p.asn)}</strong>${badge}${loc ? ` · ${escapar(loc)}` : ''}<br/>` +
    (name ? `<span style="font-size:.88em;color:#555">${escapar(name)}</span><br/>` : '') +
    cnpjLine(cnpj) +
    (razao && razao !== name ? `<span style="font-size:.78em;color:#9ca3af">Anatel: ${escapar(razao)}</span><br/>` : '') +
    (fantasia && fantasia !== name && fantasia !== razao ? `<span style="font-size:.78em;color:#9ca3af">fantasia: ${escapar(fantasia)}</span><br/>` : '') +
    (cvLabel ? `<span style="font-size:.82em;color:#777">${escapar(cvLabel)}</span>` : '')
}

export function htmlPrefixo(p: Props): string {
  const loc = [p.city, p.uf, p.country].filter(Boolean).join(' / ')
  const MAX_SHOW = 6
  let originAsns: number[] = []
  // BR prefixes: single origin_asn; PTT prefixes: origin_asns array (JSON string from MapLibre)
  if (p.origin_asn != null) originAsns = [p.origin_asn as number]
  if (p.origin_asns != null) { try { originAsns = JSON.parse(p.origin_asns as string) } catch { /* noop */ } }
  const peerAsns = lerLista(p.peer_asns)

  const fmtAsns = (asns: number[]) =>
    asns.slice(0, MAX_SHOW).map(a => `AS${a}`).join(', ') +
    (asns.length > MAX_SHOW ? ` +${asns.length - MAX_SHOW}` : '')

  // Origem única: mostra AS + nome + CNPJ (backend só envia cnpj/nome com origem única).
  const originName = p.origin_name as string | undefined
  const originHtml = originAsns.length === 1
    ? `AS${originAsns[0]}${originName ? ` · ${originName}` : ''}`
    : fmtAsns(originAsns)

  const head = (p.prefix_count ? `<strong>${escapar(p.prefix_count)} ${escapar(Number(p.prefix_count) === 1 ? 'prefixo' : 'prefixos')}</strong>` : `<strong>${escapar(p.block_count)} blocos</strong>`)
    + (loc ? ` · ${escapar(loc)}` : '')
  const lines = [head]
  if (originAsns.length) lines.push(`<span style="font-size:.82em;color:#555"><b>Origem:</b> ${escapar(originHtml)}</span>`)
  const cnpj = p.origin_cnpj as string | undefined
  if (cnpj) lines.push(`<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace;font-size:.82em">${escapar(formatCnpj(cnpj))}</a>`)
  if (peerAsns.length) lines.push(`<span style="font-size:.82em;color:#777"><b>Peers PTT:</b> ${escapar(fmtAsns(peerAsns))}</span>`)
  return lines.join('<br/>')
}

export function htmlScm(p: Props): string {
  const loc = [p.municipio, p.uf].filter(Boolean).join('/')
  const razao = (p.razao_social as string) || ''
  const fantasia = p.nome_fantasia as string | undefined
  const cnpj = p.cnpj as string | undefined
  const asns = lerLista(p.asns)
  const lines = [`<strong>${escapar(razao)}</strong> ${SCM_BADGE}${loc ? ` · ${escapar(loc)}` : ''}`]
  if (cnpj) lines.push(`<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(cnpj))}</a>`)
  if (fantasia && fantasia !== 'N/I' && fantasia !== razao)
    lines.push(`<span style="font-size:.78em;color:#9ca3af">fantasia: ${escapar(fantasia)}</span>`)
  lines.push(asns.length
    ? `<span style="font-size:.82em;color:#555">${asns.map(a => `AS${escapar(a)}`).join(', ')}</span>`
    : `<span style="font-size:.78em;color:#9ca3af">Outorga SCM sem ASN no BGP</span>`)
  const sici = linhaSici(p)
  if (sici) lines.push(sici)
  return lines.join('<br/>')
}

/**
 * Declaração de acessos da outorga (PT-26, mapa 5.4): só o fato e o mês de referência, sem adjetivo. O mês do SICI difere da data do snapshot.
 * Os campos `sici_*` vêm da camada; sem eles (snapshot antigo) nada é afirmado.
 */
export function linhaSici(p: Props): string {
  if (p.sici_ativo === undefined) return ''
  const mes = typeof p.sici_mes_referencia === 'string' && p.sici_mes_referencia ? p.sici_mes_referencia : ''
  const fmt = (v: unknown) => Number(v ?? 0).toLocaleString('pt-BR')
  let texto: string
  if (p.sici_ativo === true || p.sici_ativo === 'true') {
    const partes = [`${fmt(p.sici_acessos)} acessos (pessoa física ${fmt(p.sici_pf)}, jurídica ${fmt(p.sici_pj)})`]
    if (Number(p.sici_municipios)) partes.push(`${fmt(p.sici_municipios)} ${Number(p.sici_municipios) === 1 ? 'município' : 'municípios'}`)
    if (p.sici_tecnologia) partes.push(String(p.sici_tecnologia))
    texto = `SICI${mes ? ` ${mes}` : ''}: ${partes.join(', ')}`
  } else {
    texto = `Sem acessos declarados no SICI${mes ? ` em ${mes}` : ' no mês de referência do snapshot'}`
  }
  return `<span style="font-size:.82em;color:#555">${escapar(texto)}</span>`
}

export function htmlEnlaceTerrestre(p: Props): string {
  return `<strong>${escapar(p.type_inf ?? 'Enlace terrestre')}</strong><br/>` +
    `<span style="font-size:.78em;color:#9ca3af">ITU BBmaps · ${escapar(p.status ?? '')}</span>`
}

export function htmlCaboSubmarino(p: Props): string {
  const meta = [p.length, p.rfs_year ? `RFS ${p.rfs_year}` : ''].filter(Boolean).join(' · ')
  return `<strong>${escapar(p.name ?? '')}</strong>${meta ? `<br/><span style="font-size:.82em;color:#555">${escapar(meta)}</span>` : ''}` +
    (p.owners ? `<br/><span style="font-size:.78em;color:#9ca3af">${escapar(p.owners)}</span>` : '')
}

export function htmlPontoAterrissagem(p: Props): string {
  return `<strong>${escapar(p.name ?? '')}</strong><br/>` +
    `<span style="font-size:.78em;color:#9ca3af">Ponto de aterrissagem${escapar(p.is_tbd ? ' (planejado)' : '')}</span>`
}

export function htmlLinhaTransmissao(p: Props): string {
  const meta = [p.tensao_kv ? `${p.tensao_kv} kV` : '', p.extensao_km ? `${p.extensao_km} km` : '']
    .filter(Boolean).join(' · ')
  return `<strong>${p.subestacao_origem && p.subestacao_destino ? `${escapar(p.subestacao_origem)} / ${escapar(p.subestacao_destino)}` : (p.name ?? 'Linha de transmissão')}</strong>` +
    (meta ? `<br/><span style="font-size:.82em;color:#555">${escapar(meta)}</span>` : '') +
    `<br/><span style="font-size:.78em;color:#9ca3af">SIGEL/ANEEL</span>`
}

export function htmlErbs(p: Props): string {
  const g = [['2G', p.g2], ['3G', p.g3], ['4G', p.g4], ['5G', p.g5]].filter(([, n]) => Number(n) > 0).map(([k, n]) => `${k} ${n}`).join(' · ')
  return `<strong>${escapar(p.estacoes)} estaç${escapar(Number(p.estacoes) === 1 ? 'ão' : 'ões')} licenciada${escapar(Number(p.estacoes) === 1 ? '' : 's')}</strong> <span style="font-size:.82em;color:#555">(célula de ~2 km)</span>` +
    (g ? `<br/><span style="font-size:.82em;color:#555">${escapar(g)}</span>` : '') +
    `<br/><span style="font-size:.78em;color:#9ca3af">Anatel · cadastro de licenciamento, não é cobertura</span>`
}

export function htmlRodovia(p: Props): string {
  const meta = [p.jurisdicao, p.revestimento].filter(Boolean).join(' · ')
  return `<strong>${escapar(p.sigla ?? p.tipo_via ?? 'Rodovia')}</strong>` +
    (meta ? `<br/><span style="font-size:.82em;color:#555">${escapar(meta)}</span>` : '') +
    `<br/><span style="font-size:.78em;color:#9ca3af">IBGE/BC250</span>`
}
