// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../layout/LinkDatado'

export type TipoAcoes = 'asn' | 'operadora' | 'municipio' | 'ixp' | 'grupo'

/** Ações transversais do cabeçalho de uma entidade: comparar com outras do mesmo tipo e abrir o relatório de uma página (imprimir ou salvar em PDF pelo navegador). */
export function AcoesEntidade({ tipo, id }: { tipo: TipoAcoes; id: string }) {
  const classe = 'rounded border border-gray-200 bg-white px-2 py-1 text-xs text-primario-700 hover:bg-primario-50'
  return (
    <div className="flex flex-wrap gap-2 print:hidden" data-testid="acoes-entidade">
      {tipo !== 'grupo' && <Link to={`/comparar?tipo=${tipo}&ids=${encodeURIComponent(id)}`} className={classe}>Comparar com outros</Link>}
      {tipo !== 'ixp' && <Link to={`/relatorio/${tipo}/${encodeURIComponent(id)}`} className={classe}>Relatório de uma página</Link>}
    </div>
  )
}
