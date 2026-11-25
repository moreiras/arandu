// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../components/layout/LinkDatado'
import { SITE } from '../lib/site'
import { TetosDeUso } from '../components/TetosDeUso'

const origem = typeof window !== 'undefined' ? window.location.origin : SITE.url

function Codigo({ children, rotulo }: { children: string; rotulo: string }) {
  return <pre aria-label={rotulo} className="bg-gray-900 text-ok-300 text-xs rounded-lg p-3 overflow-x-auto"><code>{children}</code></pre>
}

/** `/dados`: como usar os mesmos dados fora da interface — API REST (curl) e servidor MCP (para LLMs) — com links para a documentação interativa e para o catálogo. */
export function DadosPage() {
  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Dados abertos: API e MCP</h1>
        <p className="text-sm text-gray-500 mt-1">
          Tudo o que a interface mostra vem de uma API REST somente leitura, de snapshots datados. O mesmo motor de consulta responde ao servidor MCP, que
          permite perguntar em linguagem natural a um assistente de IA. Cada número tem fonte e data (veja as <Link to="/fontes" className="text-primario-600 hover:underline">fontes</Link>).
        </p>
      </div>

      {/* o uso com conta primeiro; o anônimo e os limites dele depois. */}
      <section aria-labelledby="com-conta" className="space-y-3 rounded-lg border border-primario-200 bg-primario-50/50 p-4">
        <h2 id="com-conta" className="text-titulo-3 text-gray-800">Comece com uma conta (gratuita)</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-gray-700">
          <li><Link to="/login" className="text-primario-700 hover:underline">Entre</Link> com Google, LinkedIn ou PeeringDB. A conta é gratuita e libera as listas completas, o histórico e os contatos na interface.</li>
          <li>No seu <Link to="/perfil" className="text-primario-700 hover:underline">perfil</Link>, gere uma <strong>chave de MCP</strong>. Ela é pessoal; guarde-a como uma senha.</li>
          <li>Configure o seu cliente MCP com a chave no cabeçalho <code>Authorization: Bearer</code> (exemplos abaixo).</li>
        </ol>
        <p className="text-xs text-gray-600">
          Sem conta, o MCP funciona em prévia (listas de até 100 itens, 1ª página, os 2 snapshots mais recentes), e a API, chamada por scripts, tem um orçamento de uso por rede.
          A API REST não tem chave própria: no navegador ela usa a sua sessão; em scripts, use a chave pelo MCP ou fique dentro da prévia.
        </p>
      </section>

      <section aria-labelledby="tetos" className="space-y-3">
        <h2 id="tetos" className="text-titulo-3 text-gray-800">Limites de uso sem conta</h2>
        <TetosDeUso />
      </section>

      <section aria-labelledby="api" className="space-y-3">
        <h2 id="api" className="text-titulo-3 text-gray-800">API REST</h2>
        <p className="text-sm text-gray-600">Documentação interativa (Swagger): <a className="text-primario-600 hover:underline" href="/api/v1/docs">/api/v1/docs</a> · esquema <a className="text-primario-600 hover:underline" href="/api/v1/openapi.json">openapi.json</a>.
          Sem <code>date</code> a API usa o snapshot mais recente; passe <code>?date=AAAA-MM-DD</code> para um snapshot específico (as duas mais recentes são livres; o histórico exige login). A lista das datas livres está em <code>/api/v1/brasil/snapshots</code>; a lista inteira (<code>/api/v1/snapshots</code>) exige login.</p>
        <Codigo rotulo="Exemplo: snapshots disponíveis">{`curl -s ${origem}/api/v1/brasil/snapshots`}</Codigo>
        <Codigo rotulo="Exemplo: documento de um AS">{`curl -s ${origem}/api/v1/asns/8167`}</Codigo>
        <Codigo rotulo="Exemplo: consulta com filtro e ordenação">{`curl -s -X POST ${origem}/api/v1/query/operadoras \
  -H 'content-type: application/json' \
  -d '{"filter":{"field":"uf_sede","op":"eq","value":"ES"},"select":["empresa","acessos"],"sort":[{"field":"acessos","dir":"desc"}],"limit":5}'`}</Codigo>
        <p className="text-xs text-gray-500">Os campos de cada coleção estão em <a className="text-primario-600 hover:underline" href="/api/v1/schema">/api/v1/schema</a>. Contatos (e-mail e telefone) não são servidos pela API pública. Há limite de requisições por IP.</p>
      </section>

      <section aria-labelledby="mcp" className="space-y-3">
        <h2 id="mcp" className="text-titulo-3 text-gray-800">Servidor MCP</h2>
        <p className="text-sm text-gray-600">O servidor MCP (Model Context Protocol, transporte Streamable HTTP) expõe consultas, buscas por entidade e receitas prontas para assistentes de IA.
          Endereço: <code className="bg-gray-100 px-1 rounded">{origem}/mcp</code>.</p>
        <Codigo rotulo="Exemplo: adicionar ao Claude Code">{`claude mcp add --transport http ${SITE.mcp} ${origem}/mcp --header "Authorization: Bearer SUA_CHAVE"`}</Codigo>
        <Codigo rotulo="Exemplo: configuração JSON de um cliente MCP">{`{
  "mcpServers": {
    "${SITE.mcp}": {
      "type": "http",
      "url": "${origem}/mcp",
      "headers": { "Authorization": "Bearer SUA_CHAVE" }
    }
  }
}`}</Codigo>
        <p className="text-xs text-gray-500">Sem o cabeçalho, o servidor responde em prévia. Troque <code>SUA_CHAVE</code> pela chave gerada no perfil.</p>
        <p className="text-xs text-gray-500">Comece pela ferramenta <code>describe_schema</code>: ela lista os campos, os valores aceitos e receitas prontas (pergunta → argumentos).</p>
      </section>

      <section aria-labelledby="catalogo" className="space-y-2">
        <h2 id="catalogo" className="text-titulo-3 text-gray-800">Catálogo e código</h2>
        <ul className="text-sm text-gray-600 list-disc pl-5 space-y-1">
          <li><Link to="/fontes" className="text-primario-600 hover:underline">Fontes de dados</Link>: licenças, periodicidade, última coleta e os campos de cada fonte e produto.</li>
          <li><Link to="/sobre" className="text-primario-600 hover:underline">Metodologia</Link> e <Link to="/privacidade" className="text-primario-600 hover:underline">privacidade</Link>.</li>
          <li><a href="/llms.txt" className="text-primario-600 hover:underline">llms.txt</a> e <a href="/sitemap.xml" className="text-primario-600 hover:underline">sitemap.xml</a> para agentes e buscadores; <Link to="/mapa-do-site" className="text-primario-600 hover:underline">mapa do site</Link> para pessoas.</li>
          <li>Código aberto, licença AGPL-3.0-or-later.</li>
        </ul>
      </section>
    </div>
  )
}
