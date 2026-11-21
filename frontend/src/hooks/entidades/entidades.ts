// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { asnValido, codigoPttValido } from '../../lib/identificadores'
import { useMemo } from 'react'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AccessError,
  fetchASN, fetchASNPerfil, fetchGruposSocietarios, fetchIXP, fetchIXPPerfil, fetchMunicipioPerfil,
  fetchCadastroMercadoUf, fetchCadastroOperadora, fetchContratosMunicipio, fetchContratosOperadora, fetchFinanciamentoOperadora, fetchGrupo, fetchGrupoBloco, fetchGrupoMercado, fetchOperadoraPerfil, fetchRegiao, fetchSnapshot, fetchUfPerfil, fetchUfs,
} from '../../services/api'
import { useActiveDate } from '../useSnapshot'
import { useAuth } from '../../auth/AuthContext'
import { IMUTAVEL, chaves } from './chaves'
import type { FonteEntrada } from '../../components/entidade'
import type { LonLat } from '../../lib/geo'
import type { OperadoraDetalhe, OperadoraMovelDetalhe, SEACDetailResponse, STFCDetailResponse } from '../../types/api'

/**
 * Série histórica inteira nos perfis só com login (ou IP na allowlist, que o `/auth/me` devolve como usuário): é outra URL
 * (`include=historico_completo`), na chave do cache. Não espera o `/auth/me`: quem está logado pode pedir uma vez a versão curta antes.
 */
export function useHistoricoCompleto(): boolean {
  return !!useAuth().user
}

/**
 * Hooks por entidade. Escondem a origem do dado: se a rota de um perfil mudar, só o corpo do hook muda e as páginas ficam como estão. Todos usam a data ativa (`useActiveDate`) e esperam ela existir.
 */

export function useAsn(asn: number | string | undefined) {
  const date = useActiveDate()
  return useQuery({ queryKey: chaves.asn(asn, date), queryFn: () => fetchASN(asn!, date ?? undefined), enabled: !!asn && !!date, ...IMUTAVEL })
}

export function useIxp(code: string | undefined) {
  const date = useActiveDate()
  return useQuery({ queryKey: chaves.ixp(code, date), queryFn: () => fetchIXP(code!, date ?? undefined), enabled: !!code && !!date, ...IMUTAVEL })
}

/**
 * Perfil do AS: o documento, os caminhos, os pares nos PTTs diretos e a estabilidade BGP numa chamada (`?include=`), no lugar das 4
 * que a página fazia. Semeia o cache de `useAsn` e de `asnPaths` (o documento sem os blocos extras), para quem ainda os use não repetir a chamada.
 */
export function useAsnPerfil(asn: number | string | undefined) {
  const date = useActiveDate()
  const qc = useQueryClient()
  const completo = useHistoricoCompleto()
  return useQuery({
    queryKey: chaves.asnPerfil(asn, date, completo),
    queryFn: async () => {
      const perfil = await fetchASNPerfil(asn!, date ?? undefined, completo)
      const { paths, ixp_peers: _p, estabilidade: _e, ...doc } = perfil
      qc.setQueryData(chaves.asn(asn, date), doc)
      if (paths) qc.setQueryData(chaves.asnPaths(asn, date), paths)
      return perfil
    },
    enabled: !!asn && !!date && asnValido(asn),
    ...IMUTAVEL,
  })
}

/**
 * Perfil do PTT: o documento mais membros (com nomes), usuários estimados, potencial, assinantes, a linha do índice e os totais do
 * snapshot numa chamada (`?include=`), no lugar das 7 que a página fazia. Semeia as chaves que os mapas do PTT ainda consultam por conta
 * própria (`ixp-assinantes`, `ixp-est-users`, `ixp-potential`) e a de `useIxp`. Os pares v6 e v4 seguem em rotas próprias (listas longas).
 */
