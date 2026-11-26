// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SobreposicaoBloco } from '../mercado/blocos'
import { registrarAbas, registrarBloco, type BlocoDef } from '../entidade/registry'
import type { OperadoraCtx } from './contexto'
import { LinhaDoTempoOperadora } from '../historico/blocos'
import { EmpresasRelacionadasBloco } from './blocks/EmpresasRelacionadasBloco'
import { IndicadoresBloco } from './blocks/IndicadoresBloco'
import { RedeBloco } from './blocks/RedeBloco'
import { ScmBloco } from './blocks/ScmBloco'
import { SeacBloco } from './blocks/SeacBloco'
import { SmpBloco } from './blocks/SmpBloco'
import { StfcBloco } from './blocks/StfcBloco'
import { ErbsOperadoraBloco } from '../erbs/blocos'
import { MultasOperadoraBloco } from '../regulatorio/blocos'
import { ProntidaoOperadoraBloco } from '../prontidao/blocos'
import { RecursosIpv4OperadoraBloco } from '../ipv4/blocos'
import { QualidadeOperadoraBloco, ReclamacoesOperadoraBloco } from '../qualidade/blocos'
import { ConsumidorOperadoraBloco } from '../qualidade/consumidor'
import { PresencaFisicaOperadoraBloco } from '../empresas/blocos'
import { CreditoPublicoBloco, SancoesBloco } from '../financiamento/blocos'
import { ContratosOperadoraBloco } from '../contratos/blocos'

/** Blocos da página de operadora (por CNPJ), na ordem em que aparecem. Corpos idênticos aos da página de antes; ver `features/asn/index.ts`. */
const base = { entidade: 'operadora' as const }

/** Lentes da página: cada bloco pertence a uma; a ordem dentro da aba segue `ordem`. A primeira é a padrão. */
registrarAbas('operadora', [
  { id: 'resumo', rotulo: 'Resumo', descricao: 'Quanto a empresa declara à Anatel e como está posicionada.' },
  { id: 'mercado', rotulo: 'Mercado', descricao: 'Serviços outorgados, assinantes por município e evolução.' },
  { id: 'presenca', rotulo: 'Presença', descricao: 'Onde a empresa tem estabelecimentos e estações licenciadas.' },
  { id: 'rede', rotulo: 'Rede', descricao: 'ASNs, rotas, PTTs, RPKI e recursos IPv4 da empresa.' },
  { id: 'qualidade', rotulo: 'Qualidade e regulação', descricao: 'Medições da Anatel, reclamações, multas, sanções e contratos públicos.' },
  { id: 'empresa', rotulo: 'Empresa', descricao: 'Empresas relacionadas por sócios em comum (só estrutura entre empresas).' },
  { id: 'historico', rotulo: 'Histórico', descricao: 'O que mudou nesta operadora entre os snapshots.' },
])
const ABA: Record<string, string> = {
  indicadores: 'resumo',
  scm: 'mercado', sobreposicao: 'mercado', smp: 'mercado', stfc: 'mercado', seac: 'mercado',
  'presenca-fisica': 'presenca', 'estacoes-smp': 'presenca',
  rede: 'rede', 'recursos-ipv4': 'rede', prontidao: 'rede',
  qualidade: 'qualidade', reclamacoes: 'qualidade', consumidor: 'qualidade', multas: 'qualidade', 'credito-publico': 'qualidade', sancoes: 'qualidade', contratos: 'qualidade',
  'empresas-relacionadas': 'empresa',
  'linha-do-tempo': 'historico',
}
const def = (b: Omit<BlocoDef<OperadoraCtx>, 'entidade'>) => registrarBloco<OperadoraCtx>({ ...base, aba: ABA[b.id], ...b })

def({ id: 'rede', semTitulo: true, titulo: 'Rede (BGP · RPKI · IX.br)', ordem: 10, depende: ['useOperadoraPerfil'], fontes: ['registro_br', 'apnic_pop', 'lg_ixbr', 'rpki_collector', 'fulltable_routeviews'], selo: 'fato',
  nota: 'agregado dos ASNs do Registro.br com este CNPJ; os usuários são uma estimativa do APNIC', aplicavel: (c) => !!c.rede, Componente: RedeBloco })
