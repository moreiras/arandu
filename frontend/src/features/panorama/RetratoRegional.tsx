// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import { useRegistrarFontes } from '../../components/ui/FontesEDatas'
import { n0, pct1 } from '../../lib/sintese'
import type { BrasilIndicadores } from '../../types/api'
import { fracao, grande } from './formato'

type PorRegiao = NonNullable<BrasilIndicadores['por_regiao']>
type Linha = PorRegiao['regioes'][number]

/** As linhas da tabela: as cinco regiões, a de ASNs sem região e o total, com os percentuais calculados do que a API entregou (nada digitado à mão). */
export function linhasRegionais(r: PorRegiao | null | undefined) {
  if (!r) return []
  const calc = (l: Linha | PorRegiao['total'], nome: string, id: string) => ({
    id, nome, asns: l.asns, usuarios: l.usuarios,
    ipv6: fracao(l.usuarios_ipv6, l.usuarios), roa: fracao(l.usuarios_com_roa, l.usuarios), sessao: fracao(l.usuarios_sessao_rs, l.usuarios),
  })
  return [
    ...r.regioes.map((l) => calc(l, l.nome, l.regiao)),
    ...(r.sem_regiao.asns > 0 ? [calc(r.sem_regiao, 'ASNs sem região', 'sem_regiao')] : []),
    calc(r.total, 'Brasil', 'total'),
  ]
}

const p = (v: number | null) => (v == null ? '—' : pct1(v))

/**
 * "Por região" no Resumo do Panorama técnico (PT-22 / PANORAMA TÉCNICO 5.2): o agregado nacional repartido pela macro-região da sede da organização dona do AS
 * (`/brasil/indicadores`, `por_regiao`), em tabela de texto. As linhas fecham o total. A região é a da sede, não a dos usuários: a nota diz isso ao lado da tabela,
 * porque o Sudeste concentra sedes de operadoras nacionais.
 */
export function RetratoRegional({ por, dataRef }: { por: PorRegiao | null | undefined; dataRef?: string | null }) {
  useRegistrarFontes(por ? [
    { selo: 'estimado', fonte: 'APNIC Labs (usuários por ASN)', dataRef },
    { selo: 'inferido', fonte: 'cadastro de organizações (região da sede do AS)', dataRef },
  ] : [])
  const linhas = linhasRegionais(por)
  if (!por || linhas.length === 0) return null
  return (
    <section className="space-y-2" aria-labelledby="retrato-regional-titulo" data-testid="retrato-regional">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 id="retrato-regional-titulo" className="text-titulo-3 text-gray-800">Por região (sede da organização do AS)</h2>
        <p className="flex flex-wrap gap-x-3 text-sm">
          <Link to="/estados" className="text-primario-700 hover:underline">Por estado →</Link>
          <Link to="?aba=ipv6" className="text-primario-700 hover:underline">IPv6 por acessos fixos →</Link>
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm tabular-nums">
          <caption className="sr-only">ASNs brasileiros, usuários estimados e percentuais de usuários com IPv6, em ASNs com ROA e em ASNs com sessão em route server do IX.br, por região da sede</caption>
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-600">
              <th scope="col" className="py-1 pr-3 font-medium">Região</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">ASNs</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Usuários estimados</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Com IPv6</th>
              <th scope="col" className="py-1 px-2 text-right font-medium">Em ASNs com ROA</th>
              <th scope="col" className="py-1 pl-2 text-right font-medium">Em ASNs com sessão no route server</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.id} className={`border-b border-gray-100 ${l.id === 'total' ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                <th scope="row" className="py-1 pr-3 text-left font-normal">{l.id === 'total' ? <strong className="font-medium">{l.nome}</strong> : l.nome}</th>
                <td className="py-1 px-2 text-right">{n0(l.asns)}</td>
                <td className="py-1 px-2 text-right">{grande(l.usuarios) ?? '—'}</td>
                <td className="py-1 px-2 text-right">{p(l.ipv6)}</td>
                <td className="py-1 px-2 text-right">{p(l.roa)}</td>
                <td className="py-1 pl-2 text-right">{p(l.sessao)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-600" data-testid="retrato-regional-nota">
        Região é a da sede da empresa dona do AS, não a dos usuários: uma operadora nacional sediada em uma região conta todos os seus usuários nela.
        Sessão em route server mede só o IX.br; acordos bilaterais e interligação privada não aparecem. Usuários são estimativa do APNIC Labs; os percentuais são parte dos usuários da linha.
        {por.sem_regiao.asns > 0 && <> {n0(por.sem_regiao.asns)} {por.sem_regiao.asns === 1 ? 'ASN sem região' : 'ASNs sem região'} no cadastro.</>}
      </p>
    </section>
  )
}
