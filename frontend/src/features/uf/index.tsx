// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { registrarAbas, registrarBloco, type BlocoDef } from '../entidade/registry'
import { MapaUf } from './MapaUf'
import type { UfCtx } from './contexto'
import { MercadoGruposUfBloco } from '../mercado/blocos'
import { RedeTerritorioUfBloco } from '../rede/blocos'
import { PosicaoBloco } from './blocks/PosicaoBloco'
import { LinhaDoTempoUf } from '../historico/blocos'
import { MunicipiosBloco } from './blocks/MunicipiosBloco'
import { OperadorasBloco } from './blocks/OperadorasBloco'
import { PenetracaoUf } from '../territorio/blocos'
import { CeticUfBloco } from './blocks/CeticUfBloco'
import { DemandaOfertaUfBloco } from './blocks/DemandaOfertaUfBloco'
import { ErbsUfBloco } from '../erbs/blocos'
import { FustUfBloco } from '../regulatorio/blocos'
import { QualidadeUfBloco, ReclamacoesUfBloco } from '../qualidade/blocos'
import { ConsumidorUfBloco } from '../qualidade/consumidor'
import { EmpresasTelecomUfBloco } from '../empresas/blocos'
import { ProntidaoUfBloco } from '../prontidao/blocos'
import { RadarUfBloco } from '../radar/blocos'
import { ExposicaoUfBloco } from '../exposicao/blocos'
import { PainelBloco } from './blocks/PainelBloco'
import { UsuariosSedeUfBloco } from './blocks/UsuariosSedeUfBloco'
import { TransitoUfBloco } from './blocks/TransitoUfBloco'
import { PttsBloco } from './blocks/PttsBloco'
import { DeclaracaoSiciUfBloco } from './blocks/DeclaracaoSiciUfBloco'
import { SemPttBloco } from './blocks/SemPttBloco'
import { SITE } from '../../lib/site'
import { ResumoEmTexto } from '../../components/ui/ResumoEmTexto'
import { REGRAS_SINTESE_UF, sinteseUf } from './sinteseUf'

/** Blocos da página de UF: painel → PTTs → municípios → municípios sem PTT próximo → operadoras. */
const base = { entidade: 'uf' as const }

/** Lentes da página: cada bloco pertence a uma; aba sem bloco aplicável some. */
registrarAbas('uf', [
  { id: 'resumo', rotulo: 'Resumo', descricao: 'Indicadores da UF e o mapa dos municípios.' },
  { id: 'mercado', rotulo: 'Mercado', descricao: 'Municípios, operadoras e as estimativas de penetração e de demanda × oferta.' },
  { id: 'infraestrutura', rotulo: 'Infraestrutura', descricao: 'PTTs, municípios sem PTT próximo e estações do SMP licenciadas.' },
  { id: 'rede', rotulo: 'Rede', descricao: 'Segurança de roteamento, trânsito, radar e exposição dos ASNs da UF.' },
  { id: 'qualidade', rotulo: 'Qualidade e regulação', descricao: 'RQUAL, reclamações, FUST e empresas de telecom.' },
  { id: 'contexto', rotulo: 'Contexto', descricao: 'Acesso à Internet nos domicílios (TIC Domicílios).' },
  { id: 'historico', rotulo: 'Histórico', descricao: 'O que mudou na UF entre os snapshots.' },
])
const ABA: Record<string, string> = {
  sintese: 'resumo', painel: 'resumo', 'mapa-municipios': 'resumo', posicao: 'resumo',
  municipios: 'mercado', operadoras: 'mercado', 'mercado-grupos': 'mercado', penetracao: 'mercado', 'demanda-oferta': 'mercado',
  ptts: 'infraestrutura', 'sem-ptt': 'infraestrutura', 'estacoes-smp': 'infraestrutura',
  'usuarios-sede': 'rede', prontidao: 'rede', 'rede-territorio': 'rede', transito: 'rede', radar: 'rede', exposicao: 'rede',
  'declaracao-sici': 'qualidade', qualidade: 'qualidade', reclamacoes: 'qualidade', consumidor: 'qualidade', fust: 'qualidade', 'empresas-telecom': 'qualidade',
  'tic-domicilios': 'contexto',
  'linha-do-tempo': 'historico',
}
const def = (b: Omit<BlocoDef<UfCtx>, 'entidade'>) => registrarBloco<UfCtx>({ ...base, aba: ABA[b.id], ...b })

