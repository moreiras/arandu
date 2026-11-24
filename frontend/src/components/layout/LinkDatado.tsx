// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { forwardRef } from 'react'
import { Link as LinkDoRoteador, useSearchParams, type LinkProps } from 'react-router-dom'
import { comData } from '../../lib/dataAtiva'

/**
 * O `Link` do site: o de react-router-dom com a data do snapshot da página atual (`?date=`) no destino interno. Quem lê o ASN em
 * 2026-11-15 e clica no PTT continua em 2026-11-15, e o endereço do link (copiar, abrir em nova aba) também leva a data.
 * Sem `date` na URL atual o destino fica como está (snapshot mais recente). Destino que já traz `date` não muda.
 */
export const Link = forwardRef<HTMLAnchorElement, LinkProps>(function Link({ to, ...resto }, ref) {
  const [params] = useSearchParams()
  const destino = typeof to === 'string' ? comData(to, params.get('date')) : to
  return <LinkDoRoteador ref={ref} to={destino} {...resto} />
})
