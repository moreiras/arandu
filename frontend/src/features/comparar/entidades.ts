// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ASNDocument, PerfilMunicipio, PerfilOperadora } from '../../types/api'
import type { Selo } from '../../components/entidade'
import { provedoresTransitoV4 } from '../asn/sintese'

/** Tipos que o comparador genérico entende; `ixp` é o comparador de PTTs, a aba padrão de `/comparar`. */
export type TipoComparacao = 'ixp' | 'asn' | 'operadora' | 'municipio' | 'grupo'
export const TIPOS: Array<{ id: TipoComparacao; rotulo: string; exemplo: string }> = [
  { id: 'ixp', rotulo: 'PTTs', exemplo: 'sp, rj' },
  { id: 'asn', rotulo: 'ASes', exemplo: '15169, 13335' },
  { id: 'operadora', rotulo: 'Operadoras', exemplo: 'CNPJ' },
  { id: 'municipio', rotulo: 'Municípios', exemplo: 'código IBGE' },
  { id: 'grupo', rotulo: 'Grupos', exemplo: 'grp_…' },
]
export const MIN_ENTIDADES = 2
export const MAX_ENTIDADES = 4

/** Identificador válido de cada tipo: ASN (só dígitos), CNPJ (14 dígitos), IBGE (7 dígitos). */
export function idValido(tipo: Exclude<TipoComparacao, 'ixp'>, valor: string): string | null {
  const d = valor.replace(/\D/g, '')
  if (tipo === 'asn') return d && d.length <= 10 ? String(Number(d)) : null
  if (tipo === 'operadora') return d.length === 14 ? d : null
  if (tipo === 'grupo') return /^(grp|ind)_[0-9a-z]{1,20}$/i.test(valor.trim()) ? valor.trim().toLowerCase() : null
  return d.length === 7 ? d : null
}

/** Lê a lista de `?ids=` (vírgulas), sem repetição e no máximo `MAX_ENTIDADES`; ignora o que não é identificador do tipo. */
export function lerIds(tipo: Exclude<TipoComparacao, 'ixp'>, bruto: string | null): string[] {
  const ids = (bruto ?? '').split(',').map((x) => idValido(tipo, x.trim())).filter((x): x is string => !!x)
  return [...new Set(ids)].slice(0, MAX_ENTIDADES)
}

/** URL do comparador; `ids` já validados. Sem ids, só o tipo. */
export const urlComparar = (tipo: TipoComparacao, ids: string[]) => `/comparar?tipo=${tipo}${ids.length ? `&ids=${ids.join(',')}` : ''}`

/**
 * Aliases: `/comparar?asn=1,2`, `?operadora=…` e `?municipio=…` valem como `?tipo=…&ids=…`. Sem nenhum deles, o tipo é o da URL
 * ou `ixp` (o `/comparar` de sempre).
 */
export function tipoEIds(params: URLSearchParams): { tipo: TipoComparacao; ids: string[]; alias: boolean } {
  for (const t of ['asn', 'operadora', 'municipio', 'grupo'] as const) {
    if (params.has(t)) return { tipo: t, ids: lerIds(t, params.get(t)), alias: true }
  }
  const t = params.get('tipo')
  const tipo = (TIPOS.find((x) => x.id === t)?.id ?? 'ixp') as TipoComparacao
  return { tipo, ids: tipo === 'ixp' ? (params.get('ids') ?? '').split(',').map((x) => x.trim().toLowerCase()).filter(Boolean).slice(0, MAX_ENTIDADES) : lerIds(tipo, params.get('ids')), alias: false }
}

export interface ColunaComparada { id: string; nome: string; detalhe?: string; to: string }
export interface LinhaComparada { id: string; rotulo: string; celulas: Array<string | null>; selo: Selo; nota?: string }
export interface Comparacao { colunas: ColunaComparada[]; linhas: LinhaComparada[] }

const n = (v: number | null | undefined) => (v == null ? null : v.toLocaleString('pt-BR', { maximumFractionDigits: 0 }))
const d1 = (v: number | null | undefined, sufixo = '') => (v == null ? null : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}${sufixo}`)
const sinal = (v: number | null | undefined) => (v == null ? null : `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

/** Uma linha só entra se pelo menos uma entidade tem o dado: a comparação não mostra fileiras de travessões. */
const comDado = (l: LinhaComparada) => l.celulas.some((c) => c != null)

