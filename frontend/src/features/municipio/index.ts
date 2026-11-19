// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { registrarAbas, registrarBloco, type BlocoDef } from '../entidade/registry'
import type { MunicipioCtx } from './contexto'
import { InfraBloco } from './blocks/InfraBloco'
import { MercadoFixoBloco } from './blocks/MercadoFixoBloco'
import { IndicadoresBloco } from './blocks/IndicadoresBloco'
import { PenetracaoMunicipio } from '../territorio/blocos'
import { MercadoMovelBloco } from './blocks/MercadoMovelBloco'
import { MercadoGruposMunicipioBloco } from '../mercado/blocos'
import { RedeTerritorioMunicipioBloco } from '../rede/blocos'
import { SerieMercadoBloco } from './blocks/SerieMercadoBloco'
import { SemelhantesBloco } from './blocks/SemelhantesBloco'
import { PainelBloco } from './blocks/PainelBloco'
import { RedeBloco } from './blocks/RedeBloco'
import { CarregadoresRegiaoBloco, ProntidaoRegiaoBloco, ProvedoresRegiaoBloco, PttsRegiaoBloco, TransitoRegiaoBloco } from './blocks/RegiaoBlocos'
import { ErbsMunicipioBloco } from '../erbs/blocos'
import { FustMunicipioBloco } from '../regulatorio/blocos'
import { QualidadeMunicipioBloco, ReclamacoesMunicipioBloco } from '../qualidade/blocos'
import { ConsumidorMunicipioBloco } from '../qualidade/consumidor'
import { ContratosMunicipioBloco } from '../contratos/blocos'

/** Blocos da página de município: painel de indicadores → Mercado → Rede → Infraestrutura. */
const base = { entidade: 'municipio' as const }

/** Lentes da página: cada bloco pertence a uma; a ordem dentro da aba segue `ordem`. A primeira é a padrão; aba sem bloco aplicável some. */
registrarAbas('municipio', [
  { id: 'resumo', rotulo: 'Resumo', descricao: 'Acessos, concentração do mercado e PTT mais próximo, em poucos números.' },
  { id: 'mercado', rotulo: 'Mercado', descricao: 'Banda larga fixa e telefonia móvel: operadoras, parcelas e variação.' },
  { id: 'infraestrutura', rotulo: 'Infraestrutura', descricao: 'Estações do SMP licenciadas e PTTs próximos.' },
  { id: 'rede', rotulo: 'Rede', descricao: 'ASNs das operadoras e dos provedores da região, PTTs, trânsito e segurança de roteamento.' },
  { id: 'qualidade', rotulo: 'Qualidade e regulação', descricao: 'RQUAL, reclamações, FUST e contratos públicos.' },
  { id: 'contexto', rotulo: 'Contexto', descricao: 'Domicílios, penetração e mercado não visto (estimativas).' },
])
const ABA: Record<string, string> = {
  painel: 'resumo',
  'mercado-fixo': 'mercado', 'serie-mercado': 'mercado', indicadores: 'mercado', 'mercado-movel': 'mercado',
  'estacoes-smp': 'infraestrutura', infraestrutura: 'infraestrutura',
  rede: 'rede', 'regiao-provedores': 'rede', 'regiao-ptts': 'rede', 'regiao-transito': 'rede', 'regiao-carregadores': 'rede', 'regiao-prontidao': 'rede',
  qualidade: 'qualidade', reclamacoes: 'qualidade', consumidor: 'qualidade', fust: 'qualidade', contratos: 'qualidade',
  penetracao: 'contexto', semelhantes: 'contexto', 'mercado-grupos': 'mercado', 'rede-territorio': 'rede',
}
const def = (b: Omit<BlocoDef<MunicipioCtx>, 'entidade'>) => registrarBloco<MunicipioCtx>({ ...base, aba: ABA[b.id], ...b })

def({ id: 'painel', titulo: 'Indicadores do município', ordem: 10, depende: ['useMunicipioPerfil'],
  fontes: ['anatel_sici', 'anatel_sici_movel', 'registro_br', 'curada_pix'], selo: 'fato',
  nota: 'acessos: declaração mensal ao SICI (duas datas: snapshot e mês de referência); distância ao PTT: linha reta até o centróide', Componente: PainelBloco })
def({ id: 'penetracao', titulo: 'Penetração e mercado não visto', ordem: 15, depende: ['useMunicipioPerfil'], fontes: ['ibge_censo_pnad', 'anatel_sici'], selo: 'estimado',
  nota: 'domicílios do Censo 2022; o não visto é estimativa (a taxa da PNAD inclui quem usa só o celular)', aplicavel: (c) => !!c.territorio,
  Componente: PenetracaoMunicipio })
