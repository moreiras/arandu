// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { limitar, MAX_FRASES_HOME, n0, palavra, pct1, compacto, type FraseSintese } from '../../lib/sintese'
import { UNIVERSOS } from '../../lib/universos'
import type { BrasilIndicadores, SiciStats, SnapshotSummary } from '../../types/api'
import type { KpiHome } from './kpisBrasilEmNumeros'

export const REGRAS_SINTESE_HOME = 'sintese-home-4'

/** O que a Home já carrega e a síntese usa além dos KPIs: o resumo do snapshot, `/brasil/indicadores` e as estatísticas do SICI (nenhuma chamada a mais). */
export interface DadosSinteseHome {
  resumo?: SnapshotSummary | null
  br?: BrasilIndicadores | null
  sici?: SiciStats | null
}

const FONTE_LG = 'looking glasses do IX.br'
const FONTE_RPKI = 'RPKI (Routinator)'
const FONTE_SICI = 'SICI, Anatel (declarado pelas operadoras)'
const pct = (v: number, casas = 1) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: casas })}%`
const fracao = (parte: number, todo: number) => (100 * parte) / todo

/**
 * Síntese da Home (PT-22, home 5.1): até cinco frases curtas em dois parágrafos, uma por tema (rede e IPv6, IX.br, usuários alcançados pelos PTTs, segurança de
 * roteamento, mercado), sem repetir um a um os cartões acima. Cada frase combina números e leva o selo mais cauteloso entre os que usa (estimado, depois
 * inferido, depois fato), com as fontes somadas e a data do snapshot (ou o mês do SICI). Dado ausente não gera frase nem parte de frase. DNSSEC e ASPA ficam nos
 * cartões e nas páginas de segurança.
 *
 * Regras de contagem: participação direta é sessão com route server em algum PTT, indireta é só originar prefixos vistos nos PTTs; cada ASN conta uma vez no país
 * (`ixbr` de `/brasil/indicadores`). Os usuários alcançados pelos PTTs são a união por ASN (`ixp_estimated_users_v4`: fração do espaço IPv4 do ASN visto em algum PTT
 * vezes os usuários estimados do ASN), nunca a soma por PTT. Concentração: HHI nacional por CNPJ, sem nomear empresa.
 */
export function sinteseHome(kpis: { rede: KpiHome[]; mercado: KpiHome[] }, dados: DadosSinteseHome = {}): FraseSintese[] {
  const k = (lista: KpiHome[], id: string) => lista.find((x) => x.id === id && x.valor != null)
  const ases = k(kpis.rede, 'ases'), v6 = k(kpis.rede, 'ipv6'), usuarios = k(kpis.rede, 'usuarios')
  const { resumo, br, sici } = dados
  const snap = br?.snapshot_date ?? resumo?.snapshot_date ?? ases?.dataRef ?? null

  const ixbr = br?.ixbr
  const diretos = ixbr?.asns_br_diretos, indiretos = ixbr?.asns_br_indiretos
  const agg = resumo?.ixp_aggregate
  const temColeta = (resumo?.ixps_ok ?? 0) > 0
  const cob6 = temColeta && agg?.v6_br_coverage_pct ? agg.v6_br_coverage_pct : null
  const cob4 = temColeta && agg?.v4_br_coverage_pct ? agg.v4_br_coverage_pct : null
  const espaco = [cob6 != null && `${pct(cob6)} do espaço IPv6`, cob4 != null && `${pct(cob4)} do espaço IPv4`].filter(Boolean).join(' e ')
  const cobertura = espaco !== '' ? `os prefixos vistos nos PTTs cobrem ${espaco} alocados ao Brasil` : ''
  const participacao = diretos != null && temColeta
    ? `${n0(diretos)} ${palavra(diretos, 'ASN participa', 'ASNs participam')} diretamente${indiretos != null ? ` e outros ${n0(indiretos)} ${palavra(indiretos, 'participa', 'participam')} indiretamente, só originando prefixos vistos nos PTTs` : ''}`
    : ''
  const textoIx = [participacao, cobertura].filter(Boolean).join('; ')

  const pub = br?.rpki?.publicacao
  const total = pub?.br_asns_total ?? 0
  const roa = pub && total > 0 && pub.br_asns_with_roa != null
    ? `${n0(pub.br_asns_with_roa)} dos ${n0(total)} ${UNIVERSOS.asnsRegistroBr.rotulo} publicaram ao menos uma ROA (${pct(fracao(pub.br_asns_with_roa, total))})` : ''
  const rov = br?.rov?.media_ponderada_pct
  const textoRov = rov != null ? `${pct(rov, 2)} das medições do APNIC indicam filtragem de rotas inválidas (ROV)` : ''
  const textoSeguranca = [roa, textoRov].filter(Boolean).join(', e ')

  const hhi = br?.mercado?.hhi_cnpj
  const declarantes = sici && sici.operadoras_ativas > 0 ? sici.operadoras_ativas : null
  const mercado = [
    declarantes != null && `${n0(declarantes)} ${palavra(declarantes, 'CNPJ declarou', 'CNPJs declararam')} acessos de banda larga fixa ao SICI`,
    hhi != null && `o HHI nacional por CNPJ, sem agrupar grupos econômicos, é ${n0(hhi)}, numa escala de 0 a 10.000`,
  ].filter(Boolean).join(', e ')

  const alcancados = resumo?.ixp_estimated_users_v4, pais = resumo?.br_apnic_users_total
  const alcance = alcancados != null && pais != null && pais > 0 && alcancados > 0

  return limitar([
    ases && v6 && { id: 'rede', selo: 'fato', fonte: v6.fonte, dataRef: ases.dataRef, paragrafo: 'conectividade',
      texto: `Dos ${ases.valor} ${UNIVERSOS.asnsLacnic.rotulo}, ${v6.valor} originam ao menos um prefixo IPv6 na tabela global.` },
    ases && !v6 && { id: 'rede', selo: ases.selo, fonte: ases.fonte, dataRef: ases.dataRef, paragrafo: 'conectividade',
      texto: `Este snapshot registra ${ases.valor} ${UNIVERSOS.asnsLacnic.rotulo}.` },

    textoIx !== '' && { id: 'ixbr', selo: indiretos != null && participacao !== '' ? 'inferido' : 'fato', fonte: `${FONTE_LG} e alocações do Registro.br`, dataRef: snap, paragrafo: 'conectividade',
      texto: `No IX.br, ${textoIx}.` },

    alcance && { id: 'usuarios', selo: 'estimado', fonte: `APNIC Labs e ${FONTE_LG}`, dataRef: snap, paragrafo: 'conectividade',
      texto: `Os PTTs do IX.br alcançam cerca de ${compacto(alcancados)} dos ${usuarios ? `${usuarios.valor} usuários` : `${compacto(pais)} usuários`} de Internet que o APNIC estima no Brasil (${pct1(fracao(alcancados, pais))}), com cada ASN contado uma só vez e só em IPv4.` },
    !alcance && usuarios && { id: 'usuarios', selo: usuarios.selo, fonte: usuarios.fonte, dataRef: usuarios.dataRef, paragrafo: 'conectividade',
      texto: `Somando as estimativas do APNIC para cada ASN brasileiro, são ${usuarios.valor} usuários de Internet.` },

    textoSeguranca !== '' && { id: 'seguranca', selo: rov != null ? 'estimado' : 'fato', fonte: roa !== '' && rov != null ? `${FONTE_RPKI} e APNIC Labs` : roa !== '' ? FONTE_RPKI : 'APNIC Labs', dataRef: snap, paragrafo: 'seguranca-mercado',
      texto: `${textoSeguranca}.` },

    mercado !== '' && { id: 'mercado', selo: 'fato', fonte: FONTE_SICI, dataRef: br?.mercado?.mes_referencia ?? sici?.mes_referencia, paragrafo: 'seguranca-mercado',
      texto: `${mercado.charAt(0).toUpperCase()}${mercado.slice(1)}.` },
  ], MAX_FRASES_HOME)
}
