// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useId, type RefObject } from 'react'
import { DESCRICAO_SELO, formatarReferencia, nomeAcessivelSelo, ROTULO_SELO, type Selo } from '../entidade/proveniencia'
import { FormaSelo } from './SeloMarca'

/** Data na dica: dia ou mês, sem o horário de um carimbo ISO. */
function dataCurta(v: string): string {
  const m = /^(\d{4}-\d{2}(?:-\d{2})?)(?:$|T)/.exec(v)
  return formatarReferencia(m ? m[1] : v)
}

/**
 * Classes da dica, para o cartão que a contém (`group/cartao relative`): a dica aparece abaixo do cartão, sem cobrir o número, e
 * abre só por CSS, com o mouse sobre o cartão (depois de um instante) ou com o foco no botão do selo. Toque e teclado abrem pelo foco.
 * Esc fecha (o atributo `data-dica-fechada` é gravado no próprio elemento, sem estado do React). Nada aqui é estado de hover.
 */
export const CLASSES_CARTAO_COM_DICA = 'group/cartao relative'

/**
 * Selo clicável do cartão (PT-30): o botão leva a forma pequena, no canto superior direito, com o significado como nome acessível; a
 * dica com a natureza, a fonte e a data de referência fica ligada ao botão por `aria-describedby` (e continua no bloco recolhido
 * "Fontes e datas destes números", a versão completa). Abre por mouse (hover do cartão), por foco do teclado e por toque (o toque foca
 * o botão); Esc fecha sem mover o foco (WCAG 1.4.13: dispensável, e fica aberta enquanto o ponteiro está sobre o cartão ou a dica).
 */
export function SeloDica({ selo, fonte, dataRef, cartao }: { selo: Selo; fonte?: string; dataRef?: string | null; cartao: RefObject<HTMLElement | null> }) {
  const id = useId()

  useEffect(() => {
    const raiz = cartao.current
    if (!raiz) return
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && (raiz.matches(':hover') || raiz.contains(document.activeElement))) raiz.setAttribute('data-dica-fechada', '')
    }
    const reabrir = () => raiz.removeAttribute('data-dica-fechada')
    document.addEventListener('keydown', esc)
    raiz.addEventListener('mouseleave', reabrir)
    raiz.addEventListener('focusout', reabrir)
    return () => {
      document.removeEventListener('keydown', esc)
      raiz.removeEventListener('mouseleave', reabrir)
      raiz.removeEventListener('focusout', reabrir)
    }
  }, [cartao])

  return (
    <>
      <button
        type="button"
        className="absolute right-0.5 top-0.5 inline-flex h-6 w-6 items-center justify-center rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-700"
        aria-label={nomeAcessivelSelo(selo)}
        aria-describedby={id}
        data-selo={selo}
        data-testid="selo-dica-botao"
        onClick={(e) => e.currentTarget.focus()}
      >
        <FormaSelo selo={selo} tamanho={12} />
      </button>
      <span
        id={id}
        role="tooltip"
        data-testid="selo-dica"
        className={[
          'pointer-events-none invisible absolute left-0 top-full z-20 mt-1 w-full min-w-[8rem] rounded-md border border-gray-300 bg-white p-2 text-left text-xs leading-snug text-gray-900 opacity-0 shadow-md transition-opacity',
          'group-hover/cartao:pointer-events-auto group-hover/cartao:visible group-hover/cartao:opacity-100 group-hover/cartao:delay-300',
          'group-focus-within/cartao:pointer-events-auto group-focus-within/cartao:visible group-focus-within/cartao:opacity-100',
          'group-data-[dica-fechada]/cartao:!invisible group-data-[dica-fechada]/cartao:!opacity-0',
        ].join(' ')}
      >
        <span className="block font-semibold">{ROTULO_SELO[selo]}</span>
        <span className="block">{DESCRICAO_SELO[selo]}</span>
        {fonte && <span className="mt-1 block">Fonte: {fonte}</span>}
        {dataRef && <span className="block">Referência: {dataCurta(dataRef)}</span>}
      </span>
    </>
  )
}
