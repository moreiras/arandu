// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { AccessError } from './api'
import { deveRepetir } from './queryClient'

describe('política de nova tentativa', () => {
  it('4xx e erro de política não se repetem; rede e 5xx, uma vez', () => {
    expect(deveRepetir(0, new Error('HTTP 404: não encontrado'))).toBe(false)
    expect(deveRepetir(0, new Error('HTTP 422: {"detail":[]}'))).toBe(false)
    expect(deveRepetir(0, new AccessError('limit', 'acabou'))).toBe(false)
    expect(deveRepetir(0, new Error('HTTP 500'))).toBe(true)
    expect(deveRepetir(0, new TypeError('Failed to fetch'))).toBe(true)
    expect(deveRepetir(1, new Error('HTTP 500'))).toBe(false)
  })
})
