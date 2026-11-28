// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../entidade/proveniencia'
import { Link } from '../layout/LinkDatado'
import { ComoLer } from './ComoLer'
import { FontesEDatas, useEmGrupoFontes, useRegistrarFontes } from './FontesEDatas'

/** Frase do resumo: o texto vai à tela; selo, fonte e data vão para o bloco recolhido de fontes. */
export interface FraseResumo {
  id: string
  texto: string
  selo: Selo
  fonte: string
  dataRef?: string | null
  /** Link depois do texto da frase (por exemplo, o ranking completo que a frase cita em parte). */
  link?: { to: string; rotulo: string }
}

/**
 * Resumo em texto (PT-30): vem depois dos cartões, nunca no topo. As frases aparecem inteiras, em sequência, sem selo nem fonte em cada
 * uma; selos, fontes e datas ficam num bloco recolhido (o da seção, se houver um `GrupoFontes` acima; senão, o do próprio resumo).
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
  const emGrupo = useEmGrupoFontes()
  const itens = frases.map((f) => ({ selo: f.selo, fonte: f.fonte, dataRef: f.dataRef }))
  useRegistrarFontes(itens)
  if (frases.length === 0) return null
  return (
    <section aria-label={rotulo} className="space-y-2" data-testid="resumo-em-texto" {...(aoVivo ? { role: 'status', 'aria-live': 'polite' as const } : {})}>
      <h2 className="text-sm font-semibold text-gray-800">{rotulo}</h2>
      <p className="max-w-[80ch] text-sm leading-relaxed text-gray-900">
        {frases.map((f, i) => (
          <span key={f.id} data-testid={`frase-${f.id}`}>
            {i > 0 ? ' ' : ''}{f.texto}
            {f.link && <>{' '}<Link to={f.link.to} className="text-primario-600 hover:underline">{f.link.rotulo}</Link>.</>}
          </span>
        ))}
      </p>
      <div className="space-y-1">
        <ComoLer titulo="Como este resumo é gerado">
          <p>
            As frases são montadas por regras fixas (versão <code>{regras}</code>), sem modelo de linguagem, a partir dos números desta página.
            Elas descrevem os dados e não explicam causas.{notaComoLer ? ` ${notaComoLer}` : ''}
          </p>
        </ComoLer>
        {!emGrupo && <FontesEDatas itens={itens} titulo="Fontes e datas deste resumo" snapshot={snapshot} />}
      </div>
    </section>
  )
}
