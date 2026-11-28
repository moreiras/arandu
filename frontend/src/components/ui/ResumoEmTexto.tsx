// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../entidade/proveniencia'
import { ComoLer } from './ComoLer'
import { ListaFontes } from './FontesEDatas'

/** Frase do resumo: o texto vai à tela; selo, fonte e data vão para o bloco recolhido de fontes. */
export interface FraseResumo {
  id: string
  texto: string
  selo: Selo
  fonte: string
  dataRef?: string | null
  /** Frases seguidas com o mesmo `paragrafo` formam um parágrafo; sem o campo, todas ficam num só. */
  paragrafo?: string
}

/**
 * Resumo em texto (PT-30): vem depois dos cartões, nunca no topo. As frases aparecem inteiras, em sequência, sem selo nem fonte em cada
 * uma. Como o resumo é gerado e de onde vêm os dados (selos, fontes e datas das frases) ficam num único bloco recolhido do próprio
 * resumo, mesmo dentro de um `GrupoFontes`: o bloco da seção fica com os cartões, e o leitor não procura as fontes do resumo noutro lugar.
 * O texto é gerado por regra fixa, sem modelo de linguagem, a partir dos mesmos números da página.
 */
export function ResumoEmTexto({ frases, regras, rotulo = 'Em resumo', snapshot, notaComoLer, aoVivo = false }: {
  frases: FraseResumo[]
  /** Versão das regras de montagem das frases (muda quando uma regra muda). */
  regras: string
  rotulo?: string
  snapshot?: string | null
  /** Frase adicional do "Como ler" específica da página. */
  notaComoLer?: string
  /** Região anunciada (`role="status"`, `aria-live="polite"`) para o resumo que muda com a interação, como o do localizador. */
  aoVivo?: boolean
}) {
  const itens = frases.map((f) => ({ selo: f.selo, fonte: f.fonte, dataRef: f.dataRef }))
  if (frases.length === 0) return null
  const paragrafos = frases.reduce<FraseResumo[][]>((acc, f, i) => {
    if (i > 0 && f.paragrafo === frases[i - 1].paragrafo) acc[acc.length - 1].push(f)
    else acc.push([f])
    return acc
  }, [])
  return (
    <section aria-label={rotulo} className="space-y-2" data-testid="resumo-em-texto" {...(aoVivo ? { role: 'status', 'aria-live': 'polite' as const } : {})}>
      <h2 className="text-sm font-semibold text-gray-800">{rotulo}</h2>
      {paragrafos.map((grupo, p) => (
        <p key={p} className="max-w-[80ch] text-sm leading-relaxed text-gray-900">
          {grupo.map((f, i) => <span key={f.id} data-testid={`frase-${f.id}`}>{i > 0 ? ' ' : ''}{f.texto}</span>)}
        </p>
      ))}
      <ComoLer titulo="Como este resumo é gerado e de onde vêm os dados">
        <p>
          As frases são montadas por regras fixas (versão <code>{regras}</code>), sem modelo de linguagem, a partir dos números desta página.
          Elas descrevem os dados e não explicam causas.{notaComoLer ? ` ${notaComoLer}` : ''}
        </p>
        <ListaFontes itens={itens} snapshot={snapshot} />
      </ComoLer>
    </section>
  )
}
