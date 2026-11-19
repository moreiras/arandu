// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Navigate } from 'react-router-dom'

/** `/panorama/ipv6` virou a aba IPv6 do Panorama técnico: a rota segue como alias (regra 8 do AGENTS.md). */
export function PanoramaIpv6() {
  return <Navigate replace to="/panorama/tecnico?aba=ipv6" />
}
