// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RadarAsnBloco, RadarUfBloco } from './blocos'
import type { RadarAsn, RadarUf } from '../../types/api'

const comum = {
  snapshot_date: '2026-11-09', coletado_em: '2026-11-09T12:30:00Z', licenca: 'CC BY-NC 4.0', aviso: 'Mede quem usa a Cloudflare, não a rede toda.', limites: 'Rodízio de dias.', janela_ipv6: '28d',
  cobertura: { asns_do_brasil_no_snapshot: 9100, asns_na_lista_do_radar: 9207, asns_com_leitura_ipv6: 1400, asns_com_dado_ipv6: 1350, leitura_mais_antiga: '2026-11-08', leitura_mais_recente: '2026-11-09', asns_no_topo_de_trafego: 300, asns_com_velocidade: 179 },
  fonte: { nome: 'Cloudflare Radar', atribuicao: 'Dados: Cloudflare Radar, CC BY-NC 4.0.', licenca_url: 'https://creativecommons.org/licenses/by-nc/4.0/' },
  bgp_janela: { janela_dias: 28, em: '2026-11-09', vazamentos_com_asn_do_brasil: 1248, sequestros_com_asn_do_brasil: 141, criterio: 'por papel' },
  quedas: { janela: '52w', anomalias: 0, anotacoes: 0, consultado: true, em: '2026-11-09' },
}
const asn = (o: Partial<RadarAsn>): RadarAsn => ({ ...comum, asn: 64496, ...o })
const uf = (o: Partial<RadarUf>): RadarUf => ({ ...comum, uf: 'ES', asns: 40, asns_com_ipv6: 12, ipv6_mediana_pct: 31.5, ipv6_ponderado_pelo_trafego_pct: 62.25, asns_no_ponderado: 3,
  bgp: { vazou: 0, no_caminho_de_vazamento: 0, sequestrou: 0, vitima_de_sequestro: 0 }, derivado: true, ...o })

describe('Cloudflare Radar no ASN', () => {
  it('mostra IPv6 com a data da leitura, tráfego, velocidade e papéis de BGP, com licença e cobertura', () => {
    render(<RadarAsnBloco dados={{ radar: asn({ ipv6: { pct: 55.5, em: '2026-11-09' }, trafego_pct_do_brasil: 8, velocidade: { download_mbps: 250.5, upload_mbps: 120.25, latencia_ociosa_ms: 9.5, latencia_carregada_ms: 20, testes: 321 }, bgp: { vazou: 1, vitima_de_sequestro: 1 } }) } as never} snapshot={null} />)
    expect(screen.getByTestId('radar-ipv6')).toHaveTextContent('55,5% (lido em 09/11/2026)')
    expect(screen.getByText(/250,5 \/ 120,3 Mbps|250,5 \/ 120,2 Mbps/)).toBeInTheDocument()
    expect(screen.getByTestId('radar-bgp')).toHaveTextContent('vazou rotas (1); teve prefixo sequestrado (1)')
    expect(screen.getByTestId('radar-bgp')).toHaveTextContent('não provam intenção nem dano')
    expect(screen.getByTestId('radar-cobertura')).toHaveTextContent('1.350 de 9.100 ASNs do Brasil com IPv6 lido')
    expect(screen.getByTestId('radar-licenca')).toHaveTextContent('CC BY-NC 4.0')
  })
  it('ausência não vira zero: sem IPv6, tráfego nem velocidade o bloco diz "sem leitura" e "fora do topo"', () => {
    render(<RadarAsnBloco dados={{ radar: asn({}) } as never} snapshot={null} />)
    expect(screen.getByTestId('radar-ipv6')).toHaveTextContent('sem leitura')
    expect(screen.getAllByText('fora do topo')).toHaveLength(3)
    expect(screen.getByTestId('radar-bgp')).toHaveTextContent('Nenhum evento de BGP do Radar envolvendo este AS')
  })
  it('zero medido de IPv6 é dado e aparece como 0%', () => {
    render(<RadarAsnBloco dados={{ radar: asn({ ipv6: { pct: 0, em: '2026-11-09' } }) } as never} snapshot={null} />)
    expect(screen.getByTestId('radar-ipv6')).toHaveTextContent('0% (lido em 09/11/2026)')
  })
  it('não renderiza sem o produto', () => {
    const { container } = render(<RadarAsnBloco dados={{} as never} snapshot={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('Cloudflare Radar na UF', () => {
  it('rotula o agregado como derivado e mostra mediana, ponderado e cobertura', () => {
    render(<RadarUfBloco dados={{ radar: uf({ bgp: { vazou: 2, no_caminho_de_vazamento: 0, sequestrou: 0, vitima_de_sequestro: 1 } }) } as never} snapshot={null} />)
    expect(screen.getByTestId('radar-aviso')).toHaveTextContent('Agregado derivado dos ASNs da UF')
    expect(screen.getByTestId('radar-uf-asns')).toHaveTextContent('12 de 40')
    expect(screen.getByText('31,5%')).toBeInTheDocument()
    expect(screen.getByText('62,3%')).toBeInTheDocument()
    expect(screen.getByTestId('radar-uf-bgp')).toHaveTextContent('vazou rotas (2); teve prefixo sequestrado (1)')
  })
  it('sem ponderado mostra travessão, não zero', () => {
    render(<RadarUfBloco dados={{ radar: uf({ ipv6_mediana_pct: null, ipv6_ponderado_pelo_trafego_pct: null, asns_com_ipv6: 0, asns_no_ponderado: 0 }) } as never} snapshot={null} />)
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2)
  })
})