def({ id: 'empresas-relacionadas', titulo: 'Empresas relacionadas', ordem: 20, depende: ['empresas-relacionadas'], fontes: ['receita_socios', 'socios_grupos'], selo: 'inferido',
  nota: 'cruzamento dos sócios do QSA, só com evidência direta', Componente: EmpresasRelacionadasBloco })
def({ id: 'scm', semTitulo: true, titulo: 'SCM (banda larga fixa)', ordem: 30, depende: ['useOperadoraPerfil'], fontes: ['anatel_outorgas', 'anatel_sici', 'registro_br'], selo: 'fato',
  nota: 'duas datas: a do snapshot e o mês de referência da declaração ao SICI', aplicavel: (c) => !!c.data, Componente: ScmBloco })
def({ id: 'indicadores', titulo: 'Indicadores do SICI', ordem: 35, depende: ['useOperadoraPerfil'], fontes: ['anatel_sici', 'anatel_outorgas', 'apnic_pop'], selo: 'fato',
  nota: 'dado declarado à Anatel; a parcela é calculada sobre os acessos declarados, não sobre a receita; os usuários do APNIC são uma estimativa', aplicavel: (c) => !!c.indicadores, Componente: IndicadoresBloco })
def({ id: 'recursos-ipv4', titulo: 'Recursos IPv4', ordem: 38, depende: ['useOperadoraPerfil'], fontes: ['ipv4_delegated', 'fulltable_routeviews', 'rpki_collector'], selo: 'inferido',
  nota: 'blocos dos ASNs da operadora; um bloco não anunciado pode estar em uso, e o sinal de terceiros é uma hipótese', aplicavel: (c) => c.hasScm || c.hasSici, Componente: RecursosIpv4OperadoraBloco })
def({ id: 'estacoes-smp', titulo: 'Estações do SMP licenciadas', ordem: 45, depende: ['useOperadoraPerfil'], fontes: ['anatel_erbs'], selo: 'fato',
  nota: 'cadastro de licenciamento da Anatel, que não indica cobertura nem estação em operação', aplicavel: (c) => !!c.erbs, Componente: ErbsOperadoraBloco })
def({ id: 'multas', titulo: 'Multas constituídas pela Anatel', ordem: 46, depende: ['useOperadoraPerfil'], fontes: ['anatel_multas'], selo: 'fato',
  nota: 'a multa constituída pode estar em recurso, parcelada ou suspensa, então ainda não é condenação definitiva', aplicavel: (c) => !!c.multas, Componente: MultasOperadoraBloco })
// Os dois blocos abaixo ficam com título e cartão (sem `semTitulo` e `plana`): não trazem cabeçalho próprio como os de antes.
def({ id: 'presenca-fisica', titulo: 'Presença física (CNPJ da Receita × SICI)', ordem: 12.5, depende: ['useCadastroOperadora'], fontes: ['receita_cnpj', 'anatel_sici', 'anatel_sici_movel'], selo: 'fato',
  nota: 'estabelecimentos do cadastro da Receita e municípios com acessos declarados ao SICI são fontes que medem coisas diferentes; a diferença entre elas não prova atendimento', aplicavel: (c) => !!c.cadastro, Componente: PresencaFisicaOperadoraBloco })
def({ id: 'credito-publico', titulo: 'Crédito público (BNDES)', ordem: 12.6, depende: ['useFinanciamentoOperadora'], fontes: ['bndes_operacoes'], selo: 'fato',
  nota: 'operações diretas e não automáticas do BNDES, em valores nominais da data da contratação; a ausência de registro não prova que nunca houve crédito', aplicavel: (c) => !!c.financiamento?.financiamento, Componente: CreditoPublicoBloco })
def({ id: 'sancoes', titulo: 'Sanções (CEIS e CNEP)', ordem: 12.7, depende: ['useFinanciamentoOperadora'], fontes: ['cgu_ceis_cnep'], selo: 'fato',
  nota: 'registro do órgão sancionador na data do arquivo da CGU; a sanção pode já ter sido suspensa ou anulada, e o registro não é um julgamento', aplicavel: (c) => !!c.financiamento?.sancoes, Componente: SancoesBloco })
def({ id: 'contratos', titulo: 'Contratos públicos (PNCP)', ordem: 12.8, depende: ['useContratosOperadora'], fontes: ['siasg_contratos'], selo: 'fato',
  nota: 'resultados de itens publicados no PNCP, que não são contratos assinados nem pagamentos; a coleta é em rodízio, só do CNPJ de matriz e só da Lei 14.133; a data da leitura vem no bloco, e a licença do portal não foi verificada', aplicavel: (c) => !!c.contratos, Componente: ContratosOperadoraBloco })