export function useIxpPerfil(code: string | undefined) {
  const date = useActiveDate()
  const qc = useQueryClient()
  const completo = useHistoricoCompleto()
  return useQuery({
    queryKey: chaves.ixpPerfil(code, date, completo),
    queryFn: async () => {
      const perfil = await fetchIXPPerfil(code!, date ?? undefined, completo)
      const { membros: _m, usuarios_estimados, potencial, assinantes, indice: _i, totais: _t, ...doc } = perfil
      qc.setQueryData(chaves.ixp(code, date), doc)
      if (usuarios_estimados) qc.setQueryData(['ixp-est-users', code, date], usuarios_estimados)
      if (potencial) qc.setQueryData(['ixp-potential', code, date], potencial)
      if (assinantes) qc.setQueryData(['ixp-assinantes', code, date], assinantes)
      return perfil
    },
    enabled: !!code && !!date && codigoPttValido(code),
    ...IMUTAVEL,
  })
}

/**
 * Operadora: uma chamada ao perfil `/operadoras/{cnpj}` traz SCM/SICI, SMP/SICI móvel, STFC e SeAC, com a rede uma vez
 * no topo. Devolve no formato que os blocos já usam (`data`, `dataMovel`, `dataStfc`, `dataSeac` com o envelope de volta e a `rede`
 * reposta em quem a tinha). `perfil === null` = CNPJ sem informação em nenhum serviço. Sem retentativa.
 */
export function useOperadoraPerfil(cnpj: string | undefined) {
  const date = useActiveDate()
  const completo = useHistoricoCompleto()
  const q = useQuery({
    queryKey: chaves.operadoraPerfil(cnpj, date, completo),
    queryFn: async () => (await fetchOperadoraPerfil(cnpj!, date ?? undefined, completo)) ?? null,
    enabled: !!cnpj && !!date,
    ...IMUTAVEL,
    retry: false,
  })
  const perfil = q.data
  const dados = useMemo(() => {
    if (!perfil) return undefined
    const env = { snapshot_date: perfil.snapshot_date, cnpj: perfil.cnpj }
    return {
      perfil,
      data: perfil.scm ? ({ ...env, ...perfil.scm, rede: perfil.rede ?? null } as OperadoraDetalhe) : undefined,
      dataMovel: perfil.smp ? ({ ...env, ...perfil.smp, rede: perfil.rede ?? null } as OperadoraMovelDetalhe) : undefined,
      dataStfc: perfil.stfc ? ({ ...env, ...perfil.stfc } as STFCDetailResponse) : undefined,
      dataSeac: perfil.seac ? ({ ...env, ...perfil.seac } as SEACDetailResponse) : undefined,
    }
  }, [perfil])
  return { ...q, dados }
}

/**
 * Município: uma chamada ao perfil `/municipios/{ibge}` traz o SICI fixo (com % de fibra), o móvel, o centróide e os PTTs
 * mais próximos (a distância vem pronta do servidor). Devolve no formato que os blocos já usam (`fixo`/`movel` com o envelope
 * de volta, `centroide` como `LonLat`, `proximos` com `lonlat`/`km`). `perfil === null` = município sem acesso declarado.
 */
export function useMunicipioPerfil(ibge: string | undefined) {
  const date = useActiveDate()
  const q = useQuery({
    queryKey: chaves.municipioPerfil(ibge, date),
    queryFn: async () => (await fetchMunicipioPerfil(ibge!, date ?? undefined)) ?? null,
    enabled: !!ibge && !!date,
    ...IMUTAVEL,
    retry: false,
  })
  const perfil = q.data
  const dados = useMemo(() => {
    if (!perfil) return undefined
    const envelope = { snapshot_date: perfil.snapshot_date, ibge: perfil.ibge, nome: perfil.nome, uf: perfil.uf }
    return {
      perfil,
      fixo: perfil.fixo ? { ...envelope, ...perfil.fixo } : undefined,
      movel: perfil.movel ? { ...envelope, ...perfil.movel } : undefined,
      centroide: (perfil.centroide ?? undefined) as LonLat | undefined,
      indicadores: perfil.indicadores ?? undefined,
      proximos: (perfil.ptts_proximos ?? []).map((p) => ({ codigo: p.codigo, nome: p.nome, lonlat: [p.lon, p.lat] as LonLat, km: p.km })),
    }
  }, [perfil])
  return { ...q, dados }
}