def({ id: 'sintese', titulo: 'Em resumo', ordem: 11, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'ibge_censo_pnad', 'curada_pix', 'lg_ixbr', 'registro_br'], selo: 'fato',
  nota: 'frases geradas por regra a partir dos números do painel; estimativas e inferências levam o selo próprio', semTitulo: true, plana: true,
  Componente: ({ dados, snapshot }) => <ResumoEmTexto frases={sinteseUf(dados, snapshot)} snapshot={snapshot} regras={REGRAS_SINTESE_UF} notaComoLer="A UF de um AS é a da sede da organização, não a da operação, e a distância até o PTT é em linha reta, não o trajeto de fibra." /> })

def({ id: 'mapa-municipios', titulo: 'Mapa dos municípios', ordem: 12, depende: ['useUfPerfil', 'municipios-centroides', 'malha-municipal'], fontes: ['ibge_malha_municipal', 'anatel_sici', 'curada_pix'], selo: 'fato',
  nota: 'indicadores normalizados por município; município sem dado fica cinza; malha: Fonte: IBGE', aplicavel: (c) => c.municipios.length > 0, Componente: ({ dados }) => <MapaUf dados={dados} /> })

def({ id: 'posicao', titulo: 'A UF entre as 27', ordem: 13, depende: ['ufs'], fontes: ['anatel_sici', 'ibge_censo_pnad', 'curada_pix'], selo: 'estimado',
  nota: 'indicadores normalizados (penetração por domicílio, fibra, isolamento de PTT); posição 1 = maior valor, sem juízo de bom ou ruim', Componente: PosicaoBloco })

def({ id: 'painel', titulo: 'Indicadores da UF', ordem: 10, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'registro_br', 'apnic_pop', 'lg_ixbr'], selo: 'fato',
  nota: 'usuários: estimativa APNIC; distância ao PTT: linha reta até o centróide', semTitulo: true, plana: true, Componente: PainelBloco })
def({ id: 'penetracao', titulo: 'Penetração e mercado não visto', ordem: 15, depende: ['useUfPerfil'], fontes: ['ibge_censo_pnad', 'anatel_sici'], selo: 'estimado',
  nota: 'domicílios do Censo 2022; o não visto é estimativa (a taxa da PNAD inclui quem usa só o celular)', aplicavel: (c) => !!c.territorio,
  Componente: PenetracaoUf })
def({ id: 'tic-domicilios', titulo: 'Acesso à Internet nos domicílios (TIC Domicílios)', ordem: 17, depende: ['useUfPerfil'], fontes: ['cetic_tic_domicilios_microdados'], selo: 'estimado',
  nota: `estimativa do ${SITE.nome} sobre os microdados do Cetic.br|NIC.br, com erro-padrão`, aplicavel: (c) => !!c.cetic, Componente: CeticUfBloco })
def({ id: 'demanda-oferta', titulo: 'Demanda × oferta de banda larga fixa', ordem: 18, depende: ['useUfPerfil'], fontes: ['cetic_tic_domicilios_microdados', 'ibge_censo_pnad', 'anatel_sici'], selo: 'estimado',
  nota: `estimativa do ${SITE.nome}: domicílios com banda larga fixa (TIC) × acessos de pessoa física declarados ao SICI, com intervalo de 95%`, aplicavel: (c) => !!c.demandaOferta, Componente: DemandaOfertaUfBloco })
def({ id: 'estacoes-smp', titulo: 'Estações do SMP licenciadas', ordem: 19, depende: ['useUfPerfil'], fontes: ['anatel_erbs'], selo: 'fato',
  nota: 'cadastro de licenciamento da Anatel: não é cobertura nem estação em operação', aplicavel: (c) => !!c.erbs, Componente: ErbsUfBloco })
