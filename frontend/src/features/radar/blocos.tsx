// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../entidade/registry'
import type { RadarAsn, RadarUf } from '../../types/api'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined, d = 1) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: d })}%`)
const dec = (v: number | null | undefined, d = 1) => (v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: d }))
const dia = (v: string | null | undefined) => (v ? v.slice(0, 10).split('-').reverse().join('/') : '—')

const PAPEIS: Array<[string, string]> = [['vazou', 'vazou rotas'], ['no_caminho_de_vazamento', 'no caminho de um vazamento'], ['sequestrou', 'originou rota sequestrada'], ['vitima_de_sequestro', 'teve prefixo sequestrado']]

function Rodape({ b }: { b: RadarAsn | RadarUf }) {
  const c = b.cobertura
  return (
    <>
      <p className="text-xs text-gray-500" data-testid="radar-cobertura">
        Cobertura (snapshot {b.snapshot_date}): {n(c.asns_com_dado_ipv6)} de {n(c.asns_do_brasil_no_snapshot)} ASNs do Brasil com IPv6 lido pelo Radar (leituras de {dia(c.leitura_mais_antiga)} a {dia(c.leitura_mais_recente)}; o rodízio completa
        a lista em cerca de uma semana); {n(c.asns_no_topo_de_trafego)} ASNs com tráfego e {n(c.asns_com_velocidade)} com velocidade. {b.limites}
      </p>
      <p className="text-xs text-gray-500" data-testid="radar-licenca">
        {b.fonte.atribuicao ?? b.fonte.nome} Licença dos dados: <a className="text-primario-600 hover:underline" href={b.fonte.licenca_url ?? 'https://creativecommons.org/licenses/by-nc/4.0/'} target="_blank" rel="noreferrer">{b.licenca}</a>.
        Coletado em {dia(b.coletado_em)}.
      </p>
    </>
  )
}

/**
 * Cloudflare Radar neste AS. IPv6 com a data da leitura (rodízio); tráfego e velocidade só dos ASNs de topo, e ausência não é zero; eventos de BGP por papel, que não provam intenção nem dano.
 */
export function RadarAsnBloco({ dados }: BlocoProps<{ radar?: RadarAsn | null }>) {
  const r = dados.radar
  if (!r) return null
  const papeis = PAPEIS.filter(([k]) => (r.bgp?.[k as keyof typeof r.bgp] ?? 0) > 0)
  return (
    <div className="space-y-3 text-sm" data-testid="radar-asn">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="radar-aviso">{r.aviso}</p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        <div><dt className="text-xs text-gray-500">IPv6 nas requisições de pessoas</dt><dd className="tabular-nums font-medium" data-testid="radar-ipv6">{r.ipv6 ? `${pct(r.ipv6.pct)} (lido em ${dia(r.ipv6.em)})` : 'sem leitura'}</dd></div>
        <div><dt className="text-xs text-gray-500">Participação no tráfego do Brasil</dt><dd className="tabular-nums font-medium">{r.trafego_pct_do_brasil != null ? pct(r.trafego_pct_do_brasil, 2) : 'fora do topo'}</dd></div>
        <div><dt className="text-xs text-gray-500">Velocidade (download / upload)</dt><dd className="tabular-nums font-medium">{r.velocidade ? `${dec(r.velocidade.download_mbps)} / ${dec(r.velocidade.upload_mbps)} Mbps` : 'fora do topo'}</dd></div>
        <div><dt className="text-xs text-gray-500">Latência ociosa / carregada</dt><dd className="tabular-nums font-medium">{r.velocidade ? `${dec(r.velocidade.latencia_ociosa_ms)} / ${dec(r.velocidade.latencia_carregada_ms)} ms` : 'fora do topo'}</dd></div>
      </dl>
      {r.velocidade && <p className="text-xs text-gray-500">Velocidade a partir de {n(r.velocidade.testes)} testes do speed.cloudflare.com (últimos 90 dias).</p>}
      <p className="text-xs text-gray-600" data-testid="radar-bgp">
        {papeis.length
          ? `Eventos de BGP nos últimos ${r.bgp_janela.janela_dias ?? 28} dias: ${papeis.map(([k, rot]) => `${rot} (${r.bgp?.[k as keyof typeof r.bgp]})`).join('; ')}. São eventos detectados pelo Radar: não provam intenção nem dano.`
          : `Nenhum evento de BGP do Radar envolvendo este AS nos últimos ${r.bgp_janela.janela_dias ?? 28} dias.`}
      </p>
      <Rodape b={r} />
    </div>
  )
}

/** Cloudflare Radar agregado na UF: DERIVADO dos ASNs pelo mapeamento ASN → UF; o Radar não tem recorte por UF. */
export function RadarUfBloco({ dados }: BlocoProps<{ radar?: RadarUf | null }>) {
  const r = dados.radar
  if (!r) return null
  const soma = PAPEIS.reduce((s, [k]) => s + (r.bgp?.[k as keyof typeof r.bgp] ?? 0), 0)
  return (
    <div className="space-y-3 text-sm" data-testid="radar-uf">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="radar-aviso">Agregado derivado dos ASNs da UF (mapeamento ASN → UF do projeto); o Radar não tem recorte por UF. {r.aviso}</p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        <div><dt className="text-xs text-gray-500">ASNs com IPv6 lido</dt><dd className="tabular-nums font-medium" data-testid="radar-uf-asns">{n(r.asns_com_ipv6)} de {n(r.asns)}</dd></div>
        <div><dt className="text-xs text-gray-500">Mediana de IPv6 entre os ASNs</dt><dd className="tabular-nums font-medium">{pct(r.ipv6_mediana_pct)}</dd></div>
        <div><dt className="text-xs text-gray-500">IPv6 ponderado pelo tráfego</dt><dd className="tabular-nums font-medium">{pct(r.ipv6_ponderado_pelo_trafego_pct)}</dd></div>
        <div><dt className="text-xs text-gray-500">ASNs no ponderado</dt><dd className="tabular-nums font-medium">{n(r.asns_no_ponderado)}</dd></div>
      </dl>
      <p className="text-xs text-gray-600" data-testid="radar-uf-bgp">
        {soma > 0 ? `Eventos de BGP dos ASNs da UF nos últimos ${r.bgp_janela.janela_dias ?? 28} dias: ${PAPEIS.filter(([k]) => (r.bgp?.[k as keyof typeof r.bgp] ?? 0) > 0).map(([k, rot]) => `${rot} (${r.bgp?.[k as keyof typeof r.bgp]})`).join('; ')}.` : 'Nenhum evento de BGP do Radar envolvendo ASNs da UF no período.'}
      </p>
      <Rodape b={r} />
    </div>
  )
}
