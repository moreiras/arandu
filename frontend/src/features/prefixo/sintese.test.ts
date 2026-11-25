// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import type { PrefixoInfo, RpkiObservado } from '../../services/api'
import { sintesePrefixo } from './sintese'

const rpki = (estado: RpkiObservado['estado'], motivo: RpkiObservado['motivo'] = null, asns: number[] = []): RpkiObservado =>
  ({ estado, motivo, asn: 64503, roas_que_cobrem: asns.map((asn) => ({ prefix: '198.18.0.0/21', asn, maxLength: 21, ta: 'lacnic', autoriza_origem: false })) })

const base = {
  prefix: '198.18.0.0/21', ip_version: 4, origin_asn: 64502, escopo: 'alocacao_registro_br', alocacao_registro_br: '198.18.0.0/21',
  registro_asn: 64502, registro_asn_nome: 'Provedor 07 Telecom Ltda', observed_origin_asn: 64503, observed_origin_nome: 'Provedor 08 Telecom Ltda',
  observed_origin_fonte: 'tabela_global', rpki_observado: rpki('invalid', 'origem_diferente', [64502]),
  uf: 'ES', snapshot_date: '2026-09-20', geo_org: { name: 'Provedor 07 Telecom Ltda' },
} as PrefixoInfo

describe('síntese do prefixo (sintese-prefixo-2)', () => {
  it('detentor e origem observada em frases separadas; RPKI do par anunciado (PFX-E1/E2)', () => {
    const f = sintesePrefixo(base)
    expect(f.map((x) => [x.id, x.selo])).toEqual([['detentor', 'fato'], ['origem', 'fato'], ['rpki', 'fato'], ['geo', 'inferido']])
    expect(f[0].texto).toBe('Alocado pelo Registro.br ao AS64502 (Provedor 07 Telecom Ltda).')
    expect(f[1].texto).toBe('Anunciado na tabela global coletada com origem AS64503 (Provedor 08 Telecom Ltda), diferente do AS do Registro.br.')
    expect(f[2].texto).toContain('autorizam AS64502')
    expect(f.map((x) => x.texto).join(' ')).not.toMatch(/originado pelo AS64502/)
  })
  it('mesmo AS, maxLength excedido, sem ROA', () => {
    const igual = sintesePrefixo({ ...base, observed_origin_asn: 64502, rpki_observado: rpki('valid') })
    expect(igual[1].texto).toContain('o mesmo AS do Registro.br')
    expect(igual[2].texto).toBe('A origem observada tem ROA válido.')
    expect(sintesePrefixo({ ...base, rpki_observado: rpki('invalid', 'maxlength_excedido', [64503]) })[2].texto).toContain('maxLength menor que /21')
    expect(sintesePrefixo({ ...base, rpki_observado: rpki('not_found', 'sem_roa') })[2].texto).toContain('Nenhum ROA')
  })
  it('sem anúncio: não afirma origem e não valida o par', () => {
    const f = sintesePrefixo({ ...base, observed_origin_asn: null, observed_origin_fonte: null, rpki_observado: { ...rpki('nao_avaliado', 'sem_anuncio'), asn: null } })
    expect(f[1].texto).toContain('não é anunciado como está')
    expect(f[2].texto).toContain('RPKI não avaliado')
    expect(f.map((x) => x.texto).join(' ')).not.toMatch(/inválida|válido/)
  })
  it('rota fora do Registro.br e rota dentro de uma alocação', () => {
    const fora = sintesePrefixo({ ...base, escopo: 'fora_do_registro_br', registro_asn: null, alocacao_registro_br: null, origin_asn: null, uf: null, geo_org: null })
    expect(fora[0].texto).toContain('não está dentro de nenhuma alocação do Registro.br')
    expect(fora[1].texto).not.toContain('Registro.br')
    const dentro = sintesePrefixo({ ...base, prefix: '198.18.4.0/24', escopo: 'rota_dentro_de_alocacao' })
    expect(dentro[0].texto).toBe('Dentro de 198.18.0.0/21, alocado pelo Registro.br ao AS64502 (Provedor 07 Telecom Ltda).')
  })
})