def({ id: 'empresas-telecom', titulo: 'Empresas de telecom da UF (CNPJ)', ordem: 19.55, depende: ['useCadastroMercadoUf'], fontes: ['receita_cnpj'], selo: 'fato',
  nota: 'cadastro da Receita na data do dump mensal; uma contagem por empresa (a matriz com CNAE 61 principal), sem separar operadora de revenda ou de MEI', aplicavel: (c) => !!c.cadastro, Componente: EmpresasTelecomUfBloco })
def({ id: 'declaracao-sici', titulo: 'Declaração de acessos à Anatel (SICI)', ordem: 19.58, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'anatel_scm', 'apnic_pop'], selo: 'fato',
  nota: 'contagens de CNPJs, sem nomes; usuários estimados (APNIC) são estimativa; sem declaração não indica causa nem intenção', aplicavel: (c) => !!c.indicadores, Componente: DeclaracaoSiciUfBloco })
def({ id: 'qualidade', titulo: 'Qualidade (RQUAL da Anatel)', ordem: 19.6, depende: ['useUfPerfil'], fontes: ['anatel_rqual'], selo: 'fato',
  nota: 'média dos municípios medidos no último ano, por prestadora; só as grandes prestadoras; sem ranking', aplicavel: (c) => !!c.qualidade, Componente: QualidadeUfBloco })
def({ id: 'reclamacoes', titulo: 'Reclamações na Anatel', ordem: 19.7, depende: ['useUfPerfil'], fontes: ['anatel_reclamacoes'], selo: 'fato',
  nota: 'declarado por consumidores; depende do tamanho da base de clientes; sem ranking', aplicavel: (c) => !!c.reclamacoes, Componente: ReclamacoesUfBloco })
def({ id: 'consumidor', titulo: 'Reclamações no Consumidor.gov.br', ordem: 19.8, depende: ['useUfPerfil'], fontes: ['consumidor_gov'], selo: 'fato',
  nota: 'reclamações finalizadas, declaradas por consumidores; só empresas com 5 ou mais reclamações na UF; depende do tamanho da base de clientes; sem ranking', aplicavel: (c) => !!c.consumidor, Componente: ConsumidorUfBloco })
def({ id: 'fust', titulo: 'FUST: compromissos na UF', ordem: 19.5, depende: ['useUfPerfil'], fontes: ['anatel_fust'], selo: 'fato',
  nota: 'cadastro da Anatel: não identifica a empresa executora; o valor é o previsto, não o desembolsado', aplicavel: (c) => !!c.fust, Componente: FustUfBloco })
def({ id: 'usuarios-sede', titulo: 'Usuários estimados (APNIC) por sede do ASN', ordem: 19.75, depende: ['useUfPerfil', 'ufs'], fontes: ['apnic_pop', 'registro_br'], selo: 'estimado',
  nota: 'estimativa APNIC; conta na UF da sede do ASN, não é a população conectada', Componente: UsuariosSedeUfBloco })
def({ id: 'prontidao', titulo: 'Prontidão em segurança de roteamento', ordem: 19.8, depende: ['useUfPerfil'], fontes: ['apnic_irov', 'bogons', 'caida_spoofer', 'irr_route_objects', 'peeringdb_networks', 'rpki_collector'], selo: 'estimado',
  nota: 'agregado dos ASNs da UF; soma ponderada de medições de terceiros, não veredito sobre empresas', aplicavel: (c) => !!c.prontidao, Componente: ProntidaoUfBloco })
def({ id: 'transito', titulo: 'Provedores de trânsito (inferido)', ordem: 19.9, depende: ['useUfPerfil'], fontes: ['fulltable_routeviews', 'lg_ixbr', 'rpki_collector', 'caida_as2org'], selo: 'inferido',
  nota: 'relações inferidas pelo ARC v2 sobre rotas observadas; a UF é a da sede da organização; não é contrato nem tráfego', aplicavel: (c) => !!c.transito, Componente: TransitoUfBloco })
