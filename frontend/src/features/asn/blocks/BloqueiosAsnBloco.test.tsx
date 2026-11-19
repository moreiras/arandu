// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BloqueiosAsnBloco } from './BloqueiosAsnBloco'
import type { BloqueiosAsn } from '../../../types/api'

const b: BloqueiosAsn = {
  snapshot_date: '2026-11-05', coletado_em: '2026-11-07T10:00:00Z', licenca: 'CC BY-NC-SA 4.0', minimo_medicoes: 10,
  aviso: 'Veredito da PRÓPRIA sonda do OONI; não é prova de censura.', limites: 'Sondas são de voluntários.',
  fonte: { nome: 'OONI', atribuicao: 'Dados: OONI (https://ooni.org), CC BY-NC-SA 4.0.', licenca_url: 'https://creativecommons.org/licenses/by-nc-sa/4.0/' },
  janela: { inicio: '2026-10-30', fim: '2026-11-05', dias_com_dado: 7, dias_da_janela: 28 },
  testes: [
    { teste: 'whatsapp', rotulo: 'WhatsApp', n: 120, anomalias: 6, pct_anomalia: 5, criterio: 'A sonda declarou bloqueado o WhatsApp Web.' },
    { teste: 'webconnectivity', rotulo: 'Web Connectivity (amostra)', n: 900, anomalias: 18, pct_anomalia: 2, criterio: 'Amostra de horas.', amostra: true },
  ],
}

describe('bloco Bloqueios (OONI) do ASN', () => {
  it('mostra o aviso de veredito da sonda, a licença com atribuição e nunca fala em censura confirmada', () => {
    render(<BloqueiosAsnBloco {...({ dados: { bloqueios: b } } as any)} />)
    expect(screen.getByTestId('bloqueios-aviso').textContent).toMatch(/PRÓPRIA sonda/)
    expect(screen.getByTestId('bloqueios-licenca').textContent).toMatch(/OONI/)
    expect(screen.getByText('CC BY-NC-SA 4.0').getAttribute('href')).toContain('creativecommons.org')
    expect(screen.getByText('WhatsApp')).toBeTruthy()
    expect(screen.getByText(/6 \(5%\)/)).toBeTruthy()
    expect(screen.getByText(/ausência de um teste não quer dizer ausência de bloqueio/)).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/censura confirmada|bloqueado pela operadora/i)
  })

  it('não renderiza nada sem o bloco', () => {
    const { container } = render(<BloqueiosAsnBloco {...({ dados: { bloqueios: null } } as any)} />)
    expect(container.textContent).toBe('')
  })
})
