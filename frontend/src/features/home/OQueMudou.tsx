// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { ComoLer } from '../../components/ui/ComoLer'
import { LinhaProveniencia } from '../../components/ui/Kpi'
import { formatarData } from '../../lib/datas'
import { n0, palavra } from '../../lib/sintese'
import type { DestaquesHome } from '../../services/api'
import { useDestaquesHome } from './Destaques'

type PorTipo = NonNullable<DestaquesHome['o_que_mudou']['por_tipo']>

/** As contagens da janela, em pares (entrou e saiu), com o que cada número conta. A ordem e o texto são fixos; nenhum tipo recebe adjetivo. */
export const LINHAS_O_QUE_MUDOU: Array<{ id: string; tipo: string; um: string; varios: string }> = [
  { id: 'asn-novo', tipo: 'asn_novo', um: 'AS novo na tabela de roteamento', varios: 'ASes novos na tabela de roteamento' },
  { id: 'asn-sumido', tipo: 'asn_sumido', um: 'AS deixou de aparecer na tabela', varios: 'ASes deixaram de aparecer na tabela' },
  { id: 'ixp-entrada', tipo: 'ixp_entrada', um: 'entrada em PTT (par AS e PTT)', varios: 'entradas em PTT (pares AS e PTT)' },
  { id: 'ixp-saida', tipo: 'ixp_saida', um: 'saída de PTT (par AS e PTT)', varios: 'saídas de PTT (pares AS e PTT)' },
  { id: 'outorga-nova', tipo: 'outorga_nova', um: 'outorga nova no cadastro da Anatel', varios: 'outorgas novas no cadastro da Anatel' },
  { id: 'outorga-baixa', tipo: 'outorga_baixa', um: 'outorga deixou de constar no cadastro', varios: 'outorgas deixaram de constar no cadastro' },
  { id: 'rpki-novo', tipo: 'rpki_invalido_novo', um: 'AS passou a ter prefixo com RPKI inválido', varios: 'ASes passaram a ter prefixo com RPKI inválido' },
  { id: 'rpki-resolvido', tipo: 'rpki_invalido_resolvido', um: 'AS deixou de ter prefixo com RPKI inválido', varios: 'ASes deixaram de ter prefixo com RPKI inválido' },
  { id: 'roa-ganho', tipo: 'roa_ganho', um: 'AS passou a ter ROA', varios: 'ASes passaram a ter ROA' },
  { id: 'roa-perdido', tipo: 'roa_perdido', um: 'AS deixou de ter ROA', varios: 'ASes deixaram de ter ROA' },
]

/** Linhas com contagem calculada; tipo ausente da resposta (snapshot sem o campo) fica de fora, nunca vira zero. */
export function linhasDaJanela(porTipo: PorTipo | undefined) {
  if (!porTipo) return []
  return LINHAS_O_QUE_MUDOU.filter((l) => porTipo[l.tipo]).map((l) => {
    const c = porTipo[l.tipo]
    return { ...l, confirmados: c.confirmado, pendentes: c.pendente }
  })
}

/**
 * "O que mudou" na janela dos snapshots atuais (PT-22 / HOME 5.4): contagens por tipo de evento (`/brasil/destaques`, aberta, uma chamada),
 * cada uma levando a `/mudancas` filtrada pelo tipo. Cada evento é uma diferença observada entre snapshots, sem causa; só conta como
 * confirmado depois de mantido nos snapshots seguintes, e os ainda em confirmação aparecem à parte.
 */
export function OQueMudou() {
  const q = useDestaquesHome()
  const m = q.data?.o_que_mudou
  const linhas = linhasDaJanela(m?.por_tipo)
  const total = m?.total
  return (
    <section aria-labelledby="o-que-mudou-titulo" className="text-sm text-gray-700 bg-white border border-gray-200 rounded-lg px-4 py-3 space-y-2" data-testid="o-que-mudou">
      <h2 id="o-que-mudou-titulo" className="text-titulo-3 text-gray-900">O que mudou</h2>
      {m && <p>Diferenças observadas entre os snapshots de {formatarData(m.de)} e {m.ate ? formatarData(m.ate) : 'o atual'} (a janela aberta, de 2 snapshots).</p>}
      {linhas.length > 0 && (
        <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2" data-testid="o-que-mudou-contagens">
          {linhas.map((l) => (
            <div key={l.id} className="flex items-baseline gap-2">
              <dt className="order-2">
                <Link to={`/mudancas?tipo=${l.tipo}`} className="text-primario-700 hover:underline">{palavra(l.confirmados, l.um, l.varios)}</Link>
                {l.pendentes > 0 && <span className="text-xs text-gray-500"> (mais {n0(l.pendentes)} em confirmação)</span>}
              </dt>
              <dd className="order-1 min-w-10 text-right font-medium tabular-nums text-gray-900">{n0(l.confirmados)}</dd>
            </div>
          ))}
        </dl>
      )}
      {linhas.length === 0 && (
        <p>
          {total != null && total > 0
            ? <>{n0(total)} {palavra(total, 'AS brasileiro novo confirmado', 'ASes brasileiros novos confirmados')} na tabela de roteamento desde {formatarData(m!.de)}{m!.mais_recente ? <>, o mais recente em {formatarData(m!.mais_recente)}</> : null}.</>
            : total === 0 ? `Nenhum AS brasileiro novo confirmado desde ${formatarData(m!.de)}.` : q.isError ? 'Não foi possível carregar agora.' : q.isLoading ? 'Carregando…' : ''}
        </p>
      )}
      {Object.entries(m?.datas_atipicas ?? {}).map(([d, a]) => (
        <p key={d} className="text-xs text-gray-600" data-testid="o-que-mudou-atipica">Data atípica, {formatarData(d)}: os eventos de {a.tipos.map((t) => t.replace(/_/g, ' ')).join(', ')} dessa data têm uma ressalva ({a.motivo}).</p>
      ))}
      {m && <LinhaProveniencia selo="fato" fonte="diferença entre snapshots, sem causa" dataRef={m.ate ?? q.data?.snapshot_date} className="text-xs text-gray-600" />}
      <ComoLer>
        <p>Cada contagem é uma diferença observada entre snapshots consecutivos, sem causa nem intenção atribuída. Um evento só conta como confirmado depois de mantido nos snapshots seguintes (entradas e saídas do cadastro de PTT, ROA e outorgas contam no snapshot em que aparecem); por isso o mais recente pode ser anterior à data do snapshot.</p>
        <p>A janela é a dos 2 snapshots atuais; o histórico completo exige login. Entradas e saídas de PTT contam pares AS e PTT, não ASes distintos. RPKI inválido é o estado de origem da rota na validação de origem (RFC 6811, Proposed Standard), observado em cada snapshot.</p>
      </ComoLer>
      <p><Link to="/mudancas" className="text-primario-700 hover:underline">Ver tudo que mudou →</Link></p>
    </section>
  )
}
