// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExposicaoAsnBloco, ExposicaoUfBloco } from './blocos'
import type { ExposicaoAsn, ExposicaoUf } from '../../types/api'

const comum = {
  snapshot_date: '2026-11-10', coletado_em: '2026-11-10T12:30:00Z', licenca: 'Shodan (API principal): uso em produtos com atribuição', aviso: 'NÃO é prova de vulnerabilidade; ASN sem leitura não é zero.',
  limites: 'Rodízio: cada ASN tem a sua data de leitura.',
  cobertura: { asns_do_brasil_no_snapshot: 9100, asns_com_leitura: 1500, asns_com_servicos_observados: 900, leitura_mais_antiga: '2026-11-09', leitura_mais_recente: '2026-11-10' },
  fonte: { nome: 'Shodan', atribuicao: 'Dados: Shodan (https://www.shodan.io), contagens por ASN.' },
  plano: { facetas: { port: 'ok', vuln: 'indisponivel' } },
  classes_de_risco: { acesso_remoto: { rotulo: 'Acesso remoto', portas: [{ porta: 23, servico: 'Telnet' }] }, gestao_de_equipamento: { rotulo: 'Gestão de roteador/CPE', portas: [{ porta: 7547, servico: 'TR-069 (CWMP)' }] } },
}
const asn = (o: Partial<ExposicaoAsn>): ExposicaoAsn => ({ ...comum, asn: 64496, lido_em: '2026-11-10', servicos_observados: 400, ...o })
const uf = (o: Partial<ExposicaoUf>): ExposicaoUf => ({ ...comum, uf: 'ES', asns_do_cadastro: 40, asns_com_leitura: 12, asns_com_servicos_observados: 9, servicos_observados: 1000, servicos_de_risco: 80,
  pct_de_servicos_de_risco: 8, classes: { acesso_remoto: 60, gestao_de_equipamento: 20 }, servicos_de_risco_por_servico: { Telnet: 60, 'TR-069 (CWMP)': 20 }, derivado: true, ...o })

describe('Exposição de serviços no ASN', () => {
  it('mostra serviços, portas de risco por classe, plano sem CVE e a atribuição ao Shodan', () => {
    render(<ExposicaoAsnBloco dados={{ exposicao: asn({
      portas_mais_vistas: [{ porta: 80, n: 220 }, { porta: 23, n: 40 }],
      risco: { servicos_de_risco: 51, pct_dos_servicos_observados: 12.75, classes: { acesso_remoto: { total: 42, servicos: [{ porta: 23, servico: 'Telnet', n: 40 }, { porta: 3389, servico: 'RDP', n: 2 }] } } },
      vulnerabilidades: { disponivel: false, nota: 'não disponível no plano da conta do Shodan' },
    }) } as never} snapshot={null} />)
    expect(screen.getByTestId('exposicao-aviso')).toHaveTextContent('NÃO é prova de vulnerabilidade')
    expect(screen.getByTestId('exposicao-total')).toHaveTextContent('400 (lido em 10/11/2026)')
    expect(screen.getByTestId('exposicao-risco')).toHaveTextContent('51 (12,75%)')
    expect(screen.getByTestId('exposicao-classes')).toHaveTextContent('Acesso remoto: 42 — Telnet (23): 40; RDP (3389): 2')
    expect(screen.getByTestId('exposicao-vuln')).toHaveTextContent('não disponível no plano')
    expect(screen.getByTestId('exposicao-cobertura')).toHaveTextContent('1.500 de 9.100 ASNs do Brasil já consultados')
    expect(screen.getByTestId('exposicao-atribuicao')).toHaveTextContent('Dados: Shodan')
  })
  it('zero observado diz que o Shodan não viu serviço e não afirma que não há serviço', () => {
    render(<ExposicaoAsnBloco dados={{ exposicao: asn({ servicos_observados: 0, sem_servico_observado: true }) } as never} snapshot={null} />)
    expect(screen.getByTestId('exposicao-vazio')).toHaveTextContent('Isso não prova que não há serviço exposto')
  })
  it('lista as CVEs quando o plano as tem e avisa que não provam a falha', () => {
    render(<ExposicaoAsnBloco dados={{ exposicao: asn({ vulnerabilidades: { disponivel: true, cves_mais_vistas: [{ cve: 'CVE-2099-0001', n: 12 }] } }) } as never} snapshot={null} />)
    expect(screen.getByTestId('exposicao-vuln')).toHaveTextContent('CVE-2099-0001 (12)')
    expect(screen.getByTestId('exposicao-vuln')).toHaveTextContent('não provam a falha')
  })
  it('não renderiza sem o produto (ASN sem leitura não vira bloco zerado)', () => {
    const { container } = render(<ExposicaoAsnBloco dados={{} as never} snapshot={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('Exposição de serviços na UF', () => {
  it('rotula o agregado como derivado e mostra a cobertura e os totais por classe', () => {
    render(<ExposicaoUfBloco dados={{ exposicao: uf({}) } as never} snapshot={null} />)
    expect(screen.getByTestId('exposicao-aviso')).toHaveTextContent('Agregado derivado dos ASNs da UF já lidos')
    expect(screen.getByTestId('exposicao-uf-asns')).toHaveTextContent('12 de 40')
    expect(screen.getByTestId('exposicao-uf-risco')).toHaveTextContent('80 (8%)')
    expect(screen.getByTestId('exposicao-uf-classes')).toHaveTextContent('Acesso remoto: 60; Gestão de roteador/CPE: 20')
  })
  it('sem serviço observado o percentual é travessão, não zero', () => {
    render(<ExposicaoUfBloco dados={{ exposicao: uf({ servicos_observados: 0, servicos_de_risco: 0, pct_de_servicos_de_risco: null, classes: {}, servicos_de_risco_por_servico: {} }) } as never} snapshot={null} />)
    expect(screen.getByTestId('exposicao-uf-risco')).toHaveTextContent('0 (—)')
  })
})
