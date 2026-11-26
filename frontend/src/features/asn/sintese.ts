// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../../components/entidade'
import type { ASNDocument, ReferenciasAsn } from '../../types/api'
import { SITE } from '../../lib/site'
import { RELACAO_PTT } from '../../lib/universos'

/**
 * Frase-síntese do AS: gerada por **regras**, sem modelo de linguagem. Cada frase sai de campos do snapshot, leva o
 * selo (fato, inferido ou estimado) e a versão das regras. Mudar uma regra muda `REGRAS_VERSAO`; o teste fixa o conjunto de ids.
 */
export const REGRAS_VERSAO = 'sintese-as-3'

export interface Frase { id: string; texto: string; selo: Selo }
/** Frase com a fonte e a data de referência, que o resumo em texto manda para o bloco recolhido (PT-30). */
export interface FraseComFonte extends Frase { fonte: string; dataRef: string | null }

const n = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const plural = (q: number, um: string, varios: string) => `${n(q)} ${q === 1 ? um : varios}`

const FORTES = new Set(['declarado', 'confirmado', 'provavel'])

export interface ProvedoresV4 {
  /** Sem o fragmento `relacoes` (snapshot anterior ao ARC). */
  semRelacoes: boolean
  /** Provedores IPv4 de nível provável ou superior, sem o próprio AS, irmãos inferidos e ASNs do mesmo CNPJ. */
  fortes: number[]
  /** Só de nível possível, com as mesmas exclusões. */
  possiveis: number[]
  /** ASNs do mesmo CNPJ ou irmãos que apareceriam como provedor e ficaram de fora. */
  irmaos: number[]
  /** `relacoes.multihomed.v4` nulo: visibilidade insuficiente ou só relações possíveis. */
  indeterminado: boolean
}

/**
 * Provedores de trânsito IPv4 pelas relações inferidas (ARC), por nível. Nunca usa `upstreams_v4`, `is_multihomed_v4` nem
 * `single_upstream_v4` (adjacência no AS_PATH, deprecados), nem conta o próprio AS ou um irmão como provedor (ASN-E4, CMP-E5).
 */
export function provedoresTransitoV4(doc: ASNDocument): ProvedoresV4 {
  const rel = doc.relacoes
  if (!rel) return { semRelacoes: true, fortes: [], possiveis: [], irmaos: [], indeterminado: true }
  const irmaos = new Set<number>([...(doc.same_cnpj_asns ?? []).map((x) => x.asn), ...(rel.irmaos ?? []).map((x) => x.asn)])
  const fortes: number[] = []
  const possiveis: number[] = []
  const fora: number[] = []
  for (const p of rel.provedores ?? []) {
    if (!p.afi.includes('v4') || p.asn === doc.asn) continue
    if (irmaos.has(p.asn)) { if (!fora.includes(p.asn)) fora.push(p.asn); continue }
    if (FORTES.has(p.nivel)) { if (!fortes.includes(p.asn)) fortes.push(p.asn) } else if (p.nivel === 'possivel' && !possiveis.includes(p.asn)) possiveis.push(p.asn)
  }
  return { semRelacoes: false, fortes, possiveis, irmaos: fora, indeterminado: rel.multihomed?.v4 == null }
}

const lista = (asns: number[]) => asns.map((a) => `AS${a}`).join(', ')

/** Frase de trânsito da regra `sintese-as-3`: conta provedores de nível provável ou superior (não `n_provedores`, que é confirmado+). */
export function fraseTransito(doc: ASNDocument): string {
  const t = provedoresTransitoV4(doc)
  if (t.semRelacoes) return 'Esta data não tem a lista de provedores de trânsito do AS, que vem de inferência a partir das relações do CAIDA e da tabela global.'
  const poss = t.possiveis.length ? `, além de ${n(t.possiveis.length)} de nível possível` : ''
  const irm = t.irmaos.length ? ` ${lista(t.irmaos)}, do mesmo CNPJ ou da mesma organização, ${t.irmaos.length > 1 ? 'não entram' : 'não entra'} na contagem.` : ''
  if (t.fortes.length >= 2) return `Pelas relações inferidas, o AS tem ${n(t.fortes.length)} provedores de trânsito IPv4 de nível provável ou superior (${lista(t.fortes)})${poss}.${irm}`
  if (t.fortes.length === 1) return `Pelas relações inferidas, o AS tem um provedor de trânsito IPv4 de nível provável ou superior (${lista(t.fortes)})${poss}.${irm}`
  if (t.possiveis.length) return `Pelas relações inferidas, nenhum provedor de trânsito IPv4 chega ao nível provável neste snapshot; há ${plural(t.possiveis.length, 'relação possível', 'relações possíveis')}.${irm}`
  return t.indeterminado ? `Não há visibilidade suficiente para inferir provedores de trânsito IPv4.${irm}` : `Nenhum provedor de trânsito IPv4 foi inferido neste snapshot.${irm}`
}

