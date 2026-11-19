// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { BandaLargaFixaSection } from '../components/stats/BandaLargaFixaSection'
import { BandaLargaMovelSection } from '../components/stats/BandaLargaMovelSection'
import { EconomicGroupsTable } from '../components/stats/EconomicGroupsTable'
import { TelefoniaFixaSection } from '../components/stats/TelefoniaFixaSection'
import { TvPorAssinaturaSection } from '../components/stats/TvPorAssinaturaSection'
import { PaginaPanorama, type AbaPanorama } from '../features/panorama/PaginaPanorama'
import { MaioresMercado } from '../features/mercado/MaioresMercado'
import { ConcentracaoPanorama } from '../features/mercado/ConcentracaoPanorama'
import { useResumo } from '../features/panorama/useResumo'

/** Cada aba chama a seção antiga com a data ativa; só a aba aberta é montada (e só ela busca dado). */
const comData = (Secao: (p: { date?: string }) => JSX.Element | null) => function Aba() { const { date } = useResumo(); return <Secao date={date ?? undefined} /> }

export const ABAS_MERCADO: AbaPanorama[] = [
  { id: 'banda-larga-fixa', rotulo: 'Banda larga fixa', descricao: 'Acessos fixos declarados à Anatel (SICI): tecnologia, velocidade, maiores operadoras e evolução.', Conteudo: comData(BandaLargaFixaSection) },
  { id: 'banda-larga-movel', rotulo: 'Banda larga móvel', descricao: 'Acessos móveis (SMP) declarados à Anatel, por operadora e tecnologia.', Conteudo: comData(BandaLargaMovelSection) },
  { id: 'telefonia-fixa', rotulo: 'Telefonia fixa', descricao: 'Acessos de telefonia fixa (STFC) declarados à Anatel.', Conteudo: comData(TelefoniaFixaSection) },
  { id: 'tv-por-assinatura', rotulo: 'TV por assinatura', descricao: 'Assinantes de TV por assinatura (SeAC) declarados à Anatel.', Conteudo: comData(TvPorAssinaturaSection) },
  { id: 'maiores', rotulo: 'Maiores', descricao: 'Posição mês a mês das maiores operadoras de banda larga fixa e as maiores empresas ou grupos por acessos.', Conteudo: MaioresMercado },
  { id: 'concentracao', rotulo: 'Concentração', descricao: 'HHI do mercado fixo por CNPJ e por grupo econômico, por UF, e quantos municípios mudam de faixa.', Conteudo: ConcentracaoPanorama },
  { id: 'grupos', rotulo: 'Grupos econômicos', descricao: 'CNPJs com vários ASes: quem opera mais de uma rede sob a mesma empresa.', Conteudo: comData(EconomicGroupsTable) },
]

/** Panorama de mercado: as seções de mercado de Estatísticas, por serviço. Concentração e maiores (bump chart e treemap) usam análises novas do SICI. */
export function PanoramaMercado() {
  return <PaginaPanorama titulo="Panorama de mercado" descricao="Acessos e operadoras de banda larga, telefonia e TV por assinatura, a partir do que as empresas declaram à Anatel. Reúne as seções de mercado de Estatísticas." abas={ABAS_MERCADO} />
}
