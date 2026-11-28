// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { limitar, MAX_FRASES_HOME, n0, palavra, pct1, compacto, type FraseSintese } from '../../lib/sintese'
import { formatarReferencia } from '../../components/entidade/proveniencia'
import { UNIVERSOS } from '../../lib/universos'
import type { BrasilIndicadores, SiciStats, SnapshotSummary } from '../../types/api'
import { parcelaTresMaiores } from '../mercado/sinteseMercado'
import type { KpiHome } from './kpisBrasilEmNumeros'

export const REGRAS_SINTESE_HOME = 'sintese-home-3'

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
 * Síntese da Home (PT-22, home 5.1): frases em cinco parágrafos (rede, IX.br, segurança, mercado, usuários), montadas dos números que a Home já carrega, sem
 * variação (a variação das faixas segue a regra de comparabilidade da API). As quatro frases dos KPIs herdam selo, fonte e data do KPI de que saem; as demais
 * leem o resumo do snapshot, `/brasil/indicadores` e o SICI, cada uma com o próprio selo. Dado ausente não gera frase.
 *
 * Regras de contagem: participação direta é sessão com route server em algum PTT, indireta é só originar prefixos vistos nos PTTs; cada ASN conta uma vez no país
 * (`ixbr` de `/brasil/indicadores`). Os usuários alcançados pelos PTTs são a união por ASN (`ixp_estimated_users_v4`: fração do espaço IPv4 do ASN visto em algum PTT
 * vezes os usuários estimados do ASN), nunca a soma por PTT. Concentração: HHI nacional por CNPJ e parcela dos três CNPJs com mais acessos, sem nomear empresa.
 */
