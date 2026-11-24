// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { Kpi } from '../../components/ui'
import { AccessMunicipioMap } from '../../components/acessos/AccessMunicipioMap'
import { AsnBadge, OutorgaBadges } from '../../components/OutorgaBadge'
import { registrarAbas, registrarBloco, type BlocoDef, type BlocoProps } from '../entidade/registry'
import { ConcorrentesBloco, SeriePosicaoBloco, UfsBloco } from './blocks/MercadoBlocos'
import { RelacoesGrupoBloco } from './blocks/RelacoesGrupoBloco'
import { AsesTecnicoBloco, OutorgasMultasBloco, PttsTransitoBloco, QualidadeReclamacoesBloco } from './blocks/RegulatorioTecnicoBlocos'
import type { GrupoCtx } from './contexto'
import { useOrdenacao } from '../../lib/ordenacao'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'

const n = (v: number) => v.toLocaleString('pt-BR')
const reais = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
const fmtCnpj = (c: string) => { const d = c.replace(/\D/g, ''); return d.length === 14 ? `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}` : c }

const CLASSES: Record<string, string> = {
  total: 'Correspondência total: toda relação entre as empresas é de quadro de sócios idêntico ou controle exclusivo.',
  misto: 'Misto: há relações de quadro idêntico ou controle exclusivo e também de sócio em comum.',
  parcial: 'Correspondência parcial: as relações são de sócio em comum ou controle não exclusivo.',
  individual: 'Empresa individual: sem relação societária com outra empresa da base (grupo de uma empresa só).',
}

function Composicao({ dados }: BlocoProps<GrupoCtx>) {
  const g = dados.grupo
  const { ordenados, props } = useOrdenacao(g.cnpjs, {
    empresa: (c) => c.empresa || fmtCnpj(c.cnpj), cnpj: { valor: (c) => c.cnpj, primeiro: 'asc' }, assinantes: (c) => c.assinantes, asns: (c) => c.asns?.length || null,
  })
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">{CLASSES[g.classificacao]} A composição é inferida do quadro societário da Receita Federal: cada ligação entre duas empresas tem evidência direta (sócios em comum ou participação de uma na outra), e o grupo reúne as empresas ligadas em cadeia, então duas empresas podem estar no mesmo grupo sem ligação direta entre si; <strong>só a estrutura entre empresas é mostrada</strong>.</p>
      <table className="w-full text-sm" aria-label="Empresas do grupo">
        <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><ThOrdenavel {...props('empresa')} className="py-1 pr-3">Empresa</ThOrdenavel><ThOrdenavel {...props('cnpj')} className="pr-3">CNPJ</ThOrdenavel><th scope="col" className="pr-3">Serviços</th><ThOrdenavel {...props('assinantes')} alinhar="right" className="pr-3 text-right">Acessos fixos</ThOrdenavel><ThOrdenavel {...props('asns')}>ASNs</ThOrdenavel></tr></thead>
        <tbody>
          {ordenados.map((c) => (
            <tr key={c.cnpj} className="border-b border-gray-100 align-top">
              <td className="py-1 pr-3"><Link to={`/operadora/${c.cnpj}`} className="text-primario-600 hover:underline">{c.empresa || fmtCnpj(c.cnpj)}</Link></td>
              <td className="pr-3 font-mono text-xs text-gray-500">{fmtCnpj(c.cnpj)}</td>
              <td className="pr-3"><OutorgaBadges flags={c} /></td>
              <td className="pr-3 text-right tabular-nums">{n(c.assinantes)}</td>
              <td><AsnBadge asns={c.asns} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Mercado({ dados }: BlocoProps<GrupoCtx>) {
  const g = dados.grupo
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi rotulo="Acessos fixos declarados (SICI)" valor={n(g.assinantes)} />
        <Kpi rotulo="Usuários estimados (APNIC)" valor={n(g.usuarios_apnic)} />
        <Kpi rotulo="Municípios com acessos" valor={n(g.municipios.length)} />
        <Kpi rotulo="Empresas no grupo" valor={n(g.empresas)} />
      </div>
      {g.municipios.length > 0 && <AccessMunicipioMap municipios={g.municipios.map((m) => ({ ...m }))} height={380} />}
      <p className="text-xs text-gray-500">Soma dos acessos declarados por todas as empresas do grupo; não inclui móvel. Uma empresa pode declarar em mais de um CNPJ: os acessos são por CNPJ, sem dupla contagem entre empresas do grupo.</p>
    </div>
  )
}

function Rede({ dados }: BlocoProps<GrupoCtx>) {
  const g = dados.grupo
  const porRaiz = new Set((g.asns_vinculados ?? []).filter((v) => v.vinculo === 'raiz').map((v) => v.asn))
  return (
    <div className="space-y-2 text-sm">
      {g.asns.length ? (
        <>
          <p className="text-gray-600">{n(g.asns.length)} {g.asns.length === 1 ? 'ASN' : 'ASNs'} das empresas do grupo; {g.visibilidade_bgp ? 'ao menos um origina blocos na tabela BGP global.' : 'nenhum origina blocos na tabela BGP global neste snapshot.'}</p>
          <div className="flex flex-wrap gap-2">
            {g.asns.map((a) => <Link key={a} to={`/asn/${a}`} className="px-2.5 py-1 rounded border border-primario-200 bg-primario-50 text-primario-700 text-xs hover:bg-primario-100">AS{a}{porRaiz.has(a) && <span className="text-gray-500"> (mesma raiz, inferido)</span>}</Link>)}
          </div>
          {porRaiz.size > 0 && <p className="text-xs text-gray-500">{n(porRaiz.size)} {porRaiz.size === 1 ? 'ASN está registrado' : 'ASNs estão registrados'} em outro CNPJ da mesma raiz de uma empresa do grupo (filial que não está na lista): vínculo inferido. Usuários e visibilidade contam cada ASN uma vez.</p>}
        </>
      ) : <p className="text-gray-600">Nenhuma empresa do grupo tem ASN no Registro.br, nem pelo CNPJ nem pela raiz do CNPJ.</p>}
    </div>
  )
}

function Credito({ dados }: BlocoProps<GrupoCtx>) {
  const c = dados.grupo.credito_publico
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi rotulo="Operações diretas do BNDES" valor={n(c.operacoes)} />
        <Kpi rotulo="Valor contratado" valor={reais(c.contratado)} />
        <Kpi rotulo="Valor desembolsado" valor={reais(c.desembolsado)} />
        <Kpi rotulo="Empresas com registro" valor={`${n(c.empresas_com_registro)} de ${n(dados.grupo.empresas)}`} />
      </div>
      <p className="text-xs text-gray-500">{c.natureza}.</p>
    </div>
  )
}

function Sancoes({ dados }: BlocoProps<GrupoCtx>) {
  const s = dados.grupo.sancoes
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi rotulo="Vigentes" valor={n(s.vigentes)} /><Kpi rotulo="Futuras" valor={n(s.futuras)} /><Kpi rotulo="Encerradas" valor={n(s.encerradas)} />
        <Kpi rotulo="Empresas com registro" valor={`${n(s.empresas_com_registro)} de ${n(dados.grupo.empresas)}`} />
      </div>
      <p className="text-xs text-gray-500">{s.natureza}. O detalhe de cada sanção está na página da empresa.</p>
    </div>
  )
}

function Contratos({ dados }: BlocoProps<GrupoCtx>) {
  const c = dados.grupo.contratos
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi rotulo="Itens publicados" valor={n(c.itens)} /><Kpi rotulo="Contratações" valor={n(c.contratacoes)} />
        <Kpi rotulo="Valor homologado" valor={reais(c.valor_homologado)} />
        <Kpi rotulo="Empresas lidas no rodízio" valor={`${n(c.empresas_lidas)} de ${n(dados.grupo.empresas)}`} />
      </div>
      <p className="text-xs text-gray-500">{c.natureza}. Empresa ainda não lida pelo rodízio não é empresa sem contratos.</p>
    </div>
  )
}

