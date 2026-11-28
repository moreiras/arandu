// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { fetchUfs } from '../../../services/api'
import { useActiveDate } from '../../../hooks/useSnapshot'
import { n0, n1 } from '../../../lib/sintese'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { KPI, fmt } from '../../municipio/ui'

/**
 * Usuários estimados (APNIC) dos ASNs com sede na UF, na aba Rede (UF 5.5): saiu do topo porque a leitura de "usuários da UF" engana. O número conta na UF da sede
 * do ASN, não onde o usuário está, e por isso pode passar do que a UF tem de acessos (SP, sede de redes que atendem o país). Parcela do Brasil calculada das mesmas
 * linhas de `/ufs` (a mesma consulta dos cartões do painel).
 */
export function UsuariosSedeUfBloco({ dados }: BlocoProps<UfCtx>) {
  const date = useActiveDate()
  const q = useQuery({ queryKey: ['ufs', date], queryFn: () => fetchUfs(date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
  const total = (q.data?.items ?? []).reduce((t, u) => t + (u.usuarios ?? 0), 0)
  const parcela = total > 0 ? `${n1((100 * dados.totais.usuarios) / total)}% do total das 27 UFs (${n0(total)})` : ''
  return (
    <div className="space-y-2" data-testid="usuarios-sede-uf">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <KPI label="Usuários estimados em ASNs sediados na UF" value={fmt(dados.totais.usuarios)} referencia={parcela}
          hint={`APNIC, ${fmt(dados.totais.asns)} ASNs brasileiros com sede na UF`} />
      </div>
      <p className="text-xs text-gray-500">
        Conta na UF da sede do ASN; não é a população conectada nem o uso de Internet na UF (para isso, a página Uso da Internet, com a TIC Domicílios). Estimativa da APNIC por medição estatística, não contagem.
      </p>
    </div>
  )
}
