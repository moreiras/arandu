// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SITE } from '../../lib/site'

/** O que acontece de fato com um snapshot publicado (D8). O link usa o endereço do código-fonte da instância, nunca um domínio fixo. */
export function CorrecoesNoChangelog() {
  return (
    <>
      Snapshots publicados não mudam, salvo correção registrada no{' '}
      <a href={`${SITE.codigoFonte}/blob/main/CHANGELOG.md`} target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline">CHANGELOG</a>{' '}
      do projeto; quando a correção altera um número publicado, as páginas afetadas trazem uma nota datada.
    </>
  )
}
