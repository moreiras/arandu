// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { SCMRecord, SMPRecord, STFCRecord, SEACRecord } from '../../types/api'

/**
 * Serviços de uma operadora na Anatel, lidos **só** do cadastro de outorgas. Fonte única para o cabeçalho, a ficha, o relatório e
 * a regra de exibição dos blocos: ter ASN ou declarar acessos não é outorga, e credenciamento de rede virtual também não é.
 *
 * - `outorga`: há registro de outorga do serviço (no SMP, registro que não é o sintético "sem outorga SMP própria").
 * - `credenciada`: só no SMP; a empresa é credenciada de rede virtual de uma prestadora de origem, sem outorga SMP própria
 *   (RGST, Resolução Anatel nº 777/2025; os acessos dela são declarados pela prestadora de origem).
 */
export type Sigla = 'SCM' | 'SMP' | 'STFC' | 'SeAC'
export interface ServicoOperadora {
  sigla: Sigla
  tipo: 'outorga' | 'credenciada'
  /** Data de outorga mais antiga (DD/MM/AAAA, como no cadastro); null se nenhum registro a traz. */
  desde: string | null
  /** Registros de outorga do serviço (no SMP, sem contar o registro sintético de credenciamento). */
  registros: number
  /** Prestadora de origem, quando a empresa é credenciada de rede virtual (no SMP). */
  origem?: { cnpj?: string; nome?: string }
  /** Número de credenciadas, quando a empresa é prestadora de origem (host) de rede virtual. */
  credencia?: number
}

/** Marca que o coletor (`sources/anatel_smp/collect.py`) põe no registro sintético de credenciada sem outorga SMP própria. */
const SEM_OUTORGA_PROPRIA = /sem outorga smp pr[óo]pria/i

/** Registro SMP que é outorga de verdade (e não o registro sintético que só materializa o credenciamento). */
export function ehOutorgaSmp(r: SMPRecord): boolean {
  return !SEM_OUTORGA_PROPRIA.test(r.situacao ?? '')
}

const dataBr = (d: string) => { const [dd, mm, aa] = d.split('/'); return `${aa}${mm}${dd}` }
function maisAntiga(recs: Array<{ data_outorga?: string }>): string | null {
  const ds = recs.map((r) => r.data_outorga ?? '').filter((d) => /^\d{2}\/\d{2}\/\d{4}$/.test(d))
  return ds.length ? ds.sort((a, b) => dataBr(a).localeCompare(dataBr(b)))[0] : null
}

export interface FontesServicos {
  data?: { outorgas_scm?: SCMRecord[] } | null
  dataMovel?: { outorgas_smp?: SMPRecord[] } | null
  dataStfc?: { outorgas?: STFCRecord[] } | null
  dataSeac?: { outorgas?: SEACRecord[] } | null
}

export function servicosDaOperadora(f: FontesServicos): ServicoOperadora[] {
  const out: ServicoOperadora[] = []
  const simples = (sigla: Sigla, recs: Array<{ data_outorga?: string }> | undefined) => {
    if (recs?.length) out.push({ sigla, tipo: 'outorga', desde: maisAntiga(recs), registros: recs.length })
  }
  simples('SCM', f.data?.outorgas_scm)
  const smp = f.dataMovel?.outorgas_smp ?? []
  const proprias = smp.filter(ehOutorgaSmp)
  const cred = smp.find((r) => r.rede_virtual?.papel === 'credenciada')?.rede_virtual
  const host = smp.find((r) => r.rede_virtual?.papel === 'host')?.rede_virtual
  if (proprias.length) {
    out.push({ sigla: 'SMP', tipo: 'outorga', desde: maisAntiga(proprias), registros: proprias.length,
      ...(cred ? { origem: { cnpj: cred.prestadora_origem_cnpj, nome: cred.prestadora_origem_nome } } : {}),
      ...(host?.credenciadas_count ? { credencia: host.credenciadas_count } : {}) })
  } else if (cred) {
    out.push({ sigla: 'SMP', tipo: 'credenciada', desde: null, registros: 0, origem: { cnpj: cred.prestadora_origem_cnpj, nome: cred.prestadora_origem_nome } })
  }
  simples('STFC', f.dataStfc?.outorgas)
  simples('SeAC', f.dataSeac?.outorgas)
  return out
}

/** Siglas dos serviços com outorga (sem o credenciamento de rede virtual). */
export const siglasComOutorga = (s: ServicoOperadora[]): Sigla[] => s.filter((x) => x.tipo === 'outorga').map((x) => x.sigla)
export const temOutorga = (s: ServicoOperadora[], sigla: Sigla) => s.some((x) => x.sigla === sigla && x.tipo === 'outorga')
export const credenciamentoSmp = (s: ServicoOperadora[]) => s.find((x) => x.sigla === 'SMP' && x.tipo === 'credenciada')