export function compararAs(docs: ASNDocument[]): Comparacao {
  const linha = (id: string, rotulo: string, f: (d: ASNDocument) => string | null, selo: Selo = 'fato', nota?: string): LinhaComparada => ({ id, rotulo, celulas: docs.map(f), selo, nota })
  return {
    colunas: docs.map((d) => ({ id: String(d.asn), nome: `AS${d.asn}`, detalhe: d.name, to: `/asn/${d.asn}` })),
    linhas: [
      linha('pais', 'Registro', (d) => (d.is_br ? 'Brasil' : 'Fora do Brasil')),
      linha('v6', 'Prefixos IPv6 anunciados', (d) => n(d.global_prefixes_v6_count)),
      linha('v4', 'Prefixos IPv4 anunciados', (d) => n(d.global_prefixes_v4_count)),
      linha('ptts', 'PTTs com sessão direta', (d) => n(d.ixps_direct?.length)),
      linha('usuarios', 'Usuários estimados (APNIC)', (d) => n(d.apnic_users), 'estimado', 'estimativa da APNIC; um AS pode compartilhar usuários com outros da mesma operadora'),
      linha('v6usuarios', 'Usuários com IPv6', (d) => d1(d.apnic_v6_pct_as, '%'), 'estimado'),
      linha('transito', 'Provedores de trânsito IPv4 (ARC, nível provável ou superior)', (d) => { const t = provedoresTransitoV4(d); return t.semRelacoes ? null : n(t.fortes.length) }, 'inferido',
        'relações inferidas do AS_PATH visto em poucos coletores, sem o próprio AS nem irmãos; não provam contrato'),
      linha('rpki', 'ROAs cadastrados', (d) => n(d.roa_list?.length)),
      linha('aspa', 'Provedores declarados em ASPA', (d) => n(d.aspa_providers?.length)),
    ].filter(comDado),
  }
}

export function compararOperadoras(perfis: PerfilOperadora[]): Comparacao {
  const linha = (id: string, rotulo: string, f: (p: PerfilOperadora) => string | null, selo: Selo = 'fato', nota?: string): LinhaComparada => ({ id, rotulo, celulas: perfis.map(f), selo, nota })
  const nome = (p: PerfilOperadora) => p.indicadores?.empresa ?? p.scm?.empresa ?? p.smp?.empresa ?? p.cnpj
  return {
    colunas: perfis.map((p) => ({ id: p.cnpj, nome: nome(p), detalhe: p.cnpj, to: `/operadora/${p.cnpj}` })),
    linhas: [
      linha('acessos', 'Acessos fixos declarados', (p) => n(p.indicadores?.acessos), 'fato', 'declarado ao SICI; mês de referência na página da operadora'),
      linha('share', 'Parcela dos acessos do país', (p) => d1(p.indicadores?.share_br, '%')),
      linha('posicao', 'Posição por acessos', (p) => (p.indicadores?.posicao_br ? `${n(p.indicadores.posicao_br)}º` : null)),
      linha('var', 'Variação em 12 meses', (p) => sinal(p.indicadores?.var_aa?.pct)),
      linha('municipios', 'Municípios com acessos', (p) => n(p.scm?.municipios)),
      linha('asns', 'ASNs', (p) => n(p.scm?.asns?.length ?? p.smp?.asns?.length), 'fato', 'ASNs ligados ao CNPJ pelo Registro.br'),
      linha('porte', 'Porte', (p) => p.scm?.porte ?? p.smp?.porte ?? null),
      linha('grupo', 'Grupo', (p) => p.scm?.grupo ?? p.smp?.grupo ?? null, 'inferido', 'grupo por quadro societário em comum'),
    ].filter(comDado),
  }
}

export function compararMunicipios(perfis: PerfilMunicipio[]): Comparacao {
  const linha = (id: string, rotulo: string, f: (p: PerfilMunicipio) => string | null, selo: Selo = 'fato', nota?: string): LinhaComparada => ({ id, rotulo, celulas: perfis.map(f), selo, nota })
  return {
    colunas: perfis.map((p) => ({ id: p.ibge, nome: p.nome, detalhe: p.uf, to: `/municipio/${p.ibge}` })),
    linhas: [
      linha('acessos', 'Acessos fixos declarados', (p) => n(p.indicadores?.acessos ?? p.fixo?.acessos)),
      linha('operadoras', 'Operadoras declarantes', (p) => n(p.indicadores?.n_operadoras ?? p.fixo?.operadores_count)),
      linha('hhi', 'Concentração (HHI, 10.000 = monopólio)', (p) => n(p.indicadores?.hhi ?? p.fixo?.hhi), 'fato', 'sobre acessos declarados, não sobre receita'),
      linha('lider', 'Participação da maior operadora', (p) => d1(p.indicadores?.lider?.share, '%')),
      linha('var', 'Variação dos acessos em 12 meses', (p) => sinal(p.indicadores?.var_aa_pct)),
      linha('domicilios', 'Domicílios (projeção)', (p) => n(p.territorio?.domicilios_projetados ?? p.territorio?.domicilios), 'estimado'),
      linha('penetracao', 'Acessos fixos por 100 domicílios', (p) => (p.territorio?.penetracao == null ? null : d1(p.territorio.penetracao * 100)), 'estimado', 'um domicílio pode ter vários acessos ou nenhum'),
      linha('ptt', 'Distância ao PTT mais próximo', (p) => (p.territorio?.km_ptt == null ? null : `${n(p.territorio.km_ptt)} km`), 'estimado', 'linha reta até o centróide do município'),
    ].filter(comDado),
  }
}