/** O nginx do frontend deixa 10 requisições por segundo por IP (rajada de 20) e responde 429 acima disso; as chamadas do raio saem espaçadas abaixo disso. */
export const INTERVALO_RAIO_MS = 110
let proximaVaga = 0
/** Próxima vaga de chamada do raio: espera o intervalo desde a vaga anterior (compartilhada por todos os perfis pedidos em rajada). */
function vagaDoRaio(): Promise<void> {
  const agora = Date.now()
  const quando = Math.max(agora, proximaVaga)
  proximaVaga = quando + INTERVALO_RAIO_MS
  return quando > agora ? new Promise((r) => setTimeout(r, quando - agora)) : Promise.resolve()
}

/**
 * Perfis de vários municípios (município com raio): cada um é uma chamada a `/municipios/{ibge}` com a MESMA chave de `useMunicipioPerfil`,
 * então o que a página já buscou é reaproveitado. `ibges` vazio não busca nada; a ordem do resultado é a da entrada. As chamadas saem espaçadas
 * (`INTERVALO_RAIO_MS`) para não bater no limite de taxa do nginx (medido no ambiente de teste: 50 de uma vez dão 429 em mais da metade); um 429 mesmo assim é tentado de novo.
 * Município que o usuário já tirou do raio (consulta cancelada) não chega a ser buscado.
 */
export function usePerfisMunicipios(ibges: string[]) {
  const date = useActiveDate()
  const qs = useQueries({
    queries: ibges.map((ibge) => ({
      queryKey: chaves.municipioPerfil(ibge, date),
      queryFn: async ({ signal }: { signal: AbortSignal }) => {
        await vagaDoRaio()
        if (signal.aborted) throw new Error('cancelado')
        return (await fetchMunicipioPerfil(ibge, date ?? undefined)) ?? null
      },
      enabled: !!date, ...IMUTAVEL,
      retry: (n: number, e: Error) => n < 3 && ((e instanceof AccessError && e.kind === 'taxa') || /HTTP 429/.test(e.message)),
      retryDelay: (n: number) => 1000 * (n + 1),
    })),
  })
  const prontos = qs.filter((q) => !q.isLoading).length
  return { perfis: qs.map((q) => q.data ?? null), prontos, total: ibges.length, carregando: prontos < ibges.length }
}

