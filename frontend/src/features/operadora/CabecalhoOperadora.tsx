// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AcoesEntidade } from '../../components/entidade/AcoesEntidade'
import { Migalhas } from '../../components/layout/Migalhas'
import { nomeExibicao } from '../../lib/nomes'
import { Link } from 'react-router-dom'
import { EntityHeader } from '../../components/entidade'
import { ContactsReveal, type ContactsAvailable } from '../../components/ContactsReveal'
import { OutorgaBadge, OutorgaBadges } from '../../components/OutorgaBadge'
import type { GrupoCnpjEntry } from '../../types/api'
import { fmtCnpj } from './ui'

/** Cabeçalho da página de operadora: nome com selos de outorga, grupo, porte, razão social/CNPJ/sede, outros CNPJs do grupo, contatos e ASNs. */
export function CabecalhoOperadora({ nome, grupo, porte, hasScm, hasSmp, hasStfc, hasSeac, razaoSocial, cnpjFinal, municipio, uf, grupoCnpjs, grupoId, contactsAvailable, fetchContacts, asns, snapshot }: {
  nome: string
  grupo?: string
  porte?: string
  hasScm: boolean
  hasSmp: boolean
  hasStfc: boolean
  hasSeac: boolean
  razaoSocial?: string
  cnpjFinal: string
  municipio?: string
  uf?: string
  grupoCnpjs: GrupoCnpjEntry[]
  /** Identificador do grupo (`GET /grupos`): leva à página do grupo. */
  grupoId?: string
  contactsAvailable?: ContactsAvailable
  fetchContacts: () => Promise<any>
  asns: number[]
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
        {grupoCnpjs.length > 0 && (
          <div className="text-sm text-gray-500 mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1">
            <span className="text-gray-400">outros CNPJs do grupo {grupo}:</span>
            {grupoId && <Link to={`/grupo/${encodeURIComponent(grupoId)}`} className="text-primario-600 hover:underline font-medium">ver o grupo</Link>}
            {grupoCnpjs.map(e => (
              <span key={e.cnpj} className="inline-flex items-center gap-1">
                <Link to={`/operadora/${e.cnpj}`} className="text-primario-600 hover:underline">
                  {e.empresa || fmtCnpj(e.cnpj)}
                </Link>
                <OutorgaBadges flags={e} />
              </span>
            ))}
          </div>
        )}
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
              sem ASN próprio no Registro.br
            </span>
          )}
        </div>
    </EntityHeader>
  )
}
