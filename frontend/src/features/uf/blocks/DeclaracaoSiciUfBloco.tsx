// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { UfCtx } from '../contexto'
import { COLETA_ANATEL, NOTA_COLETA_ANATEL } from '../../../lib/referencias'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v > 0 ? '+' : ''}${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`)

/**
 * Declaração de acessos na UF (PT-26, UF 5.2): quantos CNPJs declararam no mês de referência e quantos CNPJs com outorga SCM e sede na UF não
 * têm acessos declarados nele, por classe de usuários estimados. Só contagens (nenhum nome), com a regra de referência e o limite da leitura.
 */
export function DeclaracaoSiciUfBloco({ dados }: BlocoProps<UfCtx>) {
  const i = dados.indicadores!
  const s = i.sem_declaracao
  const mes = i.mes_referencia
  return (
    <div className="space-y-2 text-sm" data-testid="declaracao-sici-uf">
      <p>
        <strong>{n(i.n_operadoras)}</strong> CNPJs declararam acessos na UF em {mes}; variação dos acessos declarados na UF: {pct(i.var_mm_pct)} no mês e {pct(i.var_aa_pct)} em 12 meses.
      </p>
      {s && (
        <div>
          <p><strong>{n(s.cnpjs_sem_declaracao)}</strong> CNPJs com outorga SCM e sede na UF sem declaração em {mes}:</p>
          <ul className="list-disc pl-5 text-gray-700">
            <li>{n(s.com_usuarios_apnic)} com ASN ligado ao CNPJ e 100 ou mais usuários estimados (APNIC), somando {n(s.usuarios_apnic)} usuários estimados;</li>
            <li>{n(s.sem_usuarios)} com ASN ligado ao CNPJ e menos de 100 usuários estimados;</li>
            <li>{n(s.nao_comparavel)} sem ASN ligado ao CNPJ (sem como observar usuários).</li>
          </ul>
          <p className="mt-1"><Link to={`/operadoras?visao=sem-declaracao&uf=${dados.uf}`} className="text-primario-600 hover:underline">Ver a lista, com a regra e o mês de referência</Link></p>
        </div>
      )}
      <p className="text-xs text-gray-500">
        {NOTA_COLETA_ANATEL} Sem declaração em {mes} diz só que não há acessos do CNPJ declarados nesse mês no {COLETA_ANATEL}; não indica causa nem intenção. A UF é a do cadastro da outorga (sede), não a área de atuação. Usuários são estimativa da APNIC (medição estatística), não contagem.
      </p>
    </div>
  )
}
