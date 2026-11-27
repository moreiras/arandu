// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { GrupoFontes, Kpi } from '../../components/ui'
import { ResumoEmTexto } from '../../components/ui/ResumoEmTexto'
import { fetchAcessosMovelStats, fetchAcessosStats, fetchMercadoGrupos, fetchMercadoMaiores } from '../../services/api'
import { useResumo } from '../panorama/useResumo'
import { cartoesMercado } from './faixaMercado'
import { REGRAS_SINTESE_MERCADO, sinteseMercado } from './sinteseMercado'

/**
 * Faixa de cartões e resumo em texto do Panorama de mercado (PT-22 / 5.3 e PT-30): cartões primeiro (fixo e móvel, cada serviço com o seu mês e nunca somados),
 * resumo em texto depois, fontes e datas recolhidas. Usa as mesmas consultas e chaves das abas (`/acessos/stats`, aberta, e `/mercado/grupos` e `/mercado/maiores`, medidas):
 * nada é buscado duas vezes, e cartão cujo dado não chegou (por exemplo, orçamento anônimo esgotado) simplesmente não aparece.
 */
export function SinteseMercado() {
  const { date } = useResumo()
  const d = date ?? undefined
  const fixo = useQuery({ queryKey: ['acessos-stats', d], queryFn: () => fetchAcessosStats(d, 15), retry: false, staleTime: 10 * 60 * 1000 })
  const movel = useQuery({ queryKey: ['acessos-movel-stats', d], queryFn: () => fetchAcessosMovelStats(d, 15), retry: false, staleTime: 10 * 60 * 1000 })
  const grupos = useQuery({ queryKey: ['mercado-grupos', date], queryFn: () => fetchMercadoGrupos(d), retry: false, staleTime: 10 * 60 * 1000 })
  const maiores = useQuery({ queryKey: ['mercado-maiores', date], queryFn: () => fetchMercadoMaiores({ date: d }), retry: false, staleTime: 10 * 60 * 1000 })
  const cartoes = cartoesMercado(fixo.data, movel.data, grupos.data, maiores.data)
  const ref = fixo.data?.snapshot_date ?? movel.data?.snapshot_date ?? d
  const servicos = [{ id: 'fixo' as const, titulo: 'Banda larga fixa' }, { id: 'movel' as const, titulo: 'Banda larga móvel' }]
  return (
    <GrupoFontes snapshot={ref}>
      {cartoes.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2" data-testid="faixa-mercado">
          {servicos.map((sv) => {
            const cs = cartoes.filter((c) => c.servico === sv.id)
            return cs.length === 0 ? null : (
              <section key={sv.id} aria-label={sv.titulo} className="space-y-2">
                <h2 className="text-titulo-3 text-gray-800">{sv.titulo}</h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {cs.map((c) => <Kpi key={c.id} rotulo={c.rotulo} valor={c.valor} referencia={c.referencia} variacao={c.variacao ? { texto: c.variacao } : undefined} selo={c.selo} fonte={c.fonte} dataRef={c.dataRef} />)}
                </div>
              </section>
            )
          })}
        </div>
      )}
      <ResumoEmTexto frases={sinteseMercado(fixo.data, movel.data)} snapshot={ref} regras={REGRAS_SINTESE_MERCADO}
        notaComoLer="Acessos declarados pelas empresas à Anatel: não medem receita, qualidade nem pessoas. Fixo e móvel têm meses de referência diferentes e nunca são somados." />
    </GrupoFontes>
  )
}
