// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { TerritorioMunicipio, TerritorioUf } from '../../types/api'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const razao = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)

type Dados = (TerritorioMunicipio | TerritorioUf) & { penetracao?: number; domicilios?: number }

/**
 * Penetração de banda larga fixa e domicílios sem acesso fixo de pessoa física, de um município ou de uma UF. Penetração = acessos fixos declarados ÷ domicílios (Censo 2022);
 * os domicílios sem acesso fixo são ESTIMATIVA (inclui quem usa só o celular). A fórmula e o limite ficam à vista, no bloco.
 */
export function PenetracaoBloco({ t, rotuloTerritorio }: { t: Dados; rotuloTerritorio: string }) {
  const m = t as TerritorioMunicipio
  return (
    <div className="space-y-3 text-sm" data-testid="penetracao">
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div><dt className="text-xs text-gray-500">População estimada{t.estimativa_ano ? ` (${t.estimativa_ano})` : ''}</dt><dd className="text-lg font-semibold tabular-nums">{n(t.populacao_estimada ?? t.populacao)}</dd>
          {t.populacao_estimada != null && t.populacao != null && <dd className="text-xs text-gray-500">Censo {t.censo_ano}: {n(t.populacao)}</dd>}</div>
        <div><dt className="text-xs text-gray-500">Domicílios (projeção para {t.ano_projecao_domicilios ?? t.censo_ano})</dt><dd className="text-lg font-semibold tabular-nums">{n(t.domicilios_projetados ?? t.domicilios)}</dd>
          <dd className="text-xs text-gray-500">Censo {t.censo_ano}: {n(t.domicilios)}</dd></div>
        <div><dt className="text-xs text-gray-500">Acessos fixos por domicílio</dt><dd className="text-lg font-semibold tabular-nums">{razao(t.penetracao)}</dd>
          <dd className="text-xs text-gray-500">só pessoa física: {razao(t.penetracao_pf)}</dd></div>
        <div><dt className="text-xs text-gray-500">Domicílios sem acesso fixo de pessoa física (estimativa, taxa de Internet da PNAD)</dt><dd className="text-lg font-semibold tabular-nums">{n(t.nao_visto)}</dd>
          <dd className="text-xs text-gray-500">{pct(t.nao_visto_pct)} dos domicílios; inclui quem usa só o celular</dd></div>
      </dl>
      {m.sem_declaracao_sici && <p className="text-xs text-gray-600">Nenhuma operadora declarou acessos fixos neste município no SICI de {t.mes_referencia_sici}.</p>}
      <p className="text-xs text-gray-500">
        Acessos: SICI de {t.mes_referencia_sici}. Os domicílios do Censo {t.censo_ano} são projetados para {t.ano_projecao_domicilios ?? t.censo_ano} pelo crescimento de domicílios da UF na PNAD (igual em todos os municípios dela). Domicílios sem acesso fixo de pessoa física = domicílios projetados × taxa de internet da UF (PNAD {t.pnad_ano}, {pct((t as TerritorioUf).taxa_internet_pnad ?? undefined) !== '—' ? pct((t as TerritorioUf).taxa_internet_pnad) : 'taxa da UF'})
        − acessos de pessoa física, nunca abaixo de zero. A taxa mede domicílios em que havia utilização de internet, incluindo quem usa só o celular, e vale igual para todos os municípios da UF;
        por isso é uma estimativa de ordem de grandeza para {rotuloTerritorio}, não uma contagem.
      </p>
    </div>
  )
}
