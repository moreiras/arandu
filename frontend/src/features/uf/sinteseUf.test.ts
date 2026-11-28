// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da UF (PT-22, uf 5.5): números do painel, selo por frase, sem juízo; DF sem a frase de distância; sem dado, sem frase. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import type { UfCtx } from './contexto'
import { sinteseUf } from './sinteseUf'

const base = (over: Partial<UfCtx['totais']> = {}, ixps = 1, penetracao: number | null = 0.58): UfCtx => ({
  uf: 'AM', ixps: new Array(ixps).fill({}), municipios: [], semCentroides: false, mesReferencia: '2026-09',
  totais: { municipios: 62, acessos: 724373, fibra_pct: 66.9, asns: 110, usuarios: 1000, municipios_sem_ptt: 55, acessos_sem_ptt: 142967, raio_sem_ptt_km: 100, ...over },
  territorio: penetracao === null ? undefined : { penetracao, mes_referencia_sici: '2026-09' },
  operadoras: [], operadorasTotal: 0, operadorasPresentes: [], operadorasPresentesTotal: 0,
} as unknown as UfCtx)

describe('sinteseUf', () => {
  it('AM: quatro frases na ordem mercado, domicílios, infraestrutura, rede, com selo e data', () => {
    const f = sinteseUf(base(), '2026-11-22')
    expect(f.map((x) => x.id)).toEqual(['acessos', 'penetracao', 'sem-ptt', 'rede'])
    expect(f[0].texto).toBe('Amazonas tem 724.373 acessos de banda larga fixa declarados ao SICI em 09/2026, em 62 municípios, e 66,9% deles são em fibra.')
    expect(f[0].selo).toBe('fato')
    expect(f[1].texto).toContain('58 acessos fixos para cada 100 domicílios')
    expect(f[1].selo).toBe('estimado')
    expect(f[2].texto).toContain('55 ficam a mais de 100 km em linha reta')
    expect(f[2].texto).toContain('142.967')
    expect(f[2].selo).toBe('estimado')
    expect(f[3].texto).toContain('1 PTT do IX.br')
    expect(f[3].texto).toContain('110 ASNs brasileiros com UF da sede conhecida')
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('DF (0 municípios longe) não ganha a frase de distância; sem PTT a frase de rede diz isso', () => {
    const f = sinteseUf(base({ municipios_sem_ptt: 0, acessos_sem_ptt: 0 }, 0), '2026-11-22')
    expect(f.some((x) => x.id === 'sem-ptt')).toBe(false)
    expect(f.find((x) => x.id === 'rede')!.texto).toMatch(/^Não há PTT do IX\.br na UF/)
  })

  it('sem SICI (acessos nulos) e sem território, só resta a frase de rede e a síntese some', () => {
    expect(sinteseUf(base({ acessos: null, municipios: null, fibra_pct: null, municipios_sem_ptt: null, acessos_sem_ptt: null }, 1, null), '2026-11-22')).toEqual([])
  })

  it('penetração pequena não vira zero falso e a fibra ausente some da frase', () => {
    const f = sinteseUf(base({ fibra_pct: null }, 1, 0.0033), '2026-11-22')
    expect(f[0].texto).not.toContain('fibra')
    expect(f.find((x) => x.id === 'penetracao')!.texto).toContain('0,3 acessos fixos')
  })
})

const op = (cnpj: string, empresa: string, share: number) => ({ cnpj, empresa, razao_social: empresa, uf_sede: 'AM', acessos: 1000, share, municipios: 3, acessos_brasil: 5000, asns: [64500] })

describe('sinteseUf: operadoras, ASNs sem sessão em PTT e CNPJs sem declaração (uf 5.5)', () => {
  const completo = () => {
    const c = base({ asns_sem_sessao_ptt: 67 } as never)
    c.operadorasPresentes = [op('00000000000191', 'Alfa Telecom', 38.4), op('00000000000272', 'Beta Redes', 21.05), op('00000000000353', 'Gama Net', 8), op('00000000000434', 'Delta', 2)] as never
    c.indicadores = { mes_referencia: '2026-09', metodologia: 'x', acessos: 724373, n_operadoras: 90, hhi: 1, sem_declaracao: { cnpjs_sem_declaracao: 307, com_usuarios_apnic: 10, sem_usuarios: 20, nao_comparavel: 277, usuarios_apnic: 5 } } as never
    return c
  }

  it('ordem fixa: mercado, domicílios, infraestrutura, rede e regulação, com as sete frases', () => {
    const f = sinteseUf(completo(), '2026-11-22')
    expect(f.map((x) => x.id)).toEqual(['acessos', 'operadoras', 'penetracao', 'sem-ptt', 'rede', 'sem-sessao', 'sem-declaracao'])
    for (const x of f) { expect(x.fonte).not.toBe(''); expect(x.dataRef).toBeTruthy(); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS); expect(x.texto).not.toMatch(/[—–]/) }
  })

  it('as três maiores por acessos declarados na UF: nomes, parcelas, mês, regra e link para o ranking completo na própria frase', () => {
    const f = sinteseUf(completo(), '2026-11-22').find((x) => x.id === 'operadoras')!
    expect(f.texto).toBe('Em 09/2026, as três operadoras com mais acessos fixos declarados ao SICI em Amazonas são Alfa Telecom (38,4% dos acessos declarados na UF), Beta Redes (21,1% dos acessos declarados na UF) e Gama Net (8% dos acessos declarados na UF). Regra: ordem decrescente dos acessos declarados na UF, um CNPJ por operadora, sem somar grupos econômicos.')
    expect(f.texto).not.toContain('Delta')
    expect(f.selo).toBe('fato')
    expect(f.link).toEqual({ to: '/operadoras?visao=ranking&uf=AM', rotulo: 'Ver o ranking completo da UF' })
  })

  it('com menos de três operadoras presentes não há ranking nominal', () => {
    const c = completo(); c.operadorasPresentes = c.operadorasPresentes.slice(0, 2)
    expect(sinteseUf(c, '2026-11-22').some((x) => x.id === 'operadoras')).toBe(false)
  })

  it('operadora sem nome cai no CNPJ (o nome de pessoa natural já vem pelo rótulo da API)', () => {
    const c = completo(); c.operadorasPresentes = [op('00000000000191', 'Empresário individual', 40), op('00000000000272', '', 20), op('00000000000353', 'Gama Net', 8)] as never
    c.operadorasPresentes[1].razao_social = ''
    const t = sinteseUf(c, '2026-11-22').find((x) => x.id === 'operadoras')!.texto
    expect(t).toContain('Empresário individual (40% ')
    expect(t).toContain('00.000.000/0002-72 (20% ')
  })

  it('ASNs sem sessão direta: N dos M, com a definição e o aviso de que a UF é a da sede', () => {
    const f = sinteseUf(completo(), '2026-11-22').find((x) => x.id === 'sem-sessao')!
    expect(f.texto).toContain('Dos 110 ASNs brasileiros com sede em Amazonas, 67 não têm sessão direta em PTT do IX.br.')
    expect(f.texto).toMatch(/Sessão direta é a sessão BGP do ASN com o route server/)
    expect(f.texto).toMatch(/a UF é a da sede, não a de operação/)
    expect(f.selo).toBe('fato')
    const um = completo(); um.totais.asns_sem_sessao_ptt = 1
    expect(sinteseUf(um, null).find((x) => x.id === 'sem-sessao')!.texto).toContain('1 não tem sessão direta')
  })

  it('sem o agregado (resposta antiga), sem a frase de ASNs; sem indicadores, sem a de CNPJs sem declaração', () => {
    const c = completo(); delete (c.totais as { asns_sem_sessao_ptt?: number }).asns_sem_sessao_ptt; c.indicadores = null
    const ids = sinteseUf(c, null).map((x) => x.id)
    expect(ids).not.toContain('sem-sessao')
    expect(ids).not.toContain('sem-declaracao')
  })

  it('CNPJs sem declaração: contagem, mês de referência e regra, sem causa nem intenção', () => {
    const f = sinteseUf(completo(), '2026-11-22').find((x) => x.id === 'sem-declaracao')!
    expect(f.texto).toBe('307 CNPJs com outorga SCM e sede em Amazonas não têm acessos declarados ao SICI em 09/2026. Regra: CNPJ com outorga SCM e sede na UF sem acessos declarados nesse mês; isso não indica causa nem intenção.')
    expect(f.dataRef).toBe('2026-09')
    const um = completo(); um.indicadores!.sem_declaracao!.cnpjs_sem_declaracao = 1
    expect(sinteseUf(um, null).find((x) => x.id === 'sem-declaracao')!.texto).toMatch(/^1 CNPJ com outorga SCM e sede em Amazonas não tem acessos/)
  })
})