/** Lentes da página do grupo; aba sem bloco aplicável some. */
registrarAbas('grupo', [
  { id: 'geral', rotulo: 'Visão geral', descricao: 'Composição do grupo e números-chave do mercado.' },
  { id: 'mercado', rotulo: 'Mercado', descricao: 'Posição e série de acessos, UFs onde atua, concentração e empresas presentes nos mesmos municípios.' },
  { id: 'regulatorio', rotulo: 'Regulatório', descricao: 'Outorgas, multas, qualidade, reclamações, crédito público, sanções e contratos das empresas do grupo.' },
  { id: 'tecnico', rotulo: 'Técnico', descricao: 'ASes do grupo, IPv6, validação RPKI, trânsito e presença nos PTTs.' },
  { id: 'relacoes', rotulo: 'Relações', descricao: 'Com que evidência as empresas estão ligadas: tipo da ligação e quantos sócios a sustentam (sem nome de pessoa física).' },
])

const def = (b: Omit<BlocoDef<GrupoCtx>, 'entidade'>) => registrarBloco<GrupoCtx>({ entidade: 'grupo', ...b })
def({ id: 'composicao', aba: 'geral', titulo: 'Composição do grupo', ordem: 10, depende: ['useGrupoDetalhe'], fontes: ['receita_socios', 'socios_grupos', 'registro_br', 'anatel_outorgas'], selo: 'inferido',
  nota: 'a composição é inferida do quadro societário (evidência direta); sócios pessoas físicas não são mostrados', Componente: Composicao })
