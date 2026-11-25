// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Migalhas } from '../../components/layout/Migalhas'
import { EntityHeader, type SeloServico } from '../../components/entidade'
import type { PrefixoInfo } from '../../services/api'

/** Selo de escopo, em texto: de onde vem a página (alocação do Registro.br ou rota observada). */
function seloEscopo(info: PrefixoInfo): SeloServico | null {
  switch (info.escopo) {
    case 'alocacao_registro_br': return { rotulo: 'Alocação do Registro.br' }
    case 'rota_dentro_de_alocacao': return { rotulo: `Rota anunciada dentro de ${info.alocacao_registro_br}`, titulo: `Alocação do Registro.br ao AS${info.registro_asn}` }
    case 'fora_do_registro_br': return { rotulo: 'Rota anunciada, fora das alocações do Registro.br' }
    default: return null
  }
}

export function CabecalhoPrefixo({ info }: { info: PrefixoInfo }) {
  const escopo = seloEscopo(info)
  return (
    <EntityHeader
      trilha={<Migalhas grupo="rede" itens={[{ rotulo: 'Prefixos' }, { rotulo: info.prefix, mono: true }]} />}
      nome={info.prefix}
      selos={[{ rotulo: `IPv${info.ip_version}`, tom: info.ip_version === 6 ? 'laranja' : 'azul' }, ...(escopo ? [escopo] : [])]}
      snapshot={info.snapshot_date}
    />
  )
}
