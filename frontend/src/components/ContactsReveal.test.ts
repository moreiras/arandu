import { describe, expect, it } from 'vitest'
import { notaRdap } from './ContactsReveal'

// a nota de proveniência do RDAP traz a data da leitura e a cobertura, sem valores de contato.
describe('notaRdap', () => {
  const cobertura = { asns_no_universo: 9140, com_leitura_valida: 1200, leitura_mais_antiga: '2026-11-10', leitura_mais_recente: '2026-11-17' }

  it('sem dado do RDAP não mostra nada', () => {
    expect(notaRdap(undefined)).toBeNull()
    expect(notaRdap({ leitura_em: null, tentou_em: null, status: null, cobertura: null })).toBeNull()
  })

  it('leitura válida: data do ASN e cobertura do rodízio', () => {
    const t = notaRdap({ leitura_em: '2026-11-12', tentou_em: '2026-11-12', status: 'completo', cobertura })
    expect(t).toContain('lido em 2026-11-12')
    expect(t).toContain('1.200 de 9.140 ASNs com contato lido')
    expect(t).toContain('leitura mais antiga em 2026-11-10')
  })

  it('só respostas incompletas: diz que não houve leitura completa, em vez de sugerir que o ASN não tem contato', () => {
    const t = notaRdap({ leitura_em: null, tentou_em: '2026-11-12', status: 'incompleto', cobertura })
    expect(t).toContain('sem leitura completa')
    expect(t).not.toContain('lido em')
  })
})
