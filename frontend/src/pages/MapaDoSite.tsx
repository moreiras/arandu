// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../components/layout/LinkDatado'
import { GRUPOS_MENU, ITENS_AVULSOS } from '../components/layout/menu'

/**
 * `/mapa-do-site`: todas as páginas, por tema, com a descrição do menu (fonte única). Para pessoas;
 * o `/sitemap.xml` é para buscadores. Ajuda a NBR 17225 5.7.13 (mais de uma forma de achar uma página).
 */
export function MapaDoSite() {
  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Mapa do site</h1>
        <p className="mt-1 text-sm text-gray-600">Todas as páginas, por tema. Páginas de AS, PTT, operadora, município e UF se abrem pela busca no topo ou pelas listas.</p>
      </div>
      <div className="grid gap-6 sm:grid-cols-2">
        {GRUPOS_MENU.map((g) => (
          <section key={g.id} aria-labelledby={`mapa-${g.id}`}>
            <h2 id={`mapa-${g.id}`} className="text-titulo-3 text-gray-800">{g.rotulo}</h2>
            <ul className="mt-1 space-y-1.5">
              {g.itens.filter((i) => !i.externo).map((i) => (
                <li key={i.to}><Link to={i.to} className="font-medium text-primario-700 hover:underline">{i.rotulo}</Link>{i.descricao && <span className="block text-sm text-gray-600">{i.descricao}</span>}</li>
              ))}
            </ul>
          </section>
        ))}
        <section aria-labelledby="mapa-outros">
          <h2 id="mapa-outros" className="text-titulo-3 text-gray-800">Outras</h2>
          <ul className="mt-1 space-y-1.5">
            {ITENS_AVULSOS.map((i) => <li key={i.to}><Link to={i.to} className="font-medium text-primario-700 hover:underline">{i.rotulo}</Link>{i.descricao && <span className="block text-sm text-gray-600">{i.descricao}</span>}</li>)}
            <li><Link to="/privacidade" className="font-medium text-primario-700 hover:underline">Política de privacidade</Link></li>
            <li><Link to="/uso-aceitavel" className="font-medium text-primario-700 hover:underline">Política de uso aceitável</Link></li>
            <li><Link to="/acessibilidade" className="font-medium text-primario-700 hover:underline">Acessibilidade</Link></li>
            <li><a href="/sitemap.xml" className="font-medium text-primario-700 hover:underline">Sitemap para buscadores (XML)</a></li>
          </ul>
        </section>
      </div>
    </div>
  )
}
