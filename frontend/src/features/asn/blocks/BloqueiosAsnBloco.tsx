// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { palavra } from '../../../lib/sintese'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

/**
 * Bloqueios e interferência medidos pelo OONI neste AS. O número é o veredito da PRÓPRIA sonda do voluntário (não o do backend do OONI) e NÃO é prova de censura.
 * Mostra a licença e a atribuição (CC BY-NC-SA 4.0), a janela, o aviso e os limites; o Web Connectivity é amostra de horas.
 */
export function BloqueiosAsnBloco({ dados }: BlocoProps<AsnCtx>) {
  const b = dados.bloqueios
  const { ordenados, props } = useOrdenacao(b?.testes, {
    teste: (t) => t.rotulo,
    n: (t) => t.n,
    anomalia: (t) => t.pct_anomalia,
  })
  if (!b) return null
  const j = b.janela
  return (
    <div className="space-y-3 text-sm" data-testid="bloqueios-asn">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="bloqueios-aviso">{b.aviso}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <caption className="sr-only">Medições do OONI por teste neste AS</caption>
          <thead>
            <tr className="text-gray-500">
              <ThOrdenavel {...props('teste')} className="py-1 pr-3 font-medium">Teste</ThOrdenavel>
              <ThOrdenavel {...props('n')} alinhar="right" className="py-1 pr-3 text-right font-medium">Medições</ThOrdenavel>
              <ThOrdenavel {...props('anomalia')} alinhar="right" className="py-1 pr-3 text-right font-medium">Anomalia declarada pela sonda</ThOrdenavel>
              <th scope="col" className="py-1 font-medium">Critério</th>
            </tr>
          </thead>
          <tbody>
            {ordenados.map((t) => (
              <tr key={t.teste} className="border-t border-gray-100 align-top">
                <td className="py-1 pr-3 font-medium">{t.rotulo}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{n(t.n)}</td>
                <td className="py-1 pr-3 text-right tabular-nums">{n(t.anomalias)} ({pct(t.pct_anomalia)})</td>
                <td className="py-1 text-gray-600">{t.criterio}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">
        Janela: {j.inicio ?? '—'} a {j.fim ?? '—'} ({n(j.dias_com_dado)} {palavra(j.dias_com_dado ?? 0, 'dia', 'dias')} com dado). Só testes com {n(b.minimo_medicoes)} ou mais medições aparecem; a ausência de um teste não quer dizer ausência de bloqueio. {b.limites}
      </p>
      <p className="text-xs text-gray-500" data-testid="bloqueios-licenca">
        {b.fonte.atribuicao ?? b.fonte.nome} Licença dos dados: <a className="text-primario-600 hover:underline" href={b.fonte.licenca_url ?? 'https://creativecommons.org/licenses/by-nc-sa/4.0/'} target="_blank" rel="noreferrer">{b.licenca}</a>.
        Coletado em {b.coletado_em ? b.coletado_em.slice(0, 10) : '—'}.
      </p>
    </div>
  )
}
