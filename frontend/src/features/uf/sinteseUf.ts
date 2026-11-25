// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { limitar, n0, n1, plural, type FraseSintese } from '../../lib/sintese'
import { nomeUf } from '../../lib/ufs'
import { UNIVERSOS } from '../../lib/universos'
import type { UfCtx } from './contexto'

export const REGRAS_SINTESE_UF = 'sintese-uf-1'
const SICI = 'SICI, Anatel (declarado pelas operadoras)'

/**
 * Síntese da UF (PT-22, uf 5.5): frases montadas dos números do painel e da posição (`UfCtx`: totais do perfil, território e PTTs), na ordem fixa
 * mercado, domicílios, infraestrutura, rede. Ficam de fora as frases que pedem agregados novos do pipeline (maiores operadoras, ASNs sem sessão em PTT):
 * a das operadoras seria ranking nominal e a outra não tem fonte nesta página. Posição entre as 27 UFs e "Brasil: X" nos KPIs também dependem de
 * `/ufs` e ficam em `PosicaoBloco`. Sem dado, sem frase; UF sem município longe de PTT não ganha a frase de distância.
 */
export function sinteseUf(c: UfCtx, snapshot: string | null): FraseSintese[] {
  const t = c.totais
  const nome = nomeUf(c.uf)
  const mes = c.mesReferencia ?? c.territorio?.mes_referencia_sici ?? null
  const pen = c.territorio?.penetracao
  const longe = t.municipios_sem_ptt
  return limitar([
    t.acessos != null && t.acessos > 0 && { id: 'acessos', selo: 'fato', fonte: SICI, dataRef: mes,
      texto: `${nome} tem ${n0(t.acessos)} acessos de banda larga fixa declarados ao SICI${t.municipios != null ? `, em ${plural(t.municipios, 'município', 'municípios')}` : ''}${t.fibra_pct != null ? `; ${n1(t.fibra_pct)}% deles são em fibra` : ''}.` },
    pen != null && { id: 'penetracao', selo: 'estimado', fonte: 'SICI, Anatel, e Censo 2022 (IBGE) com projeção pela PNAD', dataRef: c.territorio?.mes_referencia_sici ?? mes,
      texto: `Estimativa: ${n1(pen * 100)} acessos fixos para cada 100 domicílios (domicílios do Censo 2022 projetados pela PNAD; acesso não é domicílio).` },
    longe != null && longe > 0 && t.municipios != null && { id: 'sem-ptt', selo: 'estimado', fonte: 'SICI, Anatel, e PTTs do IX.br (distância em linha reta)', dataRef: mes,
      texto: `Dos ${n0(t.municipios)} municípios com acessos declarados, ${plural(longe, 'fica', 'ficam')} a mais de ${n0(t.raio_sem_ptt_km)} km em linha reta de um PTT do IX.br${t.acessos_sem_ptt != null ? `, com ${n0(t.acessos_sem_ptt)} acessos fixos declarados` : ''} (distância do centróide, não trajeto de fibra).` },
    { id: 'rede', selo: 'fato', fonte: 'looking glasses do IX.br e Registro.br', dataRef: snapshot,
      texto: `${c.ixps.length === 0 ? 'Não há PTT do IX.br na UF' : `A UF tem ${plural(c.ixps.length, 'PTT do IX.br', 'PTTs do IX.br')}`}; ${n0(t.asns)} ${UNIVERSOS.asnsComUf.rotulo} (a UF é a da sede, não a de operação).` },
  ])
}