export function sinteseHome(kpis: { rede: KpiHome[]; mercado: KpiHome[] }, dados: DadosSinteseHome = {}): FraseSintese[] {
  const k = (lista: KpiHome[], id: string) => lista.find((x) => x.id === id && x.valor != null)
  const ases = k(kpis.rede, 'ases'), v6 = k(kpis.rede, 'ipv6'), usuarios = k(kpis.rede, 'usuarios')
  const acessos = k(kpis.mercado, 'acessos'), fibra = k(kpis.mercado, 'fibra')
  const de = (x: KpiHome, texto: string, paragrafo: string): FraseSintese => ({ id: x.id, texto, selo: x.selo, fonte: x.fonte, dataRef: x.dataRef, paragrafo })
  const mes = acessos?.dataRef ? formatarReferencia(acessos.dataRef) : null
  const { resumo, br, sici } = dados
  const snap = br?.snapshot_date ?? resumo?.snapshot_date ?? ases?.dataRef ?? null

  const ixbr = br?.ixbr
  const diretos = ixbr?.asns_br_diretos, indiretos = ixbr?.asns_br_indiretos
  const agg = resumo?.ixp_aggregate
  const temColeta = (resumo?.ixps_ok ?? 0) > 0
  const cob6 = temColeta && agg?.v6_br_coverage_pct ? agg.v6_br_coverage_pct : null
  const cob4 = temColeta && agg?.v4_br_coverage_pct ? agg.v4_br_coverage_pct : null
  const espaco = [cob6 != null && `${pct(cob6)} do espaço IPv6`, cob4 != null && `${pct(cob4)} do espaço IPv4`].filter(Boolean).join(' e ')

  const pub = br?.rpki?.publicacao
  const total = pub?.br_asns_total ?? 0
  const rotas = br?.rpki?.rotas?.rpki
  const validas = [['IPv6', rotas?.v6?.pct?.valid], ['IPv4', rotas?.v4?.pct?.valid]] as const
  const rotasValidas = validas.filter(([, v]) => v != null).map(([f, v]) => `${pct(v as number)} em ${f}`).join(' e ')
  const dnssec = br?.dnssec?.media_ponderada_pct, rov = br?.rov?.media_ponderada_pct

  const hhi = br?.mercado?.hhi_cnpj
  const tres = parcelaTresMaiores(sici?.top_operadoras, sici?.total_acessos)
  const alcancados = resumo?.ixp_estimated_users_v4, pais = resumo?.br_apnic_users_total

  return limitar([
    ases && de(ases, `Este snapshot registra ${ases.valor} ${UNIVERSOS.asnsLacnic.rotulo}.`, 'rede'),
    v6 && de(v6, `Desses ASNs, ${v6.valor} originam ao menos um prefixo IPv6 na tabela global. Um bloco IPv6 alocado e não anunciado não entra no cálculo.`, 'rede'),

    diretos != null && temColeta && { id: 'ixbr-diretos', selo: 'fato', fonte: FONTE_LG, dataRef: snap, paragrafo: 'ixbr',
      texto: `No IX.br, ${n0(diretos)} ${palavra(diretos, 'ASN', 'ASNs')} da lista do Registro.br ${palavra(diretos, 'participa', 'participam')} diretamente, com sessão em route server de ao menos um PTT.` },
    indiretos != null && temColeta && { id: 'ixbr-indiretos', selo: 'inferido', fonte: `${FONTE_LG} (origem das rotas)`, dataRef: snap, paragrafo: 'ixbr',
      texto: `Outros ${n0(indiretos)} ${palavra(indiretos, 'ASN participa indiretamente, pois só origina', 'ASNs participam indiretamente, pois só originam')} prefixos vistos nos PTTs, levados por outro participante.` },
    espaco !== '' && { id: 'ixbr-espaco', selo: 'fato', fonte: `${FONTE_LG} e alocações do Registro.br`, dataRef: snap, paragrafo: 'ixbr',
      texto: `Os prefixos vistos nos PTTs cobrem ${espaco} alocados ao Brasil pelo Registro.br.` },

    dnssec != null && { id: 'dnssec', selo: 'estimado', fonte: 'APNIC Labs', dataRef: br?.dnssec?.fonte?.as_of ?? snap, paragrafo: 'seguranca',
      texto: `${pct(dnssec, 2)} das medições do APNIC no Brasil indicam resolvedores de DNS que validam DNSSEC.` },
    pub && total > 0 && pub.br_asns_with_roa != null && { id: 'roa', selo: 'fato', fonte: FONTE_RPKI, dataRef: snap, paragrafo: 'seguranca',
      texto: `${n0(pub.br_asns_with_roa)} dos ${n0(total)} ${UNIVERSOS.asnsRegistroBr.rotulo} publicaram ao menos uma ROA (${pct(fracao(pub.br_asns_with_roa, total))}).` },
    rotasValidas !== '' && { id: 'roa-rotas', selo: 'fato', fonte: `${FONTE_RPKI} e tabela global (RouteViews)`, dataRef: snap, paragrafo: 'seguranca',
      texto: `Entre as rotas de origem brasileira, ${rotasValidas} têm origem válida segundo as ROAs.` },
    rov != null && { id: 'rov', selo: 'estimado', fonte: 'APNIC Labs', dataRef: br?.rov?.fonte?.as_of ?? snap, paragrafo: 'seguranca',
      texto: `${pct(rov, 2)} das medições do APNIC indicam filtragem de rotas inválidas (ROV).` },
    pub && total > 0 && pub.br_asns_with_aspa != null && { id: 'aspa', selo: 'fato', fonte: FONTE_RPKI, dataRef: snap, paragrafo: 'seguranca',
      texto: `A ASPA, que lista os provedores autorizados de um ASN, foi publicada por ${n0(pub.br_asns_with_aspa)} ${palavra(pub.br_asns_with_aspa, 'ASN', 'ASNs')} (${pct(fracao(pub.br_asns_with_aspa, total))}).` },

    acessos && de(acessos, `${mes ? `Em ${mes}, as` : 'No mês de referência, as'} operadoras declararam ao SICI, da Anatel, ${acessos.valor} acessos de banda larga fixa${fibra ? `, dos quais ${fibra.valor} em fibra` : ''}.`, 'mercado'),
    acessos && sici && sici.operadoras_ativas > 0 && { id: 'operadoras', selo: 'fato', fonte: FONTE_SICI, dataRef: sici.mes_referencia, paragrafo: 'mercado',
      texto: `Esses acessos vêm de ${n0(sici.operadoras_ativas)} ${palavra(sici.operadoras_ativas, 'CNPJ que declarou', 'CNPJs que declararam')} acessos fixos no mês.` },
    hhi != null && { id: 'hhi', selo: 'fato', fonte: FONTE_SICI, dataRef: br?.mercado?.mes_referencia ?? sici?.mes_referencia, paragrafo: 'mercado',
      texto: `O HHI do mercado fixo no país é ${n0(hhi)}, numa escala de 0 a 10.000. O cálculo usa os acessos declarados por CNPJ e não agrupa CNPJs do mesmo grupo econômico.` },
    tres != null && { id: 'tres-maiores', selo: 'fato', fonte: FONTE_SICI, dataRef: sici?.mes_referencia, paragrafo: 'mercado',
      texto: `Os três CNPJs com mais acessos declarados somam ${pct1(tres)} do total.` },

    usuarios && de(usuarios, `Somando as estimativas do APNIC para cada ASN brasileiro, são ${usuarios.valor} usuários de Internet. Esse número é estimado a partir de amostras de anúncios.`, 'usuarios'),
    alcancados != null && pais != null && pais > 0 && alcancados > 0 && { id: 'ixbr-usuarios', selo: 'estimado', fonte: `APNIC Labs e ${FONTE_LG}`, dataRef: snap, paragrafo: 'usuarios',
      texto: `Os prefixos vistos nos PTTs do IX.br alcançam cerca de ${compacto(alcancados)} desses usuários (${pct1(fracao(alcancados, pais))}). Cada ASN conta uma só vez, e o cálculo usa só IPv4.` },
  ], MAX_FRASES_HOME)
}
