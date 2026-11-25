// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useMemo, useState } from 'react'
import { SinteseTopo } from '../../components/ui/SinteseTopo'
import type { FraseSintese } from '../../lib/sintese'
import { REGRAS_SINTESE_LOCALIZADOR, sinteseLocalizador, type EntradaSinteseLocalizador } from './sinteseLocalizador'

/** O valor depois de `ms` sem mudar: o raio no controle deslizante muda a cada pixel e o leitor de tela não deve anunciar cada passo. */
export function useAtrasado<T>(valor: T, ms: number): T {
  const [x, setX] = useState(valor)
  useEffect(() => {
    const t = setTimeout(() => setX(valor), ms)
    return () => clearTimeout(t)
  }, [valor, ms])
  return x
}

export const ESPERA_SINTESE_MS = 500

/**
 * Síntese em texto do raio, ao vivo (`role="status"`, `aria-live="polite"`): atualiza a cada mudança de ponto ou raio, com espera de 500 ms. Serve de alternativa em texto ao
 * mapa, que é canvas. Sem ponto escolhido mostra só a instrução, também na região anunciada. A região reserva altura para a página não saltar quando a síntese aparece.
 */
export function SinteseLocalizador({ marcado, entrada }: { marcado: boolean; entrada: EntradaSinteseLocalizador }) {
  // a chave textual evita novo efeito a cada renderização (a entrada é um objeto novo a cada vez)
  const chave = JSON.stringify(marcado ? sinteseLocalizador(entrada) : [])
  const atrasada = useAtrasado(chave, ESPERA_SINTESE_MS)
  const frases = useMemo(() => JSON.parse(atrasada) as FraseSintese[], [atrasada])
  return (
    <div className="min-h-[7.5rem]" data-testid="sintese-localizador">
      {frases.length === 0 ? (
        <p role="status" aria-live="polite" className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700">
          Escolha um ponto no mapa ou busque um município: aqui aparece um resumo em texto das redes, da interconexão e dos acessos de banda larga ao redor.
        </p>
      ) : (
        <SinteseTopo frases={frases} snapshot={entrada.snapshot} regras={REGRAS_SINTESE_LOCALIZADOR} aoVivo minFrases={1}
          comoLer="Atualiza ao mudar o ponto ou o raio. A pertinência ao raio usa a localização da sede; a lista e o mapa mostram o detalhe." />
      )}
    </div>
  )
}