/** As frases do AS, na ordem de leitura; regra sem dado não gera frase (nunca preenche com palpite). Cada frase leva fonte e data para o bloco recolhido da ficha. */
export function sinteseAs(doc: ASNDocument, ref?: ReferenciasAsn | null): FraseComFonte[] {
  const f: FraseComFonte[] = []
  const dataRef = doc.snapshot_date ?? null
  const v4 = doc.global_prefixes_v4_count ?? doc.global_prefixes_v4?.length ?? 0
  const v6 = doc.global_prefixes_v6_count ?? doc.global_prefixes_v6?.length ?? 0
  f.push({
    id: 'anuncio', selo: 'fato', fonte: 'Tabela global de roteamento (RouteViews)', dataRef,
    texto: v4 + v6 > 0
      ? `AS${doc.asn} (${doc.name}) anuncia ${plural(v6, 'prefixo IPv6', 'prefixos IPv6')} e ${plural(v4, 'prefixo IPv4', 'prefixos IPv4')} na tabela de roteamento global.`
      : `AS${doc.asn} (${doc.name}) não aparece com prefixos na tabela de roteamento global deste snapshot.`,
  })
  const diretos = doc.ixps_direct?.length ?? 0
  const origem = doc.ixps_origin?.length ?? 0
  f.push({
    id: 'ptts', selo: 'fato', fonte: 'Looking glass do IX.br', dataRef,
    texto: diretos + origem > 0
      ? `O AS tem sessão no route server em ${plural(diretos, 'PTT do IX.br', 'PTTs do IX.br')} e aparece como originador em ${plural(origem, 'PTT', 'PTTs')}.`
      : 'O AS não aparece em PTTs do IX.br coletados neste snapshot.',
  })
  // `rpki_validation` cobre a união dos prefixos alocados (Registro.br) e anunciados (tabela global). A frase só fala de "anunciados" quando
  // o denominador é o conjunto anunciado (o mesmo dos cartões); sem a lista de anunciados, diz "alocados ou anunciados".
  const anunciados = new Set([...(doc.global_prefixes_v4 ?? []), ...(doc.global_prefixes_v6 ?? [])])
  const validados = Object.entries(doc.rpki_validation ?? {})
  const rpki = anunciados.size > 0 ? validados.filter(([p]) => anunciados.has(p)) : validados
  const [uno, varios] = anunciados.size > 0 ? ['anunciado', 'anunciados'] : ['alocado ou anunciado', 'alocados ou anunciados']
  if (rpki.length > 0) {
    const valido = rpki.filter(([, s]) => s === 'valid').length
    const invalido = rpki.filter(([, s]) => s === 'invalid').length
    f.push({
      id: 'rpki', selo: 'fato', fonte: 'RPKI (validação dos prefixos do AS)', dataRef,
      texto: `${n(valido)} de ${n(rpki.length)} ${rpki.length === 1 ? `prefixo ${uno} tem` : `prefixos ${varios} têm`} ROA válido`
        + (invalido > 0 ? `, e ${plural(invalido, 'está inválido', 'estão inválidos')}.` : '.'),
    })
  }
  if (doc.apnic_users != null && doc.apnic_users > 0) {
    const pos = ref?.usuarios_posicao
    f.push({
      id: 'usuarios', selo: 'estimado', fonte: 'APNIC Labs', dataRef,
      texto: `O APNIC estima cerca de ${n(doc.apnic_users)} usuários neste AS`
        + (pos && ref ? `, que ocupa o ${n(pos)}º lugar entre os ${n(ref.usuarios_com_dado)} ASes brasileiros com estimativa.` : '.'),
    })
  }
  f.push({ id: 'transito', selo: 'inferido', fonte: 'Relações inferidas (CAIDA, tabela global e looking glass do IX.br)', dataRef, texto: fraseTransito(doc) })
  const alertas = doc.alerts?.length ?? 0
  if (alertas > 0) f.push({ id: 'alertas', selo: 'fato', fonte: `Regras do ${SITE.nome} sobre os dados do snapshot`, dataRef, texto: `Pelas regras do ${SITE.nome}, este AS tem ${plural(alertas, 'ponto de atenção', 'pontos de atenção')} (aba Resumo).` })
  return f
}

export interface KpiAs { id: string; rotulo: string; valor: number | null; sufixo?: string; referencia?: string; selo: Selo; fonte: string }

/**
 * Indicadores da ficha, cada um com a referência de comparação quando o servidor a envia (`include=referencias`) e a proveniência (PT-14):
 * prefixos e sessões são observação (fato); usuários, do APNIC, são estimativa. O rótulo de PTTs diz o universo: sessão em route server,
 * não o cadastro de participantes (PT-15).
 */
export function kpisAs(doc: ASNDocument, ref?: ReferenciasAsn | null): KpiAs[] {
  const med = (v?: number | null, un = '') => (v == null ? undefined : `mediana dos ASes BR: ${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}${un}`)
  return [
    { id: 'v6', rotulo: 'Prefixos IPv6 anunciados', valor: doc.global_prefixes_v6_count ?? null, selo: 'fato', fonte: 'tabela global (RouteViews)' },
    { id: 'v4', rotulo: 'Prefixos IPv4 anunciados', valor: doc.global_prefixes_v4_count ?? null, referencia: med(ref?.prefixos_v4_mediana), selo: 'fato', fonte: 'tabela global (RouteViews)' },
    { id: 'ptts', rotulo: RELACAO_PTT.pttsSessaoRs, valor: doc.ixps_direct?.length ?? null, referencia: med(ref?.ixps_diretos_mediana), selo: 'fato', fonte: 'looking glass do IX.br' },
    { id: 'usuarios', rotulo: 'Usuários estimados (APNIC)', valor: doc.apnic_users ?? null, selo: 'estimado', fonte: 'APNIC Labs',
      referencia: ref?.usuarios_posicao ? `${ref.usuarios_posicao.toLocaleString('pt-BR')}º de ${ref.usuarios_com_dado.toLocaleString('pt-BR')} ASes BR` : undefined },
    { id: 'v6usuarios', rotulo: 'Usuários IPv6', valor: doc.apnic_v6_pct_as ?? null, sufixo: '%', referencia: med(ref?.pct_v6_mediana, '%'), selo: 'estimado', fonte: 'APNIC Labs' },
  ]
}
