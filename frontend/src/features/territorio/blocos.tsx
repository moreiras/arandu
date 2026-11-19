// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../entidade/registry'
import type { MunicipioCtx } from '../municipio/contexto'
import type { UfCtx } from '../uf/contexto'
import { PenetracaoBloco } from './PenetracaoBloco'

/** Registros `.ts` não têm JSX: os blocos de penetração das páginas de município e UF moram aqui. */
export const PenetracaoMunicipio = ({ dados }: BlocoProps<MunicipioCtx>) => <PenetracaoBloco t={dados.territorio!} rotuloTerritorio="o município" />
export const PenetracaoUf = ({ dados }: BlocoProps<UfCtx>) => <PenetracaoBloco t={dados.territorio!} rotuloTerritorio="a UF" />
