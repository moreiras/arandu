// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { cobre } from '../../../lib/prefixo'
import type { BlocoProps } from '../../entidade/registry'
import type { PrefixoCtx } from '../contexto'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

const ESTADO: Record<string, { texto: string; cor: string }> = {
  valid: { texto: 'válido', cor: 'bg-ok-100 text-ok-800' },
  invalid: { texto: 'inválido', cor: 'bg-perigo-100 text-perigo-800' },
  not_found: { texto: 'sem ROA', cor: 'bg-gray-100 text-gray-600' },
}

/** Validação da origem contra os ROAs (RPKI): o estado calculado para este prefixo, os ROAs que o cobrem e as ASPAs do AS de origem. */
export function RpkiBloco({ dados }: BlocoProps<PrefixoCtx>) {
  const { prefix, asn, carregandoAsn } = dados
  const { ordenados: roas, props } = useOrdenacao((asn?.roa_list ?? []).filter((r) => cobre(r.prefix, prefix)), {
    roa: (r) => r.prefix,
    maxlen: { valor: (r) => r.maxLength, primeiro: 'asc' },
    ta: (r) => r.ta,
  })
  if (!asn) return <p className="text-sm text-gray-500">{carregandoAsn ? 'Carregando o AS de origem…' : 'Documento do AS de origem indisponível neste snapshot.'}</p>
  const estado = asn.rpki_validation?.[prefix]
  const e = estado ? ESTADO[estado] : undefined
  return (
    <div className="space-y-3 text-sm">
      <div>
        <span className="text-xs text-gray-500 mr-2">Validação da origem</span>
        {e ? <span className={`px-2 py-0.5 rounded text-xs font-medium ${e.cor}`}>{e.texto}</span> : <span className="text-gray-500">não avaliada para este prefixo</span>}
      </div>
      {roas.length > 0 ? (
        <table className="w-full text-xs">
          <thead><tr className="text-left text-gray-400 border-b border-gray-100"><ThOrdenavel {...props('roa')} className="py-1">ROA</ThOrdenavel><th scope="col">AS autorizado</th><ThOrdenavel {...props('maxlen')}>maxLength</ThOrdenavel><ThOrdenavel {...props('ta')}>TA</ThOrdenavel></tr></thead>
          <tbody className="divide-y divide-gray-50">
            {roas.map((r, i) => (
              <tr key={`${r.prefix}-${i}`}><td className="py-1 font-mono">{r.prefix}</td><td>AS{asn.asn}</td><td>{r.maxLength}</td><td className="uppercase">{r.ta}</td></tr>
            ))}
          </tbody>
        </table>
      ) : <p className="text-gray-500">Nenhum ROA cobre este prefixo.</p>}
      <p className="text-xs text-gray-500">
        ASPA do AS de origem: {asn.aspa_providers == null ? 'sem registro' : `${asn.aspa_providers.length} provedor(es) declarado(s)`}.
      </p>
    </div>
  )
}
