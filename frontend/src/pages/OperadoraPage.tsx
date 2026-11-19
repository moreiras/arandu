// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchEmpresasRelacionadas, fetchOperadoraContacts, fetchOperadoraMovelContacts } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { useCadastroOperadora, useContratosOperadora, useFinanciamentoOperadora, useFontes, useOperadoraPerfil } from '../hooks/entidades'
import { EntityPage } from '../features/entidade/EntityPage'
import { CabecalhoOperadora } from '../features/operadora/CabecalhoOperadora'
import { FichaOperadora } from '../features/operadora/FichaOperadora'
import type { OperadoraCtx } from '../features/operadora/contexto'
import { fmtCnpj, mergeGrupoCnpjs } from '../features/operadora/ui'
import '../features/operadora'

/**
 * Página da operadora, por CNPJ.
 *
 * O CNPJ é a chave que une outorga SCM, ASNs do Registro.br e grupo econômico.
 * Aqui ele vira entidade navegável: ASNs (com agregação de rede), outorgas SCM/SMP e, quando declarados, os
 * acessos ao SICI (fixo e móvel) — cada bloco (`features/operadora`) aparece só se a fonte
 * correspondente existir. Um CNPJ pode ter só SCM, só SMP, ou os dois (as grandes operadoras).
 */
export function OperadoraPage() {
  const { cnpj } = useParams<{ cnpj: string }>()
  const [params] = useSearchParams()
  const versaoAntiga = params.get('versao') === '1'      // a página sem ficha e sem abas (`?versao=1`)
  const { fontes } = useFontes()

  const q = useOperadoraPerfil(cnpj)
  const cadastro = useCadastroOperadora(cnpj)
  const financiamento = useFinanciamentoOperadora(cnpj)
  const contratos = useContratosOperadora(cnpj)
  const { data, dataMovel, dataStfc, dataSeac } = q.dados ?? {}
  // o grupo vem do cruzamento societário (mesma chave do bloco "Empresas relacionadas": a resposta é reaproveitada ao abrir a aba Empresa)
  const temGrupo = !!(data?.grupo_cnpjs?.length || dataMovel?.grupo_cnpjs?.length)
  const dataAtiva = useActiveDate()
  const relacionadas = useQuery({ queryKey: ['empresas-relacionadas', cnpj, dataAtiva], queryFn: () => fetchEmpresasRelacionadas(cnpj!, dataAtiva ?? undefined), enabled: temGrupo && !!cnpj && !!dataAtiva, staleTime: Infinity, retry: false })

  if (q.isLoading) return <div className="text-sm text-gray-400">Carregando…</div>
  if (!data && !dataMovel && !dataStfc?.outorgas.length && !dataSeac?.outorgas.length && !q.dados?.perfil?.multas) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">Não há informação para este CNPJ</h1>
        <p className="text-sm text-gray-500">
          {fmtCnpj(cnpj ?? '')} não tem ASN no Registro.br, outorga SCM/SMP/STFC/SeAC na
          Anatel nem declaração de acessos ao SICI neste snapshot.
        </p>
        <Link to="/operadoras" className="text-sm text-primario-600 hover:underline mt-3 inline-block">
          ← Voltar para a lista de provedores
        </Link>
      </div>
    )
  }

  const outorga = data?.outorgas_scm?.[0]
  const outorgaSmp = dataMovel?.outorgas_smp?.[0]
  const hasScm = !!(data?.outorgas_scm?.length)
  const hasSmp = !!(dataMovel?.outorgas_smp?.length)
  const hasStfc = !!(dataStfc?.outorgas.length)
  const hasSeac = !!(dataSeac?.outorgas.length)
  const hasSici = data?.acessos != null
  const b2cPct = hasSici && data?.acessos ? (100 * (data.pf ?? 0)) / data.acessos : 0
  const outorgaStfc = dataStfc?.outorgas[0]
  const outorgaSeac = dataSeac?.outorgas[0]
  const nome = data?.empresa || outorga?.razao_social || dataMovel?.empresa || outorgaSmp?.razao_social
    || outorgaStfc?.razao_social || outorgaSeac?.razao_social || q.dados?.perfil?.multas?.por_grupo[0]?.entidade || fmtCnpj(cnpj ?? '')
  const cnpjFinal = data?.cnpj || dataMovel?.cnpj || dataStfc?.cnpj || dataSeac?.cnpj || cnpj || ''
  const grupo = data?.grupo || dataMovel?.grupo
  const grupoCnpjs = mergeGrupoCnpjs(data?.grupo_cnpjs, dataMovel?.grupo_cnpjs)
  const porte = data?.porte || dataMovel?.porte
  const asns = data?.asns?.length ? data.asns : (dataMovel?.asns ?? [])
  const rede = data?.rede || dataMovel?.rede
  const contactsAvailable = data?.contacts_available ?? dataMovel?.contacts_available
  const fetchContacts = data
    ? () => fetchOperadoraContacts(cnpjFinal)
    : () => fetchOperadoraMovelContacts(cnpjFinal)
  const ctx: OperadoraCtx = { data, dataMovel, dataStfc, dataSeac, rede, historico: q.dados?.perfil?.historico, indicadores: q.dados?.perfil?.indicadores, sobreposicao: q.dados?.perfil?.mercado_grupos, erbs: q.dados?.perfil?.erbs, multas: q.dados?.perfil?.multas, prontidao: q.dados?.perfil?.prontidao, qualidade: q.dados?.perfil?.qualidade, reclamacoes: q.dados?.perfil?.reclamacoes, consumidor: q.dados?.perfil?.consumidor, cadastro: cadastro.data ?? null, financiamento: financiamento.data ?? null, contratos: contratos.data ?? null, cnpjFinal, hasScm, hasSici, hasStfc, hasSeac, b2cPct }
  const snapshot = data?.snapshot_date ?? dataMovel?.snapshot_date ?? dataStfc?.snapshot_date ?? dataSeac?.snapshot_date ?? q.dados?.perfil?.snapshot_date

  return (
    <div className="space-y-5">
      <CabecalhoOperadora
        nome={nome} grupo={grupo} porte={porte} hasScm={hasScm} hasSmp={hasSmp} hasStfc={hasStfc} hasSeac={hasSeac}
        razaoSocial={outorga?.razao_social} cnpjFinal={cnpjFinal} municipio={outorga?.municipio} uf={outorga?.uf}
        grupoCnpjs={grupoCnpjs} grupoId={relacionadas.data?.grupo_id ?? undefined} contactsAvailable={contactsAvailable} fetchContacts={fetchContacts} asns={asns} snapshot={snapshot}
      />
      {!versaoAntiga && <FichaOperadora nome={nome} ctx={ctx} />}
      <EntityPage entidade="operadora" rotulo={`${nome} (CNPJ ${fmtCnpj(cnpjFinal)})`} dados={ctx} snapshot={snapshot ?? null} fontes={fontes} espacamento="space-y-5" />
    </div>
  )
}
