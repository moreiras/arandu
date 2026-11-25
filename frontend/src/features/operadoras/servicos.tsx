// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import { fetchOperadorasMovel, fetchOutorgas, fetchOutorgasMapa, fetchOutorgasStats, type ServicoOutorga } from '../../services/api'
import { fmtCnpj, fmtNum } from './formato'

export type ServicoId = 'scm' | 'smp' | 'stfc' | 'seac' | 'todas'

export interface Coluna {
  key: string
  label: string
  w: string
  ordenavel: boolean
  render: (r: any) => ReactNode
  /** Explicação no cabeçalho (ⓘ); sem ela vale `DICAS_COLUNA[key]`. */
  dica?: string
}

/** Explicações das colunas das listas de outorgas, por chave (tabelas com Dica). */
export const DICAS_COLUNA: Record<string, string> = {
  data_outorga: 'Data registrada no cadastro de outorgas da Anatel (no SCM, a data de inclusão da outorga no cadastro). Pode ser a de um recadastramento, não a da outorga original.',
  acessos_fixo: 'Acessos fixos declarados ao SICI (Anatel) no mês de referência. Ter outorga não significa estar operando.',
  acessos_movel: 'Acessos móveis declarados à Anatel no mês de referência.',
  pj_fixo: 'Acessos fixos de pessoa jurídica declarados ao SICI.',
  municipios_fixo: 'Municípios com pelo menos um acesso fixo declarado ao SICI.',
  asns: 'ASNs registrados no Registro.br com o mesmo CNPJ.',
  porte: 'Porte declarado ao SICI.',
}

export interface OpcoesLista {
  date?: string; page: number; limit: number; uf?: string; q?: string; comAsn: boolean; soAtivos: boolean; sortBy: string; sortDesc: boolean
  /** Só na aba "Todas": serviços combinados (qualquer um, ou todos com `todos`) e porte declarado ao SICI. */
  servicos?: ServicoOutorga[]; todos?: boolean; porte?: string
}

/**
 * Um serviço de telecomunicações outorgado pela Anatel. A página `/operadoras` é uma só; cada serviço entra com a sua rota
 * de lista/estatística/mapa, as colunas que tem e os padrões de filtro e ordenação que as quatro páginas antigas já usavam.
 * Serviço novo = uma entrada aqui.
 */
export interface Servico {
  id: ServicoId
  /** Nome curto (aba, legenda do mapa). */
  rotulo: string
  titulo: string
  descricao: ReactNode
  /** Primeira chave da consulta da lista (cache compartilhado com o que as páginas antigas usavam). */
  chaveLista: string
  /** Sem `stats`/`mapa` (aba "Todas") a página não mostra os totais nem o mapa. */
  stats?: (date?: string) => Promise<any>
  mapa?: (o: { date?: string; uf?: string; com_asn?: boolean }) => Promise<any>
  listar: (o: OpcoesLista) => Promise<any>
  /** Há declaração de acessos ao SICI para este serviço (filtro "em operação" e aba de mapa de acessos). */
  temSici: boolean
  dicaOperacao?: string
  soAtivosPadrao: boolean
  ordenacaoPadrao: { campo: string; desc: boolean }
  /** Sentido ao clicar numa coluna nova. */
  primeiroCliqueDesc: boolean
  unidade: string
  indisponivel: string
  colunas: Coluna[]
}

const Anatel = <span className="font-medium">Anatel</span>
const traco = <span className="text-gray-300">—</span>

const asnsCell = (r: { asns?: number[] }) =>
  r.asns && r.asns.length > 0 ? (
    <div className="flex flex-wrap gap-x-1 gap-y-[6px]">
      {r.asns.map((a) => <Link key={a} to={`/asn/${a}`} className="-my-[3px] py-[3px] text-primario-600 hover:underline">AS{a}</Link>)}
    </div>
  ) : traco

const colunasPrestadora = (sigla: ServicoOutorga): Coluna[] => [
  {
    key: 'razao_social', label: 'Prestadora', w: '', ordenavel: true,
    render: (r) => (
      <>
        <Link to={`/operadora/${r.cnpj}`} className="font-medium text-gray-900 truncate block hover:text-primario-600 hover:underline">{r.nome_fantasia || r.razao_social}</Link>
        <div className="text-xs text-gray-400 font-mono truncate">{fmtCnpj(r.cnpj)}</div>
      </>
    ),
  },
  { key: 'uf', label: 'UF', w: 'w-16', ordenavel: true, render: (r) => <span className="text-gray-600">{r.uf ?? '—'}</span> },
  { key: 'municipio', label: 'Município', w: 'w-40', ordenavel: true, render: (r) => <span className="text-gray-600 truncate">{r.municipio ?? '—'}</span> },
  { key: 'data_outorga', label: 'Data no cadastro', w: 'w-24', ordenavel: true, render: (r) => <span className="text-gray-500">{r.data_outorga_por_servico?.[sigla] ?? '—'}</span> },
  { key: 'asns', label: 'ASN(s)', w: 'w-32', ordenavel: true, render: asnsCell },
]

