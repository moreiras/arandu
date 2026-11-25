// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../components/layout/LinkDatado'
import { SITE } from '../lib/site'
import { EscolhaSeuAcesso } from '../components/EscolhaSeuAcesso'
import { useLimites } from '../hooks/useLimites'
import { CORPO_EXEMPLO_CONSULTA } from '../lib/exemplosDados'

const origem = typeof window !== 'undefined' ? window.location.origin : SITE.url

function Codigo({ children, rotulo }: { children: string; rotulo: string }) {
  return <pre aria-label={rotulo} className="bg-gray-900 text-ok-300 text-xs rounded-lg p-3 overflow-x-auto"><code>{children}</code></pre>
}

/** `/dados`: como usar os mesmos dados fora da interface — API REST (curl) e servidor MCP (para LLMs) — com links para a documentação interativa e para o catálogo. */
export function DadosPage() {
  // sem a chave de MCP ligada na instalação, nenhum texto a promete; enquanto os limites carregam vale o padrão de quem a oferece
  const comChave = useLimites().data?.mcp.chave.ativa !== false
  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Dados abertos: API e MCP</h1>
        <p className="text-sm text-gray-500 mt-1">
          Tudo o que a interface mostra vem de uma API REST somente leitura, de snapshots datados. O mesmo motor de consulta responde ao servidor MCP, que
          permite perguntar em linguagem natural a um assistente de IA. Cada número tem fonte e data (veja as <Link to="/fontes" className="text-primario-600 hover:underline">fontes</Link>).
        </p>
      </div>

      <section aria-labelledby="tetos" className="space-y-3">
        <h2 id="tetos" className="text-titulo-3 text-gray-800">Escolha o seu acesso</h2>
        <EscolhaSeuAcesso />
      </section>

      <section aria-labelledby="com-conta" className="space-y-3 rounded-lg border border-primario-200 bg-primario-50/50 p-4">
        <h2 id="com-conta" className="text-titulo-3 text-gray-800">Comece com uma conta (gratuita)</h2>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-gray-700">
          <li><Link to="/login" className="text-primario-700 underline">Entre</Link> com Google, LinkedIn ou PeeringDB. A conta é gratuita e libera as listas completas, o histórico e os contatos na interface.</li>
          {comChave && <li>No seu <Link to="/perfil" className="text-primario-700 underline">perfil</Link>, gere uma <strong>chave de MCP</strong>. Ela é pessoal; guarde-a como uma senha.</li>}
          {comChave && <li>Configure o seu cliente MCP com a chave no cabeçalho <code>Authorization: Bearer</code> (exemplos abaixo).</li>}
        </ol>
        <p className="text-xs text-gray-600">
          A API REST não tem chave própria: no navegador ela usa a sua sessão; em scripts, fique dentro da prévia{comChave ? ' ou use a chave pelo MCP' : ''}.
        </p>
      </section>

      <section aria-labelledby="api" className="space-y-3">
        <h2 id="api" className="text-titulo-3 text-gray-800">API REST</h2>
        <p className="text-sm text-gray-600">Documentação interativa (Swagger): <a className="text-primario-600 hover:underline" href="/api/v1/docs">/api/v1/docs</a> · esquema <a className="text-primario-600 hover:underline" href="/api/v1/openapi.json">openapi.json</a>.
          Sem <code>date</code> a API usa o snapshot mais recente; passe <code>?date=AAAA-MM-DD</code> para um snapshot específico (as duas mais recentes são livres; o histórico exige login). A lista das datas livres está em <code>/api/v1/brasil/snapshots</code>; a lista inteira (<code>/api/v1/snapshots</code>) exige login.</p>
        <Codigo rotulo="Exemplo: snapshots disponíveis">{`curl -s ${origem}/api/v1/brasil/snapshots`}</Codigo>
        <Codigo rotulo="Exemplo: documento de um AS">{`curl -s ${origem}/api/v1/asns/8167`}</Codigo>
        <Codigo rotulo="Exemplo: operadoras com mais acessos em uma UF">{`curl -s -X POST ${origem}/api/v1/query/acessos_municipio \
  -H 'content-type: application/json' \
  -d '${CORPO_EXEMPLO_CONSULTA}'`}</Codigo>
        <p className="text-xs text-gray-500">
          O exemplo soma, por operadora, os acessos nos municípios do Espírito Santo (<code>acessos_municipio</code>: uma linha por município e operadora). A resposta traz o
          snapshot (<code>snapshot_date</code>) e o mês de referência do SICI (<code>mes_referencia</code>), e o resultado muda só quando um novo snapshot é publicado.
          Não use <code>operadoras</code> com <code>uf_sede</code> para isto: ela filtra pela UF da sede da empresa, não pela de seus clientes.
        </p>
        <p className="text-xs text-gray-500">Os campos de cada coleção estão em <a className="text-primario-600 hover:underline" href="/api/v1/schema">/api/v1/schema</a>. Contatos (e-mail e telefone) não são servidos pela API pública. Os limites de uso estão no quadro acima e em <a className="text-primario-600 hover:underline" href="/api/v1/limites">/api/v1/limites</a>.</p>
      </section>

      <section aria-labelledby="mcp" className="space-y-3">
        <h2 id="mcp" className="text-titulo-3 text-gray-800">Servidor MCP</h2>
        <p className="text-sm text-gray-600">O servidor MCP (Model Context Protocol, transporte Streamable HTTP) expõe consultas, buscas por entidade e receitas prontas para assistentes de IA.
          Endereço: <code className="bg-gray-100 px-1 rounded">{origem}/mcp</code>.</p>
        <Codigo rotulo="Exemplo: adicionar ao Claude Code">{`claude mcp add --transport http ${SITE.mcp} ${origem}/mcp${comChave ? ' --header "Authorization: Bearer SUA_CHAVE"' : ''}`}</Codigo>
        <Codigo rotulo="Exemplo: configuração JSON de um cliente MCP">{`{
  "mcpServers": {
    "${SITE.mcp}": {
      "type": "http",
      "url": "${origem}/mcp"${comChave ? `,
      "headers": { "Authorization": "Bearer SUA_CHAVE" }` : ''}
    }
  }
}`}</Codigo>
        {comChave && <p className="text-xs text-gray-500">Sem o cabeçalho, o servidor responde em prévia. Troque <code>SUA_CHAVE</code> pela chave gerada no perfil.</p>}
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
