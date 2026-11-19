// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import {
  cnpjLine, formatCnpj, htmlAsn, htmlCaboSubmarino, htmlEnlaceTerrestre, htmlErbs, htmlLinhaTransmissao, htmlPix, htmlPontoAterrissagem, htmlPrefixo, htmlRodovia, htmlScm,
} from './popups'

describe('balões do mapa', () => {
  it('CNPJ formatado só com 14 dígitos; linha de CNPJ vira link da operadora', () => {
    expect(formatCnpj('12345678000190')).toBe('12.345.678/0001-90')
    expect(formatCnpj('123')).toBe('123')
    expect(cnpjLine('12345678000190')).toContain('href="/operadora/12345678000190"')
    expect(cnpjLine(null)).toBe('')
  })

  it('PIX: nome do PTT e do ponto', () => {
    expect(htmlPix({ ixp_name: 'São Paulo', name: 'Equinix SP4' })).toBe('<strong>PIX São Paulo</strong><br/><span style="font-size:.88em;color:#555">Equinix SP4</span>')
    expect(htmlPix({ ixp_code: 'sp' })).toBe('<strong>PIX sp</strong>')
  })

  it('sede de AS: badge SCM, local, nomes distintos e rótulo da dimensão de cor', () => {
    const h = htmlAsn({ asn: 64500, has_scm: true, city: 'Vitória', uf: 'ES', name: 'Exemplo', razao_social: 'Exemplo Telecom Ltda', nome_fantasia: 'Exemplo', cnpj: '12345678000190', color_value: 'yes' }, 'rpki')
    expect(h).toContain('<strong>AS64500</strong>')
    expect(h).toContain('>SCM</span>')
    expect(h).toContain(' · Vitória/ES')
    expect(h).toContain('Anatel: Exemplo Telecom Ltda')
    expect(h).not.toContain('fantasia:')                              // igual ao nome: não repete
    expect(h).toContain('Tem RPKI')
    expect(htmlAsn({ asn: 1 }, 'solid')).toBe('<strong>AS1</strong><br/>')
  })

  it('prefixo BR: origem única com nome e CNPJ; prefixo de PTT: lista de origens e de peers do JSON do MapLibre', () => {
    const br = htmlPrefixo({ prefix_count: 3, city: 'Vitória', uf: 'ES', country: 'BR', origin_asn: 64500, origin_name: 'Exemplo', origin_cnpj: '12345678000190' })
    expect(br).toContain('<strong>3 prefixos</strong> · Vitória / ES / BR')
    expect(br).toContain('<b>Origem:</b> AS64500 · Exemplo')
    expect(br).toContain('12.345.678/0001-90')
    const ptt = htmlPrefixo({ block_count: 12, origin_asns: '[1,2,3,4,5,6,7,8]', peer_asns: '[9]' })
    expect(ptt).toContain('<strong>12 blocos</strong>')
    expect(ptt).toContain('AS1, AS2, AS3, AS4, AS5, AS6 +2')          // no máximo 6, com o resto resumido
    expect(ptt).toContain('<b>Peers PTT:</b> AS9')
  })

  it('JSON de origens quebrado não derruba o balão e mantém a origem única', () => {
    expect(htmlPrefixo({ prefix: 'x', origin_asn: 5, origin_asns: '{quebrado' })).toContain('AS5')
    expect(htmlPrefixo({ prefix: 'x', peer_asns: 'lixo' })).not.toContain('Peers PTT')
  })

  it('outorga SCM: com e sem ASN, sem repetir a razão como fantasia nem "N/I"', () => {
    const com = htmlScm({ razao_social: 'Provedor X', municipio: 'Serra', uf: 'ES', cnpj: '12345678000190', nome_fantasia: 'X Net', asns: '[64500,64501]' })
    expect(com).toContain('<strong>Provedor X</strong>')
    expect(com).toContain('fantasia: X Net')
    expect(com).toContain('AS64500, AS64501')
    const sem = htmlScm({ razao_social: 'Provedor Y', nome_fantasia: 'N/I' })
    expect(sem).not.toContain('fantasia')
    expect(sem).toContain('Outorga SCM sem ASN no BGP')
  })

  it('infraestrutura: enlace, cabo, ponto de aterrissagem, linha de transmissão e rodovia', () => {
    expect(htmlEnlaceTerrestre({ type_inf: 'Fibra', status: 'Operacional' })).toContain('ITU BBmaps · Operacional')
    expect(htmlEnlaceTerrestre({})).toContain('Enlace terrestre')
    expect(htmlCaboSubmarino({ name: 'Monet', length: '10.556 km', rfs_year: 2017, owners: 'Google' })).toBe(
      '<strong>Monet</strong><br/><span style="font-size:.82em;color:#555">10.556 km · RFS 2017</span><br/><span style="font-size:.78em;color:#9ca3af">Google</span>')
    expect(htmlPontoAterrissagem({ name: 'Fortaleza', is_tbd: true })).toContain('(planejado)')
    expect(htmlLinhaTransmissao({ subestacao_origem: 'A', subestacao_destino: 'B', tensao_kv: 500, extensao_km: 120 })).toContain('A / B')
    expect(htmlLinhaTransmissao({})).toContain('Linha de transmissão')
    expect(htmlRodovia({ sigla: 'BR-101', jurisdicao: 'Federal', revestimento: 'Pavimentada' })).toContain('BR-101')
    expect(htmlRodovia({})).toContain('Rodovia')
  })
})

describe('htmlErbs', () => {
  it('conta as estações da célula por geração e avisa que é cadastro, não cobertura', () => {
    const h = htmlErbs({ estacoes: 12, g2: 0, g3: 3, g4: 12, g5: 5 })
    expect(h).toContain('12 estações licenciadas')
    expect(h).toContain('3G 3 · 4G 12 · 5G 5')
    expect(h).not.toContain('2G')
    expect(h).toContain('não é cobertura')
    expect(htmlErbs({ estacoes: 1 })).toContain('1 estação licenciada')
  })
})
