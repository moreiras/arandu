// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { Section } from './Section'
import { Kpi } from '../ui/Kpi'
import { useAppStore } from '../../store/app'

beforeEach(() => { useAppStore.setState({ snapshotsAtuais: ['2026-11-15', '2026-11-22'] }) })

function bloco(snapshot: string) {
  return render(
    <MemoryRouter initialEntries={['/municipio/3205309']}>
      <Section id="bloco-acessos" titulo="Acessos" proveniencia={{ fontes: ['anatel_sici'] }} fontes={[{ id: 'anatel_sici', as_of: '2026-09' }]} snapshot={snapshot}
        citacao={{ entidade: 'Município de Vitória/ES', bloco: 'Acessos', blocoId: 'acessos' }}>
        <Kpi rotulo="Acessos fixos" valor="123.456" />
        <Kpi rotulo="Operadoras" valor="12" />
        <Kpi rotulo="Sem dado" valor={null} />
      </Section>
    </MemoryRouter>,
  )
}

describe('Citar este dado (D3)', () => {
  it('o texto traz os valores que o bloco mostra, o snapshot e a fonte com a data', () => {
    bloco('2026-11-22')
    const texto = (screen.getByLabelText('Texto de citação') as HTMLTextAreaElement).value
    expect(texto).toContain('Valores: Acessos fixos: 123.456; Operadoras: 12.')
    expect(texto).not.toContain('Sem dado')
    expect(texto).toContain('anatel_sici (referência 09/2026)')
    expect(texto).toContain('Snapshot de 22/11/2026.')
    expect(texto).toContain('?date=2026-11-22#bloco-acessos')
  })

  it('o aviso diz que o link abre sem login só enquanto o snapshot é recente e indica o prazo', () => {
    bloco('2026-11-22')
    expect(screen.getByTestId('aviso-link-citacao').textContent).toMatch(/abre sem login enquanto o snapshot de 22\/11\/2026 estiver entre os dois mais recentes \(hoje: 15\/11\/2026 e 22\/11\/2026\).*duas semanas.*Depois exige login/)
  })

  it('snapshot que já saiu dos recentes: o aviso diz que o link exige login', () => {
    bloco('2026-11-08')
    expect(screen.getByTestId('aviso-link-citacao').textContent).toMatch(/já não está entre os dois mais recentes.*exige login/)
  })

  it('os valores são relidos da tela quando o detalhe abre (o bloco carrega depois)', () => {
    bloco('2026-11-22')
    const detalhe = screen.getByTestId('proveniencia-compacta') as HTMLDetailsElement
    fireEvent(detalhe, new Event('toggle'))
    expect((screen.getByLabelText('Texto de citação') as HTMLTextAreaElement).value).toContain('Acessos fixos: 123.456')
  })
})
