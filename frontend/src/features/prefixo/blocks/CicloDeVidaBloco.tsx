// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchIpv4CicloDeVida } from '../../../services/api'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'

const ROTULOS: Record<string, string> = {
  titularidade: 'Mudou de organização (opaque-id)', recuperacao: 'Voltou ao pool (reservado)', liberacao: 'Saiu da reserva', novo: 'Passou a constar', removido: 'Deixou de constar',
  pais: 'Mudou de país', transferencia: 'Transferência declarada', em_recuperacao: 'Em recuperação (Registro.br)',
}
const data = (d: string) => new Date(d + 'T12:00:00').toLocaleDateString('pt-BR')

function resumo(t: { tipo: string; detalhe: Record<string, unknown> }) {
  const d = t.detalhe
  if (t.tipo === 'transferencia') {
    const o = d.origem as { nome?: string }, e = d.destino as { nome?: string }
    return `${o?.nome ?? '?'} → ${e?.nome ?? '?'}${d.anterior_a_coleta ? ' (já estava na primeira lista coletada)' : ''}`
  }
  if (t.tipo === 'em_recuperacao') return `janela até ${data(String(d.fim))}`
  const de = d.de as { opaque?: string | null; status?: string } | null, para = d.para as { opaque?: string | null; status?: string } | null
  return [de?.opaque && `de ${de.opaque}`, para?.opaque && `para ${para.opaque}`, de?.status && para?.status && de.status !== para.status && `${de.status} → ${para.status}`].filter(Boolean).join(' · ')
}

/** Ciclo de vida do bloco IPv4: estado atual no delegated, eventos observados, transferências declaradas e recuperação. Sem causa nem intenção. */
export function CicloDeVidaBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const q = useQuery({ queryKey: ['ipv4-ciclo', dados.prefix, dados.date], retry: false, staleTime: 10 * 60 * 1000, queryFn: () => fetchIpv4CicloDeVida(dados.prefix, dados.date ?? undefined) })
  const c = q.data
  if (!c) return null
  return (
    <div className="space-y-3">
      {c.atual.length > 0 && (
        <p className="text-sm text-gray-700">
          No delegated hoje: {c.atual.map((a) => `${a.inicio} (${a.quantidade.toLocaleString('pt-BR')} endereços) ${a.status}${a.organizacao ? `, ${a.organizacao}` : ''}`).join('; ')}
          {c.atual[0].asn != null && <> · <Link to={`/asn/${c.atual[0].asn}`} className="text-primario-600 hover:underline">AS{c.atual[0].asn}</Link></>}
        </p>
      )}
      {(c.espaco ?? []).map((e) => (
        <p key={e.inicio} className="text-sm text-gray-700">Pela tabela de origens: <strong>{e.classe === 'nao_anunciado' ? 'não anunciado' : e.classe === 'roa_sem_anuncio' ? 'ROA sem anúncio' : e.classe === 'parcial' ? `anunciado em parte (${e.anunciado_pct.toLocaleString('pt-BR')}%)` : 'em recuperação'}</strong>
          {e.tabelas_sem_anuncio ? ` há ${e.tabelas_sem_anuncio} tabela(s) de origem seguidas (desde ${data(e.sem_anuncio_desde ?? '')})` : ''}. <span className="text-gray-500">Não anunciado não é sem uso.</span></p>
      ))}
      {(c.sinais_de_terceiros ?? []).map((i) => (
        <div key={i.inicio} className="text-sm">
          <p className="text-gray-700">Hipótese de uso por terceiros ({i.inicio}), confiança <strong>{i.confianca}</strong>:</p>
          <ul className="text-xs text-gray-600 list-disc ml-5">{i.sinais.map((s) => <li key={s.id}><span className="font-medium">{s.id}</span> {s.evidencia}</li>)}</ul>
        </div>
      ))}
      <ol className="text-sm space-y-1">
        {c.linha_do_tempo.map((t, i) => (
          <li key={i} className="flex gap-3"><span className="text-gray-500 w-24 shrink-0 tabular-nums">{data(t.data)}</span><span><strong>{ROTULOS[t.tipo] ?? t.tipo}</strong> <span className="text-gray-600">{resumo(t)}</span> <span className="text-xs text-gray-400">· {t.fonte}</span></span></li>
        ))}
      </ol>
      <p className="text-xs text-gray-500">{c.aviso}</p>
    </div>
  )
}