def({ id: 'mercado', aba: 'geral', titulo: 'Mercado consolidado', ordem: 20, depende: ['useGrupoDetalhe'], fontes: ['anatel_sici', 'apnic_pop'], selo: 'fato',
  nota: 'acessos declarados à Anatel pelas empresas do grupo; usuários APNIC são estimativa', Componente: Mercado })
def({ id: 'rede', aba: 'tecnico', titulo: 'Rede consolidada', ordem: 30, depende: ['useGrupoDetalhe'], fontes: ['registro_br', 'fulltable_routeviews'], selo: 'fato', Componente: Rede })
def({ id: 'credito-publico', aba: 'regulatorio', titulo: 'Crédito público (BNDES) somado', ordem: 40, depende: ['useGrupoDetalhe'], fontes: ['bndes_operacoes'], selo: 'fato',
  nota: 'soma das empresas do grupo que têm registro; ausência não é prova de que nunca houve crédito', Componente: Credito })
def({ id: 'sancoes', aba: 'regulatorio', titulo: 'Sanções (CEIS e CNEP) somadas', ordem: 50, depende: ['useGrupoDetalhe'], fontes: ['cgu_ceis_cnep'], selo: 'fato',
  nota: 'registro do órgão sancionador na data do arquivo da CGU; não é julgamento', Componente: Sancoes })
def({ id: 'contratos', aba: 'regulatorio', titulo: 'Contratos públicos (PNCP) somados', ordem: 60, depende: ['useGrupoDetalhe'], fontes: ['siasg_contratos'], selo: 'fato',
  nota: 'resultados de itens publicados no PNCP, em rodízio de leitura; não são contratos assinados nem pagamentos', Componente: Contratos })

def({ id: 'serie-posicao', aba: 'mercado', titulo: 'Posição e evolução no mercado fixo', ordem: 22, depende: ['useGrupoMercado'], fontes: ['anatel_sici', 'receita_socios'], selo: 'inferido',
  nota: 'acessos declarados à Anatel (fato) somados por um agrupamento inferido do quadro societário', Componente: SeriePosicaoBloco })
def({ id: 'ufs', aba: 'mercado', titulo: 'UFs onde atua e concentração do mercado', ordem: 24, depende: ['useGrupoMercado'], fontes: ['anatel_sici', 'receita_socios'], selo: 'inferido',
  nota: 'HHI do mercado da UF com os CNPJs do mesmo grupo contados como um (inferência societária)', Componente: UfsBloco })
def({ id: 'concorrentes', aba: 'mercado', titulo: 'Empresas presentes nos mesmos municípios', ordem: 26, depende: ['useGrupoMercado'], fontes: ['anatel_sici'], selo: 'fato',
  nota: 'presença conjunta nos municípios, não rivalidade', Componente: ConcorrentesBloco })
def({ id: 'outorgas-multas', aba: 'regulatorio', titulo: 'Outorgas e multas', ordem: 34, depende: ['useGrupoBloco'], fontes: ['anatel_outorgas', 'anatel_multas'], selo: 'inferido',
  nota: 'registros da Anatel somados por agrupamento inferido; multa constituída não é condenação definitiva', Componente: OutorgasMultasBloco })
def({ id: 'qualidade-reclamacoes', aba: 'regulatorio', titulo: 'Qualidade e reclamações', ordem: 36, depende: ['useGrupoBloco'], fontes: ['anatel_rqual', 'anatel_reclamacoes', 'consumidor_gov'], selo: 'inferido',
  nota: 'a ligação marca → CNPJ é curada ou por nome fantasia único; sem ranking', Componente: QualidadeReclamacoesBloco })
def({ id: 'ases-tecnico', aba: 'tecnico', titulo: 'ASes do grupo: IPv6, prefixos e RPKI', ordem: 31, depende: ['useGrupoBloco'], fontes: ['registro_br', 'fulltable_routeviews', 'rpki', 'apnic_pop'], selo: 'estimado',
  nota: 'observações do looking glass e estimativa de usuários APNIC, somadas por agrupamento inferido', Componente: AsesTecnicoBloco })
def({ id: 'ptts-transito', aba: 'tecnico', titulo: 'Trânsito e presença nos PTTs', ordem: 32, depende: ['useGrupoBloco'], fontes: ['lg_ixbr', 'fulltable_routeviews'], selo: 'fato',
  nota: 'sessões diretas observadas; não mede tráfego', Componente: PttsTransitoBloco })
def({ id: 'relacoes-grupo', aba: 'relacoes', titulo: 'Ligações entre as empresas do grupo', ordem: 70, depende: ['useGrupoBloco'], fontes: ['receita_socios', 'socios_grupos'], selo: 'inferido',
  nota: 'indício societário (Receita Federal): só estrutura entre empresas e a contagem de sócios, sem nome nem CPF', Componente: RelacoesGrupoBloco })
