// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'
import type { RpkiObservado } from '../../../services/api'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'
import { palavra } from '../../../lib/sintese'

const ESTADO: Record<RpkiObservado['estado'], { texto: string; cor: string }> = {
  valid: { texto: 'válido', cor: 'bg-ok-100 text-ok-800' },
  invalid: { texto: 'inválido', cor: 'bg-perigo-100 text-perigo-800' },
  not_found: { texto: 'sem ROA', cor: 'bg-gray-100 text-gray-600' },
  nao_avaliado: { texto: 'não avaliado', cor: 'bg-gray-100 text-gray-600' },
}

/** Frase de diagnóstico: por que o par prefixo × origem observada tem este estado. */
function diagnostico(r: RpkiObservado, prefix: string): string {
  const autorizados = [...new Set(r.roas_que_cobrem.map((x) => `AS${x.asn}`))].join(', ')
  switch (r.estado) {
    case 'valid': return `Válido: um ROA de AS${r.asn} cobre o prefixo com maxLength suficiente para /${prefix.split('/')[1]}.`
    case 'invalid': return r.motivo === 'maxlength_excedido'
      ? `Inválido: há ROA de AS${r.asn}, mas o maxLength é menor que /${prefix.split('/')[1]}.`
      : `Inválido: os ROAs que cobrem o prefixo autorizam ${autorizados}; a origem observada é AS${r.asn}.`
    case 'not_found': return 'Sem ROA: nenhum ROA publicado cobre este prefixo.'
    default: return 'Não avaliado: o prefixo não é anunciado como está neste snapshot, então não há par prefixo e origem para validar.'
  }
}

const autoriza = (v: boolean | null) => (v == null ? '—' : v ? 'sim' : 'não')

/** Validação de origem (RFC 6811) do par anunciado, calculada no servidor: estado, motivo, os ROAs de qualquer AS que cobrem o
 *  prefixo (PFX-E4) e a ASPA do AS de origem observado. Sem anúncio, nada é validado (PFX-E2). */
export function RpkiBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { prefix, info, asn } = dados
  const r = info.rpki_observado
  const { ordenados: roas, props } = useOrdenacao(r?.roas_que_cobrem ?? [], {
    roa: (x) => x.prefix,
    as: { valor: (x) => x.asn, primeiro: 'asc' },
    maxlen: { valor: (x) => x.maxLength, primeiro: 'asc' },
    ta: (x) => x.ta,
  })
  if (!r) return <p className="text-sm text-gray-500">Sem a lista de ROAs (VRPs) neste snapshot: a validação não foi feita.</p>
  const e = ESTADO[r.estado]
  return (
    <div className="space-y-3 text-sm">
      <div>
        <span className="text-xs text-gray-500 mr-2">Validação da origem observada{r.asn != null ? ` (AS${r.asn})` : ''}</span>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${e.cor}`} data-testid="rpki-estado">{e.texto}</span>
      </div>
      <p className="text-gray-700" data-testid="rpki-diagnostico">{diagnostico(r, prefix)}</p>
      {roas.length > 0 ? (
        <table className="w-full text-xs">
          <caption className="sr-only">ROAs que cobrem {prefix}</caption>
          <thead><tr className="text-left text-gray-400 border-b border-gray-100">
            <ThOrdenavel {...props('roa')} className="py-1">ROA</ThOrdenavel><ThOrdenavel {...props('as')}>AS autorizado</ThOrdenavel>
            <ThOrdenavel {...props('maxlen')}>maxLength</ThOrdenavel><ThOrdenavel {...props('ta')}>TA</ThOrdenavel><th scope="col">Autoriza a origem observada?</th>
          </tr></thead>
          <tbody className="divide-y divide-gray-50">
            {roas.map((x, i) => (
              <tr key={`${x.prefix}-${x.asn}-${i}`}><td className="py-1 font-mono">{x.prefix}</td><td className="font-mono">AS{x.asn}</td><td>{x.maxLength}</td><td className="uppercase">{x.ta}</td><td>{autoriza(x.autoriza_origem)}</td></tr>
            ))}
          </tbody>
        </table>
      ) : <p className="text-gray-500">Nenhum ROA, de nenhum AS, cobre este prefixo.</p>}
      {r.asn != null && asn && (
        <p className="text-xs text-gray-500">
          ASPA do AS de origem observado: {asn.aspa_providers == null ? 'sem objeto ASPA publicado' : `${asn.aspa_providers.length} ${palavra(asn.aspa_providers.length, 'provedor declarado', 'provedores declarados')}`}.
        </p>
      )}
      <p className="max-w-3xl text-xs text-gray-500">
        A validação de origem (RFC 6811, Proposed Standard) compara a origem do anúncio com os ROAs publicados (RFC 9582, Proposed
        Standard). Inválido não prova ataque nem erro deliberado; um ROA com maxLength maior que o prefixo também autoriza prefixos mais específicos.
      </p>
    </div>
  )
}
