// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AccessError } from '../../services/api'
import { EstadoDados, ehErroDeAcessoOuFalha, ehNaoEncontrado, estadoDoErro, formatarEspera } from './EstadoDados'

describe('estadoDoErro', () => {
  it('separa acesso, taxa, 404 e falha', () => {
    expect(estadoDoErro(new AccessError('login', 'x'))).toBe('login')
    expect(estadoDoErro(new AccessError('limit', 'x'))).toBe('orcamento')
    expect(estadoDoErro(new AccessError('taxa', 'x'))).toBe('taxa')
    expect(estadoDoErro(new Error('HTTP 404: não encontrado'))).toBe('sem-dado')
    expect(estadoDoErro(new Error('HTTP 500: boom'))).toBe('falha')
    expect(estadoDoErro(new TypeError('Failed to fetch'))).toBe('falha')
  })
  it('só o 404 é "não encontrado"; o resto impede de afirmar ausência', () => {
    expect(ehNaoEncontrado(new Error('HTTP 404: não encontrado'))).toBe(true)
    expect(ehNaoEncontrado(new Error('HTTP 4040'))).toBe(false)
    expect(ehErroDeAcessoOuFalha(new Error('HTTP 404: não encontrado'))).toBe(false)
    expect(ehErroDeAcessoOuFalha(new AccessError('taxa', 'x'))).toBe(true)
    expect(ehErroDeAcessoOuFalha(null)).toBe(false)
  })
  it('espera legível', () => {
    expect(formatarEspera(42)).toBe('42 s')
    expect(formatarEspera(600)).toBe('10 min')
    expect(formatarEspera(3600)).toBe('1 h')
  })
})

describe('EstadoDados', () => {
  it('carregando, vazio e sem dado são status e só estes afirmam algo sobre o dado', () => {
    const { rerender } = render(<EstadoDados estado="carregando" />)
    expect(screen.getByRole('status')).toHaveTextContent('Carregando…')
    rerender(<EstadoDados estado="vazio" mensagem="Nenhuma mudança com este filtro." />)
    expect(screen.getByRole('status')).toHaveTextContent('Nenhuma mudança com este filtro.')
    rerender(<EstadoDados erro={new Error('HTTP 404: não encontrado')} snapshot="2026-11-22" />)
    expect(screen.getByRole('status')).toHaveTextContent('Sem dado publicado no snapshot de 22/11/2026.')
  })

  it('401: pede login com o motivo da API e diz que não é ausência', () => {
    render(<EstadoDados erro={new AccessError('login', 'x', { reason: 'historico' })} />)
    const s = screen.getByRole('status')
    expect(s).toHaveTextContent('Entre para ver este dado')
    expect(s).toHaveTextContent('snapshots anteriores')
    expect(s).toHaveTextContent('isso não indica que ele não exista')
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', expect.stringMatching(/^\/login\?next=/))
  })

  it('orçamento esgotado (403 ou 429): mesma mensagem, com a espera quando vem', () => {
    const { rerender } = render(<EstadoDados erro={new AccessError('limit', 'x')} />)
    expect(screen.getByRole('status')).toHaveTextContent('Limite de uso sem login atingido')
    expect(screen.getByRole('status')).not.toHaveTextContent('volte em')
    rerender(<EstadoDados erro={new AccessError('limit', 'x', { retryAfter: 7200 })} />)
    expect(screen.getByRole('status')).toHaveTextContent('Entre gratuitamente para continuar ou volte em 2 h.')
  })

  it('429 de taxa: mensagem da API, espera e "Tentar de novo"', () => {
    const tentar = vi.fn()
    const { rerender } = render(<EstadoDados erro={new AccessError('taxa', 'Muitas consultas em pouco tempo.', { retryAfter: 30 })} aoTentarDeNovo={tentar} />)
    expect(screen.getByRole('status')).toHaveTextContent('Tente de novo em 30 s.')
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(tentar).toHaveBeenCalledOnce()
    rerender(<EstadoDados erro={new AccessError('taxa', 'Limite de uso por minuto atingido. Tente novamente em 30 s.', { retryAfter: 30 })} />)
    expect(screen.getByRole('status').textContent?.match(/30 s/g)).toHaveLength(1)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('500 e rede: alerta de falha, sem afirmar ausência', () => {
    render(<EstadoDados erro={new TypeError('Failed to fetch')} oQue="o perfil do AS64496" />)
    const a = screen.getByRole('alert')
    expect(a).toHaveTextContent('Não foi possível carregar o perfil do AS64496 agora')
    expect(a).not.toHaveTextContent(/não encontrad|sem dado/i)
  })

  it('variante de página usa h1 no título', () => {
    render(<EstadoDados variante="pagina" erro={new AccessError('limit', 'x')} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Limite de uso sem login atingido' })).toBeInTheDocument()
  })
})
