// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { BandaLargaFixaSection } from '../components/stats/BandaLargaFixaSection'
import { BandaLargaMovelSection } from '../components/stats/BandaLargaMovelSection'
import { TelefoniaFixaSection } from '../components/stats/TelefoniaFixaSection'
import { TvPorAssinaturaSection } from '../components/stats/TvPorAssinaturaSection'
import { PaginaPanorama, type AbaPanorama } from '../features/panorama/PaginaPanorama'
import { MaioresMercado } from '../features/mercado/MaioresMercado'
import { ConcentracaoPanorama } from '../features/mercado/ConcentracaoPanorama'
import { useResumo } from '../features/panorama/useResumo'
import { Navigate, useSearchParams } from 'react-router-dom'

/** Destino da antiga aba `?aba=grupos`. */
export const ABA_GRUPOS_MOVIDA = '/ases?secao=organizacoes'

/** Cada aba chama a seção antiga com a data ativa; só a aba aberta é montada (e só ela busca dado). */
const comData = (Secao: (p: { date?: string }) => JSX.Element | null) => function Aba() { const { date } = useResumo(); return <Secao date={date ?? undefined} /> }

export const ABAS_MERCADO: AbaPanorama[] = [
  { id: 'banda-larga-fixa', rotulo: 'Banda larga fixa', descricao: 'Acessos fixos declarados à Anatel (SICI): tecnologia, velocidade, maiores operadoras e evolução.', Conteudo: comData(BandaLargaFixaSection) },
  { id: 'banda-larga-movel', rotulo: 'Banda larga móvel', descricao: 'Acessos móveis (SMP) declarados à Anatel, por operadora e tecnologia.', Conteudo: comData(BandaLargaMovelSection) },
  { id: 'telefonia-fixa', rotulo: 'Telefonia fixa', descricao: 'Prestadoras com outorga de STFC no cadastro da Anatel. Esta página não traz acessos de STFC.', Conteudo: comData(TelefoniaFixaSection) },
  { id: 'tv-por-assinatura', rotulo: 'TV por assinatura', descricao: 'Prestadoras com outorga de SeAC no cadastro da Anatel. Esta página não traz assinantes de SeAC.', Conteudo: comData(TvPorAssinaturaSection) },
  { id: 'maiores', rotulo: 'Maiores', descricao: 'Posição mês a mês das maiores operadoras de banda larga fixa e as maiores empresas ou grupos por acessos.', Conteudo: MaioresMercado },
  { id: 'concentracao', rotulo: 'Concentração', descricao: 'HHI do mercado fixo por CNPJ e por grupo econômico, por UF, e quantos municípios mudam de faixa.', Conteudo: ConcentracaoPanorama },
]

/** Panorama de mercado: as seções de mercado de Estatísticas, por serviço. Concentração e maiores (bump chart e treemap) usam análises novas do SICI. */
export function PanoramaMercado() {
  const [params] = useSearchParams()
  // A antiga aba "Grupos econômicos" (CNPJs com vários ASNs) não era de mercado nem de grupo econômico: foi para /ases (regra 8: nada some sem alias).
  if (params.get('aba') === 'grupos') return <Navigate to={ABA_GRUPOS_MOVIDA} replace />
  return <PaginaPanorama titulo="Panorama de mercado" descricao="Acessos e operadoras de banda larga, telefonia e TV por assinatura, a partir do que as empresas declaram à Anatel. Reúne as seções de mercado de Estatísticas." abas={ABAS_MERCADO} />
}