/** O grupo com os blocos que a comparação usa (`GET /grupos/{id}?include=mercado,regulatorio,tecnico`). */
export interface GrupoComparavel { grupo: import('../../types/api').GrupoDetalhe; mercado: import('../../types/api').GrupoMercadoFixo | null; regulatorio: import('../../types/api').GrupoRegulatorio | null; tecnico: import('../../types/api').GrupoTecnico | null }

/** Grupos econômicos lado a lado: tamanho, mercado, regulatório e técnico. O grupo é inferido; multas e reclamações não são comparadas entre grupos (não há ranking por multa ou reclamação). */
export function compararGrupos(gs: GrupoComparavel[]): Comparacao {
  const linha = (id: string, rotulo: string, f: (g: GrupoComparavel) => string | null, selo: Selo = 'fato', nota?: string): LinhaComparada => ({ id, rotulo, celulas: gs.map(f), selo, nota })
  const nome = (g: GrupoComparavel) => g.grupo.cnpjs[0]?.empresa || g.grupo.grupo_id
  return {
    colunas: gs.map((g) => ({ id: g.grupo.grupo_id, nome: g.grupo.tamanho > 1 ? `Grupo de ${nome(g)}` : nome(g), detalhe: `${g.grupo.empresas} ${g.grupo.empresas === 1 ? 'empresa' : 'empresas'}`, to: `/grupo/${g.grupo.grupo_id}` })),
    linhas: [
      linha('composicao', 'Composição', (g) => g.grupo.classificacao, 'inferido', 'inferida do quadro societário: ligações diretas entre pares, grupo reunido pela cadeia de ligações'),
      linha('cnpjs', 'CNPJs com acessos declarados', (g) => (g.mercado ? `${n(g.mercado.cnpjs_com_acessos)} de ${n(g.mercado.cnpjs_total)}` : null)),
      linha('acessos', 'Acessos fixos declarados', (g) => n(g.grupo.assinantes), 'fato', 'soma das empresas do grupo; SICI, banda larga fixa'),
      linha('parcela', 'Parcela dos acessos fixos do país', (g) => d1(g.mercado?.serie[g.mercado.serie.length - 1]?.parcela, '%'), 'inferido'),
      linha('posicao', 'Posição por acessos', (g) => (g.mercado?.posicao.atual ? `${n(g.mercado.posicao.atual)}º de ${n(g.mercado.posicao.unidades)}` : null), 'inferido', 'entre empresas e grupos que declararam no mês'),
      linha('ufs', 'UFs com acessos', (g) => n(g.mercado?.por_uf.length)),
      linha('municipios', 'Municípios com acessos', (g) => n(g.grupo.municipios.length)),
      linha('usuarios', 'Usuários estimados (APNIC)', (g) => n(g.grupo.usuarios_apnic), 'estimado', 'estimativa; usuários podem se repetir entre ASes da mesma operadora'),
      linha('asns', 'ASes', (g) => n(g.tecnico?.asns_total ?? g.grupo.asns.length)),
      linha('v6', 'Usuários com IPv6', (g) => d1(g.tecnico?.ipv6.pct_v6, '%'), 'estimado'),
      linha('roa', 'Prefixos com ROA válido', (g) => d1(g.tecnico?.rpki.valido_pct, '%')),
      linha('ptts', 'PTTs com sessão direta', (g) => n(g.tecnico?.ptts.length)),
      linha('outorgas', 'Empresas com outorga (SCM / SMP / STFC / SeAC)', (g) => (g.regulatorio ? ['SCM', 'SMP', 'STFC', 'SeAC'].map((s) => g.regulatorio!.outorgas[s] ?? 0).join(' / ') : null), 'fato', 'quantas empresas do grupo têm cada outorga'),
    ].filter(comDado),
  }
}
