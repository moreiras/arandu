// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Migalhas } from '../../components/layout/Migalhas'
import { EntityHeader } from '../../components/entidade'
import type { PrefixoInfo } from '../../services/api'

export function CabecalhoPrefixo({ info }: { info: PrefixoInfo }) {
  return (
    <EntityHeader
      trilha={<Migalhas grupo="rede" itens={[{ rotulo: 'Prefixos' }, { rotulo: info.prefix, mono: true }]} />}
      nome={info.prefix}
      selos={[{ rotulo: `IPv${info.ip_version}`, tom: info.ip_version === 6 ? 'laranja' : 'azul' }]}
      snapshot={info.snapshot_date}
    />
  )
}
