// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Migalhas } from '../components/layout/Migalhas'
import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { EntityHeader } from '../components/entidade'
import { EntityPage } from '../features/entidade/EntityPage'
import { EstadoDados } from '../components/ui/EstadoDados'
import type { MunicipioUf, UfCtx } from '../features/uf/contexto'
import '../features/uf'
import { useCadastroMercadoUf, useFontes, useUfPerfil } from '../hooks/entidades'
import { useActiveDate } from '../hooks/useSnapshot'
import { UFS, nomeUf } from '../lib/ufs'

/**
 * Página de UF: PTTs, municípios (com a distância ao PTT mais próximo), operadoras sediadas e ASNs BR da UF.
 * Uma chamada: o perfil `/ufs/{uf}` traz totais, PTTs, municípios (com a distância ao PTT, calculada no servidor) e operadoras.
 */
export function UFPage() {
  const { uf: ufParam } = useParams<{ uf: string }>()
  const uf = (ufParam ?? '').toUpperCase()
  const valida = uf in UFS
  const date = useActiveDate()
  const { fontes } = useFontes()
  const perfilQ = useUfPerfil(valida ? uf : undefined)
  const cadastroQ = useCadastroMercadoUf(valida ? uf : undefined)
  const perfil = perfilQ.data

  const municipios = useMemo<MunicipioUf[]>(() => (perfil?.municipios ?? []).map((m) => ({
    ibge: m.ibge, nome: m.nome, acessos: m.acessos, operadores: m.operadores, hhi: m.hhi, fibraPct: m.fibra_pct,
    kmPtt: m.km_ptt, ptt: m.ptt ?? undefined,
  })), [perfil])

  if (!valida) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h1 className="text-lg font-semibold text-gray-800 mb-1">UF não encontrada</h1>
        <p className="text-sm text-gray-500">“{ufParam}” não é uma sigla de UF. Exemplo: <Link className="text-primario-600 hover:underline" to="/uf/SP">/uf/SP</Link>.</p>
      </div>
    )
  }
  if (perfilQ.isLoading) return <div className="text-sm text-gray-400">Carregando…</div>
  // Sem perfil não há painel: os totais de reserva abaixo virariam "0" na tela.
  if (perfilQ.isError) {
    return <EstadoDados variante="pagina" erro={perfilQ.error} oQue={`o perfil de ${nomeUf(uf)}`} snapshot={date}
      mensagem={`O perfil de ${nomeUf(uf)} não está publicado neste snapshot.`} aoTentarDeNovo={() => void perfilQ.refetch()} />
  }

  const ctx: UfCtx = {
    uf,
    cadastro: cadastroQ.data ?? null,
    ixps: perfil?.ixps ?? [],
    municipios,
    semCentroides: municipios.every((m) => m.kmPtt == null),
    totais: perfil?.totais ?? { municipios: 0, acessos: 0, fibra_pct: null, asns: 0, usuarios: 0, municipios_sem_ptt: 0, acessos_sem_ptt: 0, raio_sem_ptt_km: 100 },
    asns: perfil ? { quantidade: perfil.totais.asns, usuarios: perfil.totais.usuarios } : undefined,
    operadoras: perfil?.operadoras?.items ?? [],
    operadorasTotal: perfil?.operadoras?.total ?? 0,
    operadorasPresentes: perfil?.operadoras_presentes?.items ?? [],
    operadorasPresentesTotal: perfil?.operadoras_presentes?.total ?? 0,
    mesReferencia: perfil?.mes_referencia ?? undefined,
    historico: perfil?.historico,
    territorio: perfil?.territorio,
    mercadoGrupos: perfil?.mercado_grupos,
    redeTerritorio: perfil?.rede_territorio,
    cetic: perfil?.cetic,
    demandaOferta: perfil?.demanda_oferta,
    erbs: perfil?.erbs,
    fust: perfil?.fust,
    prontidao: perfil?.prontidao,
    qualidade: perfil?.qualidade,
    reclamacoes: perfil?.reclamacoes,
    transito: perfil?.transito,
    radar: perfil?.radar,
    exposicao: perfil?.exposicao,
    consumidor: perfil?.consumidor,
  }
  const snapshot = perfil?.snapshot_date ?? date ?? null
  return (
    <div className="space-y-5">
      <EntityHeader
        trilha={<Migalhas grupo="territorio" itens={[{ rotulo: 'Estados', to: '/estados' }, { rotulo: uf }]} />}
        nome={nomeUf(uf)}
        selos={[{ rotulo: uf }]}
      >
        <div className="text-sm text-gray-500 mt-0.5">
          Unidade da Federação{ctx.mesReferencia ? ` · SICI, mês de referência ${ctx.mesReferencia}` : ''}{snapshot ? ` · snapshot ${snapshot}` : ''}
        </div>
      </EntityHeader>
      <EntityPage entidade="uf" rotulo={nomeUf(uf)} dados={ctx} snapshot={snapshot} fontes={fontes} espacamento="space-y-5" />
    </div>
  )
}
