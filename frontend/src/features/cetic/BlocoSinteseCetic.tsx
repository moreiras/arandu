// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQueries } from '@tanstack/react-query'
import { SinteseTopo } from '../../components/ui/SinteseTopo'
import { fetchCeticIndicadores } from '../../services/api'
import type { CeticIndicadores } from '../../types/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { REGRAS_SINTESE_CETIC, TABELAS_SINTESE, sinteseCetic, type EntradaCetic, type Pesquisa } from './sinteseCetic'

/**
 * Síntese no topo de Uso da Internet: busca as tabelas citadas (A4 e A5 da TIC Domicílios; E1A e C1 da TIC Provedores) com a MESMA consulta e chave da tabela da
 * página (`cetic-indicadores`), de modo que a tabela exibida e a frase compartilham a resposta em cache. Tabela que a edição não traz (erro) apenas não gera frase.
 */
export function SinteseCetic() {
  const date = useActiveDate() ?? undefined
  const pedidos = (Object.keys(TABELAS_SINTESE) as Pesquisa[]).flatMap((pesquisa) => TABELAS_SINTESE[pesquisa].map((tabela) => ({ pesquisa, tabela })))
  const rs = useQueries({
    queries: pedidos.map(({ pesquisa, tabela }) => ({
      queryKey: ['cetic-indicadores', date, pesquisa, tabela], queryFn: () => fetchCeticIndicadores({ date, pesquisa, tabela }), staleTime: 10 * 60 * 1000, retry: false,
    })),
  })
  const por = (p: Pesquisa): EntradaCetic | undefined => {
    const ok = pedidos.flatMap((x, i) => (x.pesquisa === p && rs[i].data ? [rs[i].data as CeticIndicadores] : []))
    return ok.length ? { edicao: ok[0].edicao, linhas: ok.flatMap((d) => d.items) } : undefined
  }
  return <SinteseTopo frases={sinteseCetic(por('domicilios'), por('provedores'))} snapshot={rs.find((r) => r.data)?.data?.snapshot_date ?? date}
    regras={REGRAS_SINTESE_CETIC} comoLer="Pesquisas por amostra: cada valor é uma estimativa com margem de erro de 95%, e duas estimativas só diferem de modo claro quando as faixas não se sobrepõem. Domicílios e Provedores têm edições de anos diferentes." />
}
