// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { SinteseTopo } from '../../../components/ui/SinteseTopo'
import type { BlocoProps } from '../../entidade/registry'
import { fetchIXPs } from '../../../services/api'
import type { PttCtx } from '../contexto'
import { REGRAS_SINTESE_PTT, sinteseIxp } from '../sinteseIxp'

/** Síntese no topo da página do PTT. A lista dos PTTs (`/ixps`, aberta) é a mesma que a tabela de PTTs e o destaque usam: mesma chave, uma busca só. */
export function SinteseBloco({ dados, snapshot }: BlocoProps<PttCtx>) {
  const date = dados.date ?? undefined
  const lista = useQuery({ queryKey: ['ixps', dados.date], queryFn: () => fetchIXPs(date), staleTime: Infinity, gcTime: Infinity, retry: false })
  return <SinteseTopo frases={sinteseIxp(dados, dados.ixp?.name ?? dados.code.toUpperCase(), lista.data?.ixps)} snapshot={snapshot ?? dados.date} regras={REGRAS_SINTESE_PTT} />
}
