// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { n0, n1, plural, type FraseSintese } from '../../lib/sintese'
import type { MercadoRaio } from './calculos'

export const REGRAS_SINTESE_LOCALIZADOR = 'sintese-localizador-1'

export interface EntradaSinteseLocalizador {
  radius: number
  /** Contagens do painel: ASNs distintos no raio, entidades (CNPJ ou AS sem CNPJ) com ASN no raio e com outorga SCM. */
  entityCounts: { asns: number; cnpjsComAsn: number; scms: number }
  /** Sedes de AS no raio (`resumoDoRaio`). */
  sedesAsn: number
  /** ASNs da lista do raio e as contagens de participação em PTT do IX.br sobre eles (`contagensIx`). */
  filteredAsnsCount: number
  nearestIx: string | null
  ixLabel: (code: string) => string
  ixCounts: { nearMember: number; anyMember: number }
  temPresenca: boolean
  mercado: MercadoRaio | null
  municipiosNoRaio: number
  mesReferencia?: string | null
  snapshot: string | null
}

/**
 * Síntese do raio no Localizador (PT-22, localizador 5.3): três frases dos números do painel (as mesmas variáveis que o painel e o bloco de mercado usam), na
 * ordem redes, interconexão, mercado. A pertinência ao raio vem de pontos geocodificados (sede da organização), por isso o selo é inferido; os acessos são declarados
 * à Anatel. Raio sem rede nem prestador diz isso, e a frase de mercado só existe com acessos declarados nos municípios do raio. Cada frase é completa, para leitor de tela.
 */
export function sinteseLocalizador(e: EntradaSinteseLocalizador): FraseSintese[] {
  const f: FraseSintese[] = []
  const vazio = e.entityCounts.asns === 0 && e.entityCounts.scms === 0
  f.push({ id: 'raio', selo: 'inferido', fonte: 'Registro.br e geolocalização das sedes (cadastro de CNPJ)', dataRef: e.snapshot,
    texto: vazio
      ? `Nenhuma rede ou prestador com sede neste raio de ${n0(e.radius)} km.`
      : `No raio de ${n0(e.radius)} km há ${plural(e.entityCounts.asns, 'ASN', 'ASNs')} (${plural(e.sedesAsn, 'sede de AS', 'sedes de AS')}), em ${plural(e.entityCounts.cnpjsComAsn, 'entidade', 'entidades')} com ASN; ${n0(e.entityCounts.scms)} com outorga SCM.` })
  if (!vazio && e.temPresenca && e.nearestIx && e.filteredAsnsCount > 0) {
    f.push({ id: 'ix', selo: 'fato', fonte: 'cadastro de participantes do IX.br', dataRef: e.snapshot,
      texto: `Entre ${plural(e.filteredAsnsCount, 'ASN listado', 'ASNs listados')} no raio, ${n0(e.ixCounts.nearMember)} participam de ${e.ixLabel(e.nearestIx)} (o PTT do IX.br mais próximo do ponto) e ${n0(e.ixCounts.anyMember)} de algum PTT do IX.br.` })
  }
  if (e.mercado && e.mesReferencia) {
    f.push({ id: 'mercado', selo: 'fato', fonte: 'SICI, Anatel (declarado pelas operadoras)', dataRef: e.mesReferencia,
      texto: `${e.municipiosNoRaio === 1 ? 'No município' : `Nos ${n0(e.municipiosNoRaio)} municípios`} com centro no raio foram declarados ${n0(e.mercado.acessos)} acessos de banda larga fixa, de ${plural(e.mercado.operadoras, 'CNPJ', 'CNPJs')}; a maior participação é de ${n1(e.mercado.maiorParticipacao)}% (regra: acessos declarados por CNPJ).` })
  }
  return f
}
