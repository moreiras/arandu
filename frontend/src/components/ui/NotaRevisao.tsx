// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SITE } from '../../lib/site'
import { NOTAS_REVISAO, type ContagemRevisada, type NotaRevisao as Nota } from '../../lib/notasRevisao'

const dataBr = (iso: string) => iso.split('-').reverse().join('/')
const num = (n: number) => n.toLocaleString('pt-BR')

function Tabela({ legenda, contagens }: { legenda: string; contagens: ContagemRevisada[] }) {
  return (
    <table className="text-xs border-collapse">
      <caption className="text-left text-gray-600 pb-1">{legenda}</caption>
      <thead>
        <tr className="text-left text-gray-600">
          <th scope="col" className="pr-4 py-0.5 font-medium">Tipo de evento</th>
          <th scope="col" className="pr-4 py-0.5 font-medium text-right">Antes</th>
          <th scope="col" className="py-0.5 font-medium text-right">Depois</th>
        </tr>
      </thead>
      <tbody>
        {contagens.map((c) => (
          <tr key={c.tipo} className="border-t border-gray-200">
            <th scope="row" className="pr-4 py-0.5 font-mono font-normal text-left">{c.tipo}</th>
            <td className="pr-4 py-0.5 text-right tabular-nums">{num(c.antes)}</td>
            <td className="py-0.5 text-right tabular-nums">{num(c.depois)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * Nota de revisão datada (D7): o que mudou num número publicado depois da publicação, a causa e a versão da regra. Recolhível
 * (`<details>`), com o rótulo "Nota de revisão" no texto do resumo (não depende de cor ou ícone) e `role="note"` com nome acessível
 * no contêiner. `aberta` abre por padrão (ex.: /mudancas); fechada, é o aviso compacto (ex.: /snapshots). Os dados vêm de `lib/notasRevisao.ts`.
 */
export function NotaRevisao({ nota = NOTAS_REVISAO[0], aberta = false }: { nota?: Nota; aberta?: boolean }) {
  const rotulo = `Nota de revisão de ${dataBr(nota.data)}: ${nota.titulo}`
  return (
    <div role="note" aria-label={rotulo} data-testid="nota-revisao" className="rounded border border-gray-300 bg-gray-50 text-sm text-gray-800">
      <details open={aberta || undefined}>
        <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold text-gray-800">
          {rotulo}
        </summary>
        <div className="space-y-3 px-3 pb-3 pt-1 leading-relaxed [&_p]:max-w-[80ch]">
          <p>{nota.o_que_mudou}</p>
          <p>Causa: {nota.causa}</p>
          <p>Versão da regra: <code>eventos_regra = {nota.regra}</code>. Revisão feita em {dataBr(nota.data)}.</p>
          <Tabela legenda={`Eventos em ${dataBr(nota.em.data)}, antes e depois da revisão`} contagens={nota.em.contagens} />
          {nota.em.nota && <p>{nota.em.nota}</p>}
          <Tabela legenda={`Soma das ${nota.total.datas} datas regeneradas (${dataBr(nota.total.de)} a ${dataBr(nota.total.ate)})`} contagens={nota.total.contagens} />
          <p>Não mudam: {nota.total.inalterados}.</p>
          <p>
            Registro completo no{' '}
            <a href={`${SITE.codigoFonte}/blob/main/CHANGELOG.md`} target="_blank" rel="noopener noreferrer" className="text-primario-700 underline">
              CHANGELOG (abre em nova aba)
            </a>.
          </p>
        </div>
      </details>
    </div>
  )
}