export const SERVICOS: Record<ServicoId, Servico> = {
  scm: {
    id: 'scm', rotulo: 'SCM', titulo: 'Outorgas SCM', chaveLista: 'scms', temSici: true, soAtivosPadrao: false,
    descricao: <>Serviço de Comunicação Multimídia — dados abertos da {Anatel}, cruzados com ASNs do Registro.br por CNPJ.</>,
    dicaOperacao: 'Ter outorga não significa estar operando: cerca de metade dos CNPJs com outorga não declara acesso ao SICI. Este filtro conta quem declarou acesso fixo ou móvel; os CNPJs com outorga SCM que declararam acesso fixo (cobertura de declaração, na home) são um pouco menos.',
    ordenacaoPadrao: { campo: 'acessos_fixo', desc: true }, primeiroCliqueDesc: false, unidade: 'outorgas',
    indisponivel: 'Dados de SCM não disponíveis para este snapshot. Rode as etapas anatel_scm e scm_geo para coletar os dados da Anatel.',
    stats: (d) => fetchOutorgasStats('SCM', d), mapa: (o) => fetchOutorgasMapa('SCM', o),
    listar: (o) => fetchOutorgas({
      date: o.date, page: o.page, limit: o.limit, servico: ['SCM'], uf: o.uf, q: o.q, com_asn: o.comAsn || undefined, ativo: o.soAtivos || undefined,
      sort_by: o.sortBy || undefined, sort_desc: o.sortDesc,
    }),
    colunas: [
      { key: 'cnpj', label: 'CNPJ', w: 'w-36', ordenavel: true,
        render: (r) => <Link to={`/operadora/${r.cnpj}`} className="font-mono text-gray-600 whitespace-nowrap hover:underline hover:text-primario-600">{fmtCnpj(r.cnpj)}</Link> },
      { key: 'razao_social', label: 'Razão Social / Nome Fantasia', w: '', ordenavel: true,
        render: (r) => (
          <>
            <Link to={`/operadora/${r.cnpj}`} className="font-medium text-gray-900 truncate block hover:text-primario-600 hover:underline">{r.razao_social}</Link>
            {r.nome_fantasia && <div className="text-xs text-gray-400 truncate">{r.nome_fantasia}</div>}
          </>
        ) },
      { key: 'municipio', label: 'Município / UF', w: 'w-40', ordenavel: true,
        render: (r) => <span className="text-gray-600 truncate">{r.municipio && <span>{r.municipio}</span>}{r.uf && <span className="ml-1 text-gray-400">/{r.uf}</span>}</span> },
      { key: 'data_outorga', label: 'Data no cadastro', w: 'w-24', ordenavel: true, render: (r) => <span className="text-gray-500">{r.data_outorga_por_servico?.SCM ?? '—'}</span> },
      { key: 'acessos_fixo', label: 'Acessos', w: 'w-24', ordenavel: true,
        render: (r) => r.acessos_fixo > 0
          ? <Link to={`/operadora/${r.cnpj}`} className="block text-right tabular-nums text-primario-600 hover:underline">{fmtNum(r.acessos_fixo)}</Link>
          : <span className="block text-right text-gray-300" title="Sem acesso declarado ao SICI no mês de referência">—</span> },
      { key: 'pj_fixo', label: 'B2B', w: 'w-20', ordenavel: true,
        render: (r) => r.acessos_fixo > 0 ? <span className="block text-right tabular-nums text-gray-500">{fmtNum(r.pj_fixo)}</span> : <span className="block text-right text-gray-300">—</span> },
      { key: 'municipios_fixo', label: 'Munic.', w: 'w-20', ordenavel: true,
        render: (r) => r.acessos_fixo > 0 ? <span className="block text-right tabular-nums text-gray-500">{fmtNum(r.municipios_fixo)}</span> : <span className="block text-right text-gray-300">—</span> },
      { key: 'asns', label: 'ASN(s)', w: 'w-36', ordenavel: true, render: asnsCell },
    ],
  },
  smp: {
    // padrão: o universo (outorgadas e credenciadas, com e sem declaração); o filtro visível restringe (OPERADORAS-E2)
    id: 'smp', rotulo: 'SMP', titulo: 'Operadoras SMP', chaveLista: 'operadoras-movel', temSici: true, soAtivosPadrao: false,
    descricao: <>Serviço Móvel Pessoal — dados abertos da {Anatel}, cruzados com ASNs do Registro.br por CNPJ. Universo pequeno: as grandes operadoras móveis e MVNOs/M2M.</>,
    dicaOperacao: 'Ter outorga não significa estar operando',
    ordenacaoPadrao: { campo: 'acessos', desc: true }, primeiroCliqueDesc: true, unidade: 'operadoras',
    indisponivel: 'Dados de SMP não disponíveis para este snapshot. Rode as etapas anatel_smp, smp_geo e anatel_sici_movel para coletar os dados da Anatel.',
    stats: (d) => fetchOutorgasStats('SMP', d), mapa: (o) => fetchOutorgasMapa('SMP', o),
    // `ativo` só vai quando o filtro está ligado: omitido, a API devolve o universo móvel
    listar: (o) => fetchOperadorasMovel({
      date: o.date, page: o.page, limit: o.limit, uf: o.uf, q: o.q, com_asn: o.comAsn || undefined, ativo: o.soAtivos ? true : undefined,
      sort_by: o.sortBy || undefined, sort_desc: o.sortDesc,
    }),
    colunas: [
      { key: 'empresa', label: 'Operadora', w: '', ordenavel: true,
        render: (r) => (
          <>
            <Link to={`/operadora/${r.cnpj}`} className="font-medium text-gray-900 truncate block hover:text-primario-600 hover:underline">{r.empresa || r.razao_social}</Link>
            <div className="text-xs text-gray-400 font-mono truncate">{fmtCnpj(r.cnpj)}</div>
          </>
        ) },
      { key: 'uf_sede', label: 'UF sede', w: 'w-20', ordenavel: true, render: (r) => <span className="text-gray-600">{r.uf_sede ?? '—'}</span> },
      { key: 'acessos', label: 'Acessos', w: 'w-24', ordenavel: true,
        render: (r) => r.ativo
          ? <Link to={`/operadora/${r.cnpj}`} className="block text-right tabular-nums text-primario-600 hover:underline">{fmtNum(r.acessos)}</Link>
          : <span className="block text-right text-gray-300" title="Sem acesso declarado ao SICI no mês de referência">—</span> },
      { key: 'acessos_pj', label: 'B2B', w: 'w-20', ordenavel: true,
        render: (r) => r.ativo ? <span className="block text-right tabular-nums text-gray-500">{fmtNum(r.acessos_pj)}</span> : <span className="block text-right text-gray-300">—</span> },
      { key: 'municipios', label: 'Munic.', w: 'w-20', ordenavel: true,
        render: (r) => r.ativo ? <span className="block text-right tabular-nums text-gray-500">{fmtNum(r.municipios)}</span> : <span className="block text-right text-gray-300">—</span> },
      { key: 'geracao', label: 'Geração', w: 'w-20', ordenavel: false, render: (r) => <span className="text-gray-500">{r.geracao_predominante ?? traco}</span> },
      { key: 'asns', label: 'ASN(s)', w: 'w-32', ordenavel: false, render: asnsCell },
      { key: 'rede_virtual', label: 'Rede virtual', w: 'w-28', ordenavel: false,
        render: (r) => (
          <>
            {r.rede_virtual?.papel === 'host' && (
              <span className="px-1.5 py-0.5 rounded bg-primario-100 text-primario-800 font-medium whitespace-nowrap" title={`Credencia ${r.rede_virtual.credenciadas_count} operadora(s) MVNO`}>
                Host ({r.rede_virtual.credenciadas_count})
              </span>
            )}
            {r.rede_virtual?.papel === 'credenciada' && (
              <>
                {/* com data de outorga a empresa tem outorga SMP própria e também é credenciada: os dois fatos (OPERADORAS-E12) */}
                {r.data_outorga && <span className="block text-gray-600 whitespace-nowrap">Outorga própria</span>}
                <Link to={`/operadora/${r.rede_virtual.prestadora_origem_cnpj}`} title={`Credenciada de ${r.rede_virtual.prestadora_origem_nome}`}
                  className="px-1.5 py-0.5 rounded bg-v6-100 text-v6-800 font-medium whitespace-nowrap hover:bg-v6-200">MVNO</Link>
                {!r.data_outorga && <span className="block text-gray-500 whitespace-nowrap">sem outorga SMP própria</span>}
              </>
            )}
            {!r.rede_virtual && traco}
          </>
        ) },
    ],
  },
  stfc: {
    id: 'stfc', rotulo: 'STFC', titulo: 'Outorgas STFC', chaveLista: 'stfcs', temSici: false, soAtivosPadrao: false,
    descricao: <>Serviço Telefônico Fixo Comutado — dados abertos da {Anatel}, cruzados com ASNs do Registro.br por CNPJ. Universo maior que SMP: inclui pequenos provedores de VoIP/telefonia fixa.</>,
    ordenacaoPadrao: { campo: 'razao_social', desc: false }, primeiroCliqueDesc: false, unidade: 'outorgas',
    indisponivel: 'Dados de STFC não disponíveis para este snapshot.',
    stats: (d) => fetchOutorgasStats('STFC', d), mapa: (o) => fetchOutorgasMapa('STFC', o),
    listar: (o) => fetchOutorgas({ date: o.date, page: o.page, limit: o.limit, servico: ['STFC'], uf: o.uf, q: o.q, com_asn: o.comAsn || undefined, sort_by: o.sortBy || undefined, sort_desc: o.sortDesc }),
    colunas: colunasPrestadora('STFC'),
  },
  seac: {
    id: 'seac', rotulo: 'SeAC', titulo: 'Outorgas SeAC', chaveLista: 'seacs', temSici: false, soAtivosPadrao: false,
    descricao: <>Serviço de Acesso Condicionado — dados abertos da {Anatel}, cruzados com ASNs do Registro.br por CNPJ. TV por assinatura — outorgas SeAC (Lei 12.485/2011).</>,
    ordenacaoPadrao: { campo: 'razao_social', desc: false }, primeiroCliqueDesc: false, unidade: 'outorgas',
    indisponivel: 'Dados de SEAC não disponíveis para este snapshot.',
    stats: (d) => fetchOutorgasStats('SeAC', d), mapa: (o) => fetchOutorgasMapa('SeAC', o),
    listar: (o) => fetchOutorgas({ date: o.date, page: o.page, limit: o.limit, servico: ['SeAC'], uf: o.uf, q: o.q, com_asn: o.comAsn || undefined, sort_by: o.sortBy || undefined, sort_desc: o.sortDesc }),
    colunas: colunasPrestadora('SeAC'),
  },
  todas: {
    id: 'todas', rotulo: 'Combinar serviços', titulo: 'Outorgas por serviço, combinadas', chaveLista: 'outorgas', temSici: false, soAtivosPadrao: false,
    descricao: <>Uma linha por CNPJ, com os serviços de outorga que ele tem na {Anatel} (SCM, SMP, STFC, SeAC) e os acessos que declarou ao SICI. Combine os serviços (qualquer um ou todos), a UF e o porte.</>,
    ordenacaoPadrao: { campo: 'acessos', desc: true }, primeiroCliqueDesc: true, unidade: 'prestadoras',
    indisponivel: 'Dados de outorgas não disponíveis para este snapshot.',
    listar: (o) => fetchOutorgas({
      date: o.date, page: o.page, limit: o.limit, servico: o.servicos, todos: o.todos, uf: o.uf, q: o.q, com_asn: o.comAsn || undefined,
      ativo: o.soAtivos || undefined, porte: o.porte, sort_by: o.sortBy || undefined, sort_desc: o.sortDesc,
    }),
    colunas: [
      ...colunasPrestadora('SCM').slice(0, 2),
      { key: 'servicos', label: 'Serviços', w: 'w-40', ordenavel: true,
        render: (r) => <div className="flex flex-wrap gap-1">{(r.servicos as string[]).map((sv) => <span key={sv} className="px-1.5 py-0.5 rounded bg-primario-50 text-primario-800 font-medium">{sv}</span>)}</div> },
      { key: 'acessos_fixo', label: 'Acessos fixos', w: 'w-24', ordenavel: true,
        render: (r) => r.acessos_fixo > 0 ? <span className="block text-right tabular-nums text-gray-700">{fmtNum(r.acessos_fixo)}</span> : <span className="block text-right text-gray-300">—</span> },
      { key: 'acessos_movel', label: 'Acessos móveis', w: 'w-24', ordenavel: true,
        render: (r) => r.acessos_movel > 0 ? <span className="block text-right tabular-nums text-gray-700">{fmtNum(r.acessos_movel)}</span> : <span className="block text-right text-gray-300">—</span> },
      { key: 'porte', label: 'Porte', w: 'w-28', ordenavel: false, render: (r) => <span className="text-gray-500">{r.porte || traco}</span> },
      { key: 'asns', label: 'ASN(s)', w: 'w-32', ordenavel: true, render: asnsCell },
    ],
  },
}

export const ORDEM_SERVICOS: ServicoId[] = ['scm', 'smp', 'stfc', 'seac', 'todas']

export function servicoDe(valor: string | null | undefined): Servico {
  return SERVICOS[(valor ?? '').toLowerCase() as ServicoId] ?? SERVICOS.scm
}