def({ id: 'mercado-fixo', titulo: 'Mercado — banda larga fixa', ordem: 20, depende: ['useMunicipioPerfil'], fontes: ['anatel_sici', 'registro_br'], selo: 'fato',
  nota: 'duas datas: o snapshot e o mês de referência da declaração ao SICI', aplicavel: (c) => !!c.fixo, Componente: MercadoFixoBloco })
def({ id: 'indicadores', titulo: 'Variação do mercado fixo', ordem: 25, depende: ['useMunicipioPerfil'], fontes: ['anatel_sici'], selo: 'fato',
  nota: 'dado declarado; a variação compara o mês de referência com o mês anterior e com o de 12 meses antes', aplicavel: (c) => !!c.indicadores, Componente: IndicadoresBloco })
def({ id: 'mercado-movel', titulo: 'Mercado — telefonia móvel', ordem: 30, depende: ['useMunicipioPerfil'], fontes: ['anatel_sici_movel', 'registro_br'], selo: 'fato',
  nota: 'duas datas: o snapshot e o mês de referência da declaração ao SICI móvel', aplicavel: (c) => !!c.movel, Componente: MercadoMovelBloco })
def({ id: 'estacoes-smp', titulo: 'Estações do SMP licenciadas', ordem: 35, depende: ['useMunicipioPerfil'], fontes: ['anatel_erbs'], selo: 'fato',
  nota: 'cadastro de licenciamento da Anatel: não é cobertura nem estação em operação', aplicavel: (c) => !!c.erbs, Componente: ErbsMunicipioBloco })
def({ id: 'qualidade', titulo: 'Qualidade (RQUAL da Anatel)', ordem: 37.5, depende: ['useMunicipioPerfil'], fontes: ['anatel_rqual'], selo: 'fato',
  nota: 'último resultado apurado pela Anatel por prestadora; poucas medidas = resultado incerto; só as grandes prestadoras; sem ranking', aplicavel: (c) => !!c.qualidade, Componente: QualidadeMunicipioBloco })
def({ id: 'reclamacoes', titulo: 'Reclamações na Anatel', ordem: 37.7, depende: ['useMunicipioPerfil'], fontes: ['anatel_reclamacoes'], selo: 'fato',
  nota: 'declarado por consumidores, últimos 3 anos da fonte; depende do tamanho da base de clientes; reclamação não é prova de falha', aplicavel: (c) => !!c.reclamacoes, Componente: ReclamacoesMunicipioBloco })
def({ id: 'consumidor', titulo: 'Reclamações no Consumidor.gov.br', ordem: 37.8, depende: ['useMunicipioPerfil'], fontes: ['consumidor_gov'], selo: 'fato',
  nota: 'reclamações finalizadas, declaradas por consumidores; a cidade é casada ao IBGE pelo nome; só empresas com 5 ou mais reclamações; depende do tamanho da base de clientes', aplicavel: (c) => !!c.consumidor, Componente: ConsumidorMunicipioBloco })
def({ id: 'contratos', titulo: 'Contratos públicos de operadoras (PNCP)', ordem: 37.9, depende: ['useContratosMunicipio'], fontes: ['siasg_contratos'], selo: 'fato',
  nota: 'o município é o do órgão comprador, não o local de entrega; resultados de itens publicados no PNCP em rodízio de coleta; não é ranking nem prova de atendimento; licença do portal não verificada', aplicavel: (c) => !!c.contratos, Componente: ContratosMunicipioBloco })
def({ id: 'fust', titulo: 'FUST — compromissos no município', ordem: 37, depende: ['useMunicipioPerfil'], fontes: ['anatel_fust'], selo: 'fato',
  nota: 'cadastro da Anatel: não identifica a empresa executora; o valor é o previsto, não o desembolsado', aplicavel: (c) => !!c.fust, Componente: FustMunicipioBloco })
def({ id: 'rede', titulo: 'Rede — ASNs das operadoras', ordem: 40, depende: ['useMunicipioPerfil'], fontes: ['registro_br'], selo: 'inferido',
  nota: 'ASNs ligados à operadora pelo CNPJ (Registro.br)', aplicavel: (c) => [...(c.fixo?.operadores ?? []), ...(c.movel?.operadores ?? [])].some((o) => o.asns.length > 0), Componente: RedeBloco })