def({ id: 'radar', titulo: 'IPv6, tráfego e BGP (Cloudflare Radar, derivado)', ordem: 19.95, depende: ['useUfPerfil'], fontes: ['cloudflare_radar'], selo: 'estimado',
  nota: 'agregado derivado dos ASNs da UF (o Radar não tem recorte por UF); mede quem usa a Cloudflare; dados CC BY-NC 4.0', aplicavel: (c) => !!c.radar, Componente: RadarUfBloco })
def({ id: 'exposicao', titulo: 'Exposição de serviços (Shodan, derivado)', ordem: 19.97, depende: ['useUfPerfil'], fontes: ['shodan_exposicao'], selo: 'estimado',
  nota: 'agregado derivado dos ASNs da UF já lidos; contagem observada pelo Shodan, não prova de vulnerabilidade; só contagens, nunca lista de IPs; dados do Shodan', aplicavel: (c) => !!c.exposicao, Componente: ExposicaoUfBloco })
def({ id: 'ptts', titulo: 'PTTs na UF', ordem: 20, depende: ['ixps'], fontes: ['lg_ixbr', 'ixbr_api'], selo: 'fato', aplicavel: (c) => c.ixps.length > 0, Componente: PttsBloco })
def({ id: 'municipios', titulo: 'Maiores municípios em banda larga fixa', ordem: 30, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'curada_pix'], selo: 'fato',
  nota: 'duas datas: o snapshot e o mês de referência da declaração ao SICI', aplicavel: (c) => c.municipios.length > 0, Componente: MunicipiosBloco })
def({ id: 'sem-ptt', titulo: 'Municípios a mais de 100 km de um PTT', ordem: 40, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'curada_pix'], selo: 'estimado',
  nota: 'distância em linha reta até o centróide; não é o trajeto de fibra', aplicavel: (c) => !c.semCentroides && c.municipios.some((m) => m.kmPtt != null && m.kmPtt > 100), Componente: SemPttBloco })
def({ id: 'operadoras', titulo: 'Operadoras na UF', ordem: 50, depende: ['acessos-operadoras'], fontes: ['anatel_sici', 'anatel_outorgas', 'registro_br'], selo: 'fato',
  nota: 'duas datas: o snapshot e o mês de referência da declaração ao SICI; parcela sobre acessos declarados na UF, não sobre receita', aplicavel: (c) => c.operadorasPresentes.length > 0 || c.operadoras.length > 0, Componente: OperadorasBloco })
def({ id: 'linha-do-tempo', titulo: 'Linha do tempo', ordem: 60, depende: ['useUfPerfil'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr', 'rpki_collector', 'apnic_pop'], selo: 'fato', nota: 'diferenças observadas entre snapshots',
  aplicavel: (c) => !!c.historico, Componente: LinhaDoTempoUf })

def({ id: 'mercado-grupos', titulo: 'Concentração por CNPJ e por grupo', ordem: 29, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'socios_grupos'], selo: 'inferido',
  nota: 'O HHI por grupo é inferido do quadro societário em comum e pode juntar empresas independentes; ambos sobre acessos declarados, não receita', aplicavel: (c) => !!c.mercadoGrupos, Componente: MercadoGruposUfBloco })

def({ id: 'rede-territorio', titulo: 'IPv6, ROV e dependência de trânsito (estimativas)', ordem: 19.85, depende: ['useUfPerfil'], fontes: ['anatel_sici', 'apnic_pop', 'apnic_irov', 'caida_asrel'], selo: 'estimado',
  nota: 'estimativa e inferência: a adoção de IPv6 do AS vale igual em todos os municípios da operadora; um provedor de trânsito só pode ser falta de observação; a cobertura diz que parcela entrou; no ROV a UF é a da sede do ASN', aplicavel: (c) => !!c.redeTerritorio, Componente: RedeTerritorioUfBloco })
