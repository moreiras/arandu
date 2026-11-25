// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../../components/entidade/AcoesEntidade'
import { Migalhas } from '../../components/layout/Migalhas'
import { nomeExibicao } from '../../lib/nomes'
import { Link } from '../../components/layout/LinkDatado'
import { EntityHeader } from '../../components/entidade'
import { ContactsReveal, type ContactsAvailable } from '../../components/ContactsReveal'
import { OutorgaBadge, OutorgaBadges } from '../../components/OutorgaBadge'
import type { AsnVinculado, GrupoCnpjEntry, GrupoSocietarioResumo } from '../../types/api'
import { fmtCnpj } from './ui'
import { ROTULO_SA_NAO_INFERIVEL, COMO_LER_SA } from '../grupo/SemInferenciaSA'
import { ComoLer } from '../../components/ui/ComoLer'
import type { ServicoOperadora } from './servicos'

/** Rótulo curto do vínculo ASN ↔ CNPJ (D5) na tela. */
const ROTULO_VINCULO: Record<string, string> = { cnpj: 'mesmo CNPJ', raiz: 'mesma raiz do CNPJ', marca: 'mesma marca', estrangeiro: 'AS estrangeiro' }

/** Cabeçalho da página de operadora: nome com selos de outorga, grupo, porte, razão social/CNPJ/sede, outros CNPJs do grupo, contatos e ASNs. */
export function CabecalhoOperadora({ nome, grupo, porte, hasScm, hasSmp, hasStfc, hasSeac, credenciadaSmp, razaoSocial, cnpjFinal, municipio, uf, grupoCnpjs, grupoSocietario, grupoSocietarioCarregando, contactsAvailable, fetchContacts, asns, vinculados = [], snapshot }: {
  nome: string
  grupo?: string
  porte?: string
  hasScm: boolean
  hasSmp: boolean
  hasStfc: boolean
  hasSeac: boolean
  /** Credenciamento de rede virtual no SMP (sem outorga própria): selo "MVNO", nunca "SMP". */
  credenciadaSmp?: ServicoOperadora
  razaoSocial?: string
  cnpjFinal: string
  municipio?: string
  uf?: string
  grupoCnpjs: GrupoCnpjEntry[]
  /** Grupo societário do CNPJ (`GET /grupos/empresa/{cnpj}`, chamado sempre): nome por regra visível, tamanho e integrantes; inferido do quadro da Receita. */
  grupoSocietario?: GrupoSocietarioResumo | null
  grupoSocietarioCarregando?: boolean
  contactsAvailable?: ContactsAvailable
  fetchContacts: () => Promise<any>
  asns: number[]
  /** Vínculo ASN ↔ CNPJ (D5) além do mesmo CNPJ: raiz, marca e estrangeiro, com selo inferido. */
  vinculados?: AsnVinculado[]
  snapshot?: string
}) {
  return (
    <EntityHeader
      trilha={<Migalhas grupo="mercado" itens={[{ rotulo: 'Operadoras', to: '/operadoras' }, { rotulo: nomeExibicao(nome) }]} />}
      nome={nome}
      ladoDoNome={
        <>
          {grupo && grupo !== 'OUTROS' && (
          <span className="text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5">
            grupo {grupo}
          </span>
          )}
          {porte && <span className="text-xs text-gray-400">{porte}</span>}
          {hasScm && <OutorgaBadge label="SCM" />}
          {hasSmp && <OutorgaBadge label="SMP" />}
          {!hasSmp && credenciadaSmp && (
            <span className="text-xs font-semibold bg-v6-100 text-v6-800 rounded px-1.5 py-0.5">
              MVNO<span className="sr-only">: credenciada de rede virtual no SMP{credenciadaSmp.origem?.nome ? ` de ${credenciadaSmp.origem.nome}` : ''}, sem outorga SMP própria</span>
            </span>
          )}
          {hasStfc && <OutorgaBadge label="STFC" />}
          {hasSeac && <OutorgaBadge label="SeAC" />}
        </>
      }
      snapshot={snapshot}
      acoes={cnpjFinal ? <AcoesEntidade tipo="operadora" id={cnpjFinal.replace(/\D/g, '')} /> : undefined}
    >
        <div className="text-sm text-gray-500 mt-0.5">
          {razaoSocial && razaoSocial !== nome && (
            <span>{razaoSocial} · </span>
          )}
          <span className="font-mono">{fmtCnpj(cnpjFinal)}</span>
          {municipio && <span> · sede em {municipio}/{uf}</span>}
        </div>
        {/* OPERADORA-E10: duas definições de grupo, cada uma com a sua origem; o SICI é declarado, o societário é inferido */}
        <dl className="text-sm text-gray-500 mt-1 space-y-1" aria-label="Grupos da operadora">
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1" data-testid="grupo-sici">
            <dt className="text-gray-400">Grupo no SICI (declarado à Anatel):</dt>
            <dd className="contents">
              {grupo && grupo !== 'OUTROS' ? (
                <>
                  <span className="font-medium text-gray-700">{grupo}</span>
                  {grupoCnpjs.length > 0 ? grupoCnpjs.map(e => (
                    <span key={e.cnpj} className="inline-flex items-center gap-1">
                      <Link to={`/operadora/${e.cnpj}`} className="text-primario-600 hover:underline">{e.empresa || fmtCnpj(e.cnpj)}</Link>
                      <OutorgaBadges flags={e} />
                    </span>
                  )) : <span>(nenhum outro CNPJ declarado com este grupo)</span>}
                </>
              ) : <span>nenhum grupo declarado{grupo === 'OUTROS' ? ' (a Anatel registra "OUTROS")' : ''}</span>}
            </dd>
          </div>
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1" data-testid="grupo-societario">
            <dt className="text-gray-400">Grupo societário (inferido do quadro societário da Receita):</dt>
            <dd className="contents">
              {grupoSocietarioCarregando && !grupoSocietario ? <span>carregando…</span>
                : !grupoSocietario ? <span>sem informação do quadro societário neste snapshot</span>
                : grupoSocietario.grupo_inferivel === false && grupoSocietario.tamanho <= 1 ? (
                  <>
                    <span className="font-medium text-gray-700" data-testid="rotulo-sa">{ROTULO_SA_NAO_INFERIVEL}</span>
                    <span>(grupo declarado ao SICI: {grupo && grupo !== 'OUTROS' ? <span className="font-medium text-gray-700">{grupo}</span> : 'nenhum'})</span>
                    <Link to={`/grupo/${encodeURIComponent(grupoSocietario.grupo_id)}`} className="text-primario-600 hover:underline font-medium">ver o grupo</Link>
                  </>
                ) : grupoSocietario.tamanho <= 1 ? (
                  <>
                    <span>só este CNPJ, sem ligação societária com outra operadora</span>
                    <Link to={`/grupo/${encodeURIComponent(grupoSocietario.grupo_id)}`} className="text-primario-600 hover:underline font-medium">ver o grupo</Link>
                  </>
                ) : (
                  <>
                    <Link to={`/grupo/${encodeURIComponent(grupoSocietario.grupo_id)}`} className="text-primario-600 hover:underline font-medium">{grupoSocietario.nome} ({grupoSocietario.tamanho} empresas)</Link>
                    {grupoSocietario.integrantes.map(e => (
                      <span key={e.cnpj} className="inline-flex items-center gap-1">
                        <Link to={`/operadora/${e.cnpj}`} className="text-primario-600 hover:underline">{e.empresa || fmtCnpj(e.cnpj)}</Link>
                        <OutorgaBadges flags={e} />
                      </span>
                    ))}
                    {grupoSocietario.integrantes_total > grupoSocietario.integrantes.length && <span>e mais {grupoSocietario.integrantes_total - grupoSocietario.integrantes.length}</span>}
                    {grupoSocietario.grupo_inferivel === false && <span data-testid="rotulo-sa-em-grupo">(o quadro desta S.A. não foi usado: a ligação vem do quadro de outra empresa)</span>}
                  </>
                )}
            </dd>
          </div>
          {grupoSocietario?.grupo_inferivel === false && <ComoLer className="max-w-3xl"><p>{grupoSocietario.como_ler || COMO_LER_SA}</p></ComoLer>}
        </dl>
        <ContactsReveal
          available={contactsAvailable}
          fetchContacts={fetchContacts}
        />
        <div className="flex flex-wrap gap-2 mt-2">
          {asns.map(a => (
            <Link key={a} to={`/asn/${a}`}
                  className="px-2.5 py-1 rounded border border-primario-200 bg-primario-50 text-primario-700 text-xs hover:bg-primario-100">
              AS{a}
            </Link>
          ))}
          {!asns.length && (
            <span className="text-xs text-gray-400 border border-gray-200 rounded px-2.5 py-1">
              sem ASN no Registro.br com este CNPJ
            </span>
          )}
          {vinculados.filter(v => v.vinculo !== 'cnpj').map(v => (
            <Link key={v.asn} to={`/asn/${v.asn}`} title={ROTULO_VINCULO[v.vinculo] + (v.marca ? `: ${v.marca}` : '')}
                  className="px-2.5 py-1 rounded border border-dashed border-gray-300 bg-white text-gray-700 text-xs hover:bg-gray-50">
              AS{v.asn} <span className="text-gray-500">({ROTULO_VINCULO[v.vinculo]}, inferido)</span>
            </Link>
          ))}
        </div>
    </EntityHeader>
  )
}