def({ id: 'infraestrutura', titulo: 'Infraestrutura — PTTs próximos', ordem: 50, depende: ['map-pix', 'municipios-centroides'], fontes: ['curada_pix'], selo: 'estimado',
  nota: 'distância em linha reta até o centróide do município', aplicavel: (c) => c.proximos.length > 0, Componente: InfraBloco })
def({ id: 'regiao-provedores', titulo: 'Provedores da região (ASNs)', ordem: 41, depende: ['useRegiao'], fontes: ['anatel_sici', 'registro_br', 'cnpj_geo', 'prefix_geo'], selo: 'inferido',
  nota: 'o ASN entra pelo SICI, pela sede do CNPJ ou por prefixos geolocalizados no município (DB-IP, precisão de cidade)', aplicavel: (c) => !!c.regiao && c.regiao.asns.total > 0, Componente: ProvedoresRegiaoBloco })
def({ id: 'regiao-ptts', titulo: 'Participação nos PTTs', ordem: 42, depende: ['useRegiao'], fontes: ['lg_ixbr', 'peeringdb_ixps'], selo: 'fato',
  nota: 'direto = sessão no PTT; indireto = rotas do ASN vistas no PTT por meio de outro ASN', aplicavel: (c) => !!c.regiao && c.regiao.asns.total > 0, Componente: PttsRegiaoBloco })
def({ id: 'regiao-transito', titulo: 'Provedores de trânsito da região', ordem: 43, depende: ['useRegiao'], fontes: ['caida_asrel', 'fulltable_routeviews', 'lg_ixbr'], selo: 'inferido',
  nota: 'relações provedor–cliente inferidas (ARC v1) com a probabilidade; não é contrato', aplicavel: (c) => !!c.regiao && c.regiao.transito.length > 0, Componente: TransitoRegiaoBloco })
def({ id: 'regiao-carregadores', titulo: 'Quem leva a região até os PTTs', ordem: 44, depende: ['useRegiao'], fontes: ['lg_ixbr'], selo: 'inferido',
  nota: 'vizinho observado nos caminhos dos looking glasses que tem sessão num PTT', aplicavel: (c) => !!c.regiao && c.regiao.carregadores.length > 0, Componente: CarregadoresRegiaoBloco })
def({ id: 'regiao-prontidao', titulo: 'Segurança de roteamento da região', ordem: 45, depende: ['useRegiao'], fontes: ['apnic_irov', 'bogons', 'caida_spoofer', 'irr_route_objects', 'peeringdb_networks', 'rpki_collector'], selo: 'inferido',
  nota: 'índice de prontidão dos ASNs ligados à região; vale com qualquer número de ASNs e diz quantos sustentam o número', aplicavel: (c) => !!c.regiao?.prontidao, Componente: ProntidaoRegiaoBloco })

def({ id: 'semelhantes', titulo: 'Comparação com municípios do mesmo porte', ordem: 16, depende: ['useMunicipioSemelhantes'], fontes: ['ibge_censo_pnad', 'anatel_sici'], selo: 'estimado',
  nota: 'porte = domicílios projetados entre metade e o dobro; posição 1 = maior valor, sem juízo de bom ou ruim', aplicavel: (c) => !!c.territorio, Componente: SemelhantesBloco })

def({ id: 'serie-mercado', titulo: 'Participação de mercado ao longo do tempo', ordem: 22, depende: ['useMunicipioPerfil'], fontes: ['anatel_sici'], selo: 'fato',
  nota: 'participação sobre acessos declarados (não receita), 13 meses; mês sem declaração fica sem ponto', aplicavel: (c) => !!c.serieMercado, Componente: SerieMercadoBloco })

def({ id: 'mercado-grupos', titulo: 'Concentração por CNPJ e por grupo', ordem: 21, depende: ['useMunicipioPerfil'], fontes: ['anatel_sici', 'socios_grupos'], selo: 'inferido',
  nota: 'O HHI por grupo é inferido do quadro societário em comum e pode juntar empresas independentes; ambos sobre acessos declarados, não receita', aplicavel: (c) => !!c.mercadoGrupos, Componente: MercadoGruposMunicipioBloco })

def({ id: 'rede-territorio', titulo: 'IPv6 e dependência de trânsito (estimativas)', ordem: 39, depende: ['useMunicipioPerfil'], fontes: ['anatel_sici', 'apnic_pop', 'caida_asrel'], selo: 'estimado',
  nota: 'estimativa e inferência: a adoção de IPv6 do AS vale igual em todos os municípios da operadora; um provedor de trânsito só pode ser falta de observação; a cobertura diz que parcela entrou', aplicavel: (c) => !!c.redeTerritorio, Componente: RedeTerritorioMunicipioBloco })
