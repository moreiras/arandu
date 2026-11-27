// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQueries } from '@tanstack/react-query'
import { GrupoFontes, Kpi } from '../../components/ui'
import { ResumoEmTexto } from '../../components/ui/ResumoEmTexto'
import { fetchCeticIndicadores } from '../../services/api'
import type { CeticIndicadores } from '../../types/api'
import { useActiveDate } from '../../hooks/useSnapshot'
import { cartoesCetic } from './cartoesCetic'
import { REGRAS_SINTESE_CETIC, TABELAS_SINTESE, sinteseCetic, type EntradaCetic, type Pesquisa } from './sinteseCetic'

/**
 * Resumo em texto de Uso da Internet (PT-30): busca as tabelas citadas (A4 e A5 da TIC Domicílios; E1A e C1 da TIC Provedores) com a MESMA consulta e chave da tabela da
 * página (`cetic-indicadores`), de modo que a tabela exibida e a frase compartilham a resposta em cache. Tabela que a edição não traz (erro) apenas não gera frase.
 */
export function SinteseCetic({ aoAbrirTabela }: { aoAbrirTabela?: (pesquisa: Pesquisa, tabela: string) => void } = {}) {
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
  const dom = por('domicilios'), prov = por('provedores')
  const cartoes = cartoesCetic(dom, prov)
  const ref = rs.find((r) => r.data)?.data?.snapshot_date ?? date
  return (
    <GrupoFontes snapshot={ref}>
      {cartoes.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="cartoes-cetic">
          {cartoes.map((c) => (
            <div key={c.id} className="min-w-0">
              <Kpi rotulo={c.rotulo} valor={c.valor} selo="estimado" fonte={`${c.fonte} (Cetic.br|NIC.br)`} dataRef={c.edicao}
                referencia={[c.margem, c.nota].filter(Boolean).join(' · ')} />
              {aoAbrirTabela && <button type="button" onClick={() => aoAbrirTabela(c.pesquisa, c.tabela)} className="mt-1 min-h-6 text-xs text-primario-700 hover:underline">Ver a tabela {c.tabela}</button>}
            </div>
          ))}
        </div>
      )}
      <ResumoEmTexto frases={sinteseCetic(dom, prov)} snapshot={ref}
        regras={REGRAS_SINTESE_CETIC} notaComoLer="Pesquisas por amostra: cada valor é uma estimativa com margem de erro de 95%, e duas estimativas só diferem de modo claro quando as faixas não se sobrepõem. Domicílios e Provedores têm edições de anos diferentes." />
    </GrupoFontes>
  )
}
