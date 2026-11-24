// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Busca de lugar do localizador: homônimo sem UF não vira um ponto entre as UFs (LOC-E4). */
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { server } from '../../test/server'
import { LugarAmbiguo, geocodeQuery } from './useLocalizadorDados'

describe('geocodeQuery (LOC-E4)', () => {
  it('"Bom Jesus" sem UF: erro com as UFs, sem coordenada', async () => {
    server.use(http.get('*/api/v1/resolve/place', () => HttpResponse.json({ snapshot_date: 'd', place: 'Bom Jesus', ambiguo: true, ufs: { PI: 3, RN: 2 }, lat: null, lon: null, n: 5 })))
    const e = await geocodeQuery('Bom Jesus').catch((x) => x)
    expect(e).toBeInstanceOf(LugarAmbiguo)
    expect((e as LugarAmbiguo).ufs).toEqual(['PI', 'RN'])
  })

  it('"Bom Jesus/PI" vai à API como digitado e devolve o ponto', async () => {
    let pedido = ''
    server.use(http.get('*/api/v1/resolve/place', ({ request }) => {
      pedido = new URL(request.url).searchParams.get('q') ?? ''
      return HttpResponse.json({ snapshot_date: 'd', place: pedido, uf: 'PI', lat: -9.07, lon: -44.36, n: 3 })
    }))
    expect(await geocodeQuery('Bom Jesus/PI')).toEqual([-9.07, -44.36])
    expect(pedido).toBe('Bom Jesus/PI')
  })

  it('404 continua "não encontrado" (null)', async () => {
    server.use(http.get('*/api/v1/resolve/place', () => HttpResponse.json({ detail: 'x' }, { status: 404 })))
    expect(await geocodeQuery('Lugar Inexistente')).toBeNull()
  })
})