def({ id: 'qualidade', titulo: 'Qualidade (RQUAL da Anatel)', ordem: 46.5, depende: ['useOperadoraPerfil'], fontes: ['anatel_rqual', 'curada_marcas_operadoras'], selo: 'fato',
  nota: 'indicadores apurados pela Anatel, nacionais por prestadora; a ligação entre prestadora e CNPJ é curada; sem ranking nem veredito', aplicavel: (c) => !!c.qualidade, Componente: QualidadeOperadoraBloco })
def({ id: 'reclamacoes', titulo: 'Reclamações na Anatel', ordem: 46.7, depende: ['useOperadoraPerfil'], fontes: ['anatel_reclamacoes', 'curada_marcas_operadoras', 'anatel_sici'], selo: 'fato',
  nota: 'declaradas por consumidores; a ligação entre marca e CNPJ é curada ou feita por nome fantasia único; uma reclamação não prova falha', aplicavel: (c) => !!c.reclamacoes, Componente: ReclamacoesOperadoraBloco })
def({ id: 'consumidor', titulo: 'Reclamações no Consumidor.gov.br', ordem: 46.8, depende: ['useOperadoraPerfil'], fontes: ['consumidor_gov', 'curada_marcas_operadoras'], selo: 'fato',
  nota: 'reclamações finalizadas, declaradas por consumidores; índice, tempo e nota só com 30 ou mais casos; a ligação entre empresa e CNPJ é curada; uma reclamação não prova falha', aplicavel: (c) => !!c.consumidor, Componente: ConsumidorOperadoraBloco })
def({ id: 'prontidao', titulo: 'Prontidão em segurança de roteamento', ordem: 47, depende: ['useOperadoraPerfil'], fontes: ['apnic_irov', 'bogons', 'caida_spoofer', 'irr_route_objects', 'peeringdb_networks', 'rpki_collector'], selo: 'estimado',
  nota: 'agregado dos ASNs do CNPJ; soma ponderada de medições de terceiros, sem veredito sobre a empresa', aplicavel: (c) => !!c.prontidao, Componente: ProntidaoOperadoraBloco })
def({ id: 'smp', semTitulo: true, titulo: 'SMP (telefonia móvel)', ordem: 40, depende: ['useOperadoraPerfil'], fontes: ['anatel_outorgas', 'anatel_sici_movel'], selo: 'fato',
  nota: 'duas datas: a do snapshot e o mês de referência da declaração ao SICI móvel', aplicavel: (c) => (c.servicos ?? []).some((s) => s.sigla === 'SMP') || c.dataMovel?.acessos != null, Componente: SmpBloco })
def({ id: 'stfc', semTitulo: true, titulo: 'STFC (telefonia fixa comutada)', ordem: 50, depende: ['operadora-stfc'], fontes: ['anatel_outorgas'], selo: 'fato', aplicavel: (c) => c.hasStfc, Componente: StfcBloco })
def({ id: 'seac', semTitulo: true, titulo: 'SeAC (TV por assinatura)', ordem: 60, depende: ['operadora-seac'], fontes: ['anatel_outorgas'], selo: 'fato', aplicavel: (c) => c.hasSeac, Componente: SeacBloco })
def({ id: 'linha-do-tempo', titulo: 'Linha do tempo', ordem: 70, depende: ['useOperadoraPerfil'], fontes: ['registro_br', 'fulltable_routeviews', 'lg_ixbr', 'rpki_collector', 'apnic_pop'], selo: 'fato', nota: 'diferenças observadas entre snapshots',
  aplicavel: (c) => !!c.historico, Componente: LinhaDoTempoOperadora })

def({ id: 'sobreposicao', titulo: 'Quem aparece nos mesmos municípios', ordem: 55, depende: ['useOperadoraPerfil'], fontes: ['anatel_sici', 'socios_grupos'], selo: 'fato',
  nota: 'presença nos mesmos municípios, sem implicar rivalidade nem disputa de clientes; a marca "mesmo grupo" é inferência do quadro societário', aplicavel: (c) => !!c.sobreposicao, Componente: SobreposicaoBloco })