/** Cadastro da operadora: a raiz do CNPJ sem cadastro de telecom volta como erro 404 (204 na rede) e o bloco simplesmente não aparece. */
export function useCadastroOperadora(cnpj: string | undefined) {
  const date = useActiveDate()
  const raiz = (cnpj ?? '').replace(/\D/g, '').slice(0, 8)
  return useQuery({
    queryKey: ['cadastro-operadora', raiz, date] as const,
    queryFn: () => fetchCadastroOperadora(raiz, date ?? undefined),
    enabled: raiz.length === 8 && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** Crédito público e sanções da operadora: sem registro nas duas fontes é 404 (204 na rede) e os blocos não aparecem. */
export function useFinanciamentoOperadora(cnpj: string | undefined) {
  const date = useActiveDate()
  const raiz = (cnpj ?? '').replace(/\D/g, '').slice(0, 8)
  return useQuery({
    queryKey: ['financiamento-operadora', raiz, date] as const,
    queryFn: () => fetchFinanciamentoOperadora(raiz, date ?? undefined),
    enabled: raiz.length === 8 && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** Contratos públicos da operadora: raiz ainda sem leitura do rodízio é 404 (204 na rede) e o bloco não aparece. */
export function useContratosOperadora(cnpj: string | undefined) {
  const date = useActiveDate()
  const raiz = (cnpj ?? '').replace(/\D/g, '').slice(0, 8)
  return useQuery({
    queryKey: ['contratos-operadora', raiz, date] as const,
    queryFn: () => fetchContratosOperadora(raiz, date ?? undefined),
    enabled: raiz.length === 8 && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** Contratos públicos com órgão sediado no município: sem contratação nas leituras é 404 (204 na rede) e o bloco não aparece. */
export function useContratosMunicipio(ibge: string | undefined) {
  const date = useActiveDate()
  return useQuery({
    queryKey: ['contratos-municipio', ibge, date] as const,
    queryFn: () => fetchContratosMunicipio(ibge!, date ?? undefined),
    enabled: !!ibge && /^\d{7}$/.test(ibge) && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** Empresas de telecom da UF. */
export function useCadastroMercadoUf(uf: string | undefined) {
  const date = useActiveDate()
  const sigla = uf?.toUpperCase()
  return useQuery({
    queryKey: ['cadastro-mercado-uf', sigla, date] as const,
    queryFn: () => fetchCadastroMercadoUf(sigla!, date ?? undefined),
    enabled: !!sigla && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** ASNs do conjunto de municípios: uma chamada a `/regiao` com os códigos (o município da página e os do raio). `ibges` vazio não busca. */
export function useRegiao(ibges: string[]) {
  const date = useActiveDate()
  const chave = ibges.join(',')
  return useQuery({
    queryKey: ['regiao', chave, date] as const,
    queryFn: () => fetchRegiao(ibges, date ?? undefined),
    enabled: ibges.length > 0 && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** UF: o perfil `/ufs/{uf}` traz totais, PTTs, municípios com a distância ao PTT mais próximo e as maiores operadoras numa chamada. */
export function useUfPerfil(uf: string | undefined) {
  const date = useActiveDate()
  const sigla = uf?.toUpperCase()
  const completo = useHistoricoCompleto()
  return useQuery({
    queryKey: chaves.uf(sigla, date, completo),
    queryFn: () => fetchUfPerfil(sigla!, date ?? undefined, completo),
    enabled: !!sigla && sigla.length === 2 && !!date,
    ...IMUTAVEL,
    retry: false,
  })
}

/** Resumo das 27 UFs (acessos, fibra, usuários estimados, PTTs); alimenta `/estados`. */
export function useUfs() {
  const date = useActiveDate()
  return useQuery({ queryKey: chaves.ufs(date), queryFn: () => fetchUfs(date ?? undefined), enabled: !!date, ...IMUTAVEL, retry: false })
}

/** Grupo econômico: sai da lista de grupos societários (mesma chave da página de Grupos, sem chamada extra). */
export function useGrupo(grupoId: string | undefined) {
  const date = useActiveDate()
  const q = useQuery({ queryKey: chaves.gruposSocietarios(date), queryFn: () => fetchGruposSocietarios(date ?? undefined), enabled: !!date, staleTime: 5 * 60 * 1000 })
  const grupo = useMemo(() => q.data?.grupos?.find((g) => g.grupo_id === grupoId), [q.data, grupoId])
  return { ...q, data: grupo, listaCarregada: !!q.data }
}

/** `sources[]` do manifesto do snapshot ativo — alimenta o rodapé de proveniência. `undefined` até chegar (ou se o manifesto não tem). */
export function useFontes(): { fontes: FonteEntrada[] | undefined; snapshot: string | null } {
  const date = useActiveDate()
  const q = useQuery({ queryKey: chaves.snapshot(date), queryFn: () => fetchSnapshot(date!), enabled: !!date, ...IMUTAVEL, retry: false })
  const fontes = (q.data?.manifest as { sources?: FonteEntrada[] | null } | null | undefined)?.sources ?? undefined
  return { fontes, snapshot: date }
}

/** O grupo no mercado fixo: só é buscado quando a aba Mercado abre. */
export function useGrupoMercado(grupoId: string | undefined) {
  const date = useActiveDate()
  return useQuery({ queryKey: ['grupo-mercado', grupoId, date] as const, queryFn: () => fetchGrupoMercado(grupoId!, date ?? undefined), enabled: !!grupoId && !!date, ...IMUTAVEL, retry: false })
}

/** Regulatório e técnico do grupo: cada aba busca o seu bloco quando abre. */
export function useGrupoBloco<T>(grupoId: string | undefined, bloco: 'regulatorio' | 'tecnico' | 'relacoes') {
  const date = useActiveDate()
  return useQuery({ queryKey: ['grupo-bloco', bloco, grupoId, date] as const, queryFn: () => fetchGrupoBloco<T>(grupoId!, bloco, date ?? undefined), enabled: !!grupoId && !!date, ...IMUTAVEL, retry: false })
}

/** Grupo societário consolidado: composição, mercado, rede e somas de crédito, sanções e contratos das empresas do grupo. */
export function useGrupoDetalhe(grupoId: string | undefined) {
  const date = useActiveDate()
  return useQuery({ queryKey: ['grupo', grupoId, date] as const, queryFn: () => fetchGrupo(grupoId!, date ?? undefined), enabled: !!grupoId && !!date, ...IMUTAVEL, retry: false })
}
