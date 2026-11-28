// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { formatarReferencia } from '../../components/entidade/proveniencia'
import { limitar, MAX_FRASES_ORDEM_FIXA, n0, n1, palavra, plural, type FraseSintese } from '../../lib/sintese'
import { nomeUf } from '../../lib/ufs'
import { UNIVERSOS } from '../../lib/universos'
import { fmtCnpj } from '../municipio/ui'
import type { UfCtx } from './contexto'

export const REGRAS_SINTESE_UF = 'sintese-uf-3'
const SICI = 'SICI, Anatel (declarado pelas operadoras)'

/**
 * Síntese da UF (PT-22, uf 5.5): frases montadas dos números do painel e dos blocos (`UfCtx`: totais do perfil, território, operadoras presentes e indicadores), na
 * ordem fixa mercado, domicílios, infraestrutura, rede e regulação. A frase das maiores operadoras é ranking nominal: só entra com a regra e o mês de referência na
 * própria frase e com o link para o ranking completo; os nomes vêm do perfil, que já aplica a regra de pessoa natural (o registro traz `cnpj` e `asns`). A de
 * CNPJs sem declaração usa o `include=indicadores` que a página já pede (nenhuma chamada a mais). "Brasil: X" e a posição entre as 27 UFs ficam nos cartões do
 * painel (`referenciasUf.ts`) e em `PosicaoBloco`. Sem dado, sem frase; UF sem município longe de PTT não ganha a frase de distância.
 */
export function sinteseUf(c: UfCtx, snapshot: string | null): FraseSintese[] {
  const t = c.totais
  const nome = nomeUf(c.uf)
  const mes = c.mesReferencia ?? c.territorio?.mes_referencia_sici ?? null
  const mesTxt = mes ? formatarReferencia(mes) : null
  const pen = c.territorio?.penetracao
  const longe = t.municipios_sem_ptt
  const tres = c.operadorasPresentes.slice(0, 3)
  const sem = c.indicadores?.sem_declaracao
  const mesDecl = c.indicadores?.mes_referencia ?? mes
  return limitar([
    t.acessos != null && t.acessos > 0 && { id: 'acessos', selo: 'fato', fonte: SICI, dataRef: mes,
      texto: `${nome} tem ${n0(t.acessos)} acessos de banda larga fixa declarados ao SICI${mesTxt ? ` em ${mesTxt}` : ''}${t.municipios != null ? `, em ${plural(t.municipios, 'município', 'municípios')}` : ''}${t.fibra_pct != null ? `, e ${n1(t.fibra_pct)}% deles são em fibra` : ''}.` },
    tres.length === 3 && { id: 'operadoras', selo: 'fato', fonte: SICI, dataRef: mes,
      texto: `${mesTxt ? `Em ${mesTxt}, as` : 'As'} três operadoras com mais acessos fixos declarados ao SICI em ${nome} são ${tres.map((o) => `${o.empresa || o.razao_social || fmtCnpj(o.cnpj)} (${n1(o.share)}% dos acessos declarados na UF)`).join(', ').replace(/, ([^,]*)$/, ' e $1')}. Regra: ordem decrescente dos acessos declarados na UF, um CNPJ por operadora, sem somar grupos econômicos.`,
      link: { to: `/operadoras?visao=ranking&uf=${c.uf}`, rotulo: 'Ver o ranking completo da UF' } },
    pen != null && { id: 'penetracao', selo: 'estimado', fonte: 'SICI, Anatel, e Censo 2022 (IBGE) com projeção pela PNAD', dataRef: c.territorio?.mes_referencia_sici ?? mes,
      texto: `Estimativa: ${n1(pen * 100)} acessos fixos para cada 100 domicílios. Os domicílios são os do Censo 2022 projetados pela PNAD, e acesso não é domicílio.` },
    longe != null && longe > 0 && t.municipios != null && { id: 'sem-ptt', selo: 'estimado', fonte: 'SICI, Anatel, e PTTs do IX.br (distância em linha reta)', dataRef: mes,
      texto: `Dos ${n0(t.municipios)} municípios com acessos declarados, ${plural(longe, 'fica', 'ficam')} a mais de ${n0(t.raio_sem_ptt_km)} km em linha reta de um PTT do IX.br${t.acessos_sem_ptt != null ? `, com ${n0(t.acessos_sem_ptt)} acessos fixos declarados` : ''}. A distância é a do centróide do município, não o trajeto de fibra.` },
    { id: 'rede', selo: 'fato', fonte: 'looking glasses do IX.br e Registro.br', dataRef: snapshot,
      texto: `${c.ixps.length === 0 ? 'Não há PTT do IX.br na UF' : `A UF tem ${plural(c.ixps.length, 'PTT do IX.br', 'PTTs do IX.br')}`}. Há ${n0(t.asns)} ${UNIVERSOS.asnsComUf.rotulo}, e a UF é a da sede, não a de operação.` },
    t.asns > 1 && t.asns_sem_sessao_ptt != null && { id: 'sem-sessao', selo: 'fato', fonte: 'looking glasses e route servers do IX.br, e Registro.br', dataRef: snapshot,
      texto: `Dos ${n0(t.asns)} ASNs brasileiros com sede em ${nome}, ${n0(t.asns_sem_sessao_ptt)} ${palavra(t.asns_sem_sessao_ptt, 'não tem', 'não têm')} sessão direta em PTT do IX.br. Sessão direta é a sessão BGP do ASN com o route server de ao menos um PTT; o ASN pode alcançar o IX.br por trânsito de outro AS, e a UF é a da sede, não a de operação.` },
    sem != null && mesDecl != null && { id: 'sem-declaracao', selo: 'fato', fonte: 'SICI e outorgas SCM, Anatel', dataRef: mesDecl,
      texto: `${plural(sem.cnpjs_sem_declaracao, 'CNPJ com outorga SCM e sede em ' + nome + ' não tem', 'CNPJs com outorga SCM e sede em ' + nome + ' não têm')} acessos declarados ao SICI em ${formatarReferencia(mesDecl)}. Regra: CNPJ com outorga SCM e sede na UF sem acessos declarados nesse mês; isso não indica causa nem intenção.` },
  ], MAX_FRASES_ORDEM_FIXA)
}
