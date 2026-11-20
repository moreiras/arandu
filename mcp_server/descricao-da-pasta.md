# mcp_server/ — servidor MCP (Model Context Protocol)

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Expõe os snapshots publicados a assistentes de IA (Streamable HTTP, porta 8001, `/mcp`). Usa o mesmo `Store` e os mesmos serviços
da API (`api/`): não há lógica de dados própria aqui, só a forma das tools. Sem chave o MCP entrega a mesma prévia que o site sem
login; com a chave da conta (`Authorization: Bearer <esquema>_mcp_…`), o nível de usuário. Contatos e dados de pessoa física nunca
saem pelo MCP.

## Arquivos

| Arquivo | Papel |
|---|---|
| `app.py` | Aplicação: monta o servidor, registra as tools, resources e prompts e aplica as descrições curtas de `descricoes.py`. |
| `contexto.py` | Contexto comum: o objeto `mcp`, o `Store` do processo, a resolução de data e os auxiliares das tools de visualização. |
| `chave.py` | Autenticação por chave de MCP (nível *user*), verificada pela API. |
| `previa.py` | Prévia sem chave, equivalente à do site sem login. |
| `entrada.py` | Entrada e saída das tools: aceita as formas que os modelos mandam de fato (texto "null", listas como texto, UF no nome) e nunca falha em silêncio. |
| `nomes.py` | Nomes das tools por domínio (`asn_`, `ixp_`, `rota_`, `operadora_`…) e aliases ocultos dos nomes antigos. |
| `descricoes.py` | Descrições curtas das tools, no formato "use para / não use para", que é o que o modelo lê em `tools/list`. |
| `guia.py` | Tabela tarefa → tool que gera as instruções do servidor e o bloco `tarefas` do `describe_schema`. |
| `instrucoes.py` | Texto enviado ao cliente no `initialize` (campo `instructions`). |
| `recursos.py` | Resources (visão geral, glossário, resumo, schema, receitas) e prompts. |
| `capacidades.py` | Tools geradas das capacidades declaradas em `serve/capabilities/*.yaml`. |
| `consolidadas.py` | Tools consolidadas: uma por assunto, com o recorte escolhido por argumento. |

## Tools por assunto

| Arquivo | Tools |
|---|---|
| `tools_entidades.py` | Snapshots, ASNs, IXPs, PTTs externos, CDNs e prefixos. |
| `tools_consulta.py` | `describe_schema`, `query`, consultas em lote, resolvedores (operadora, lugar) e analíticos de PTT. |
| `tools_mercado.py` | Perfis consolidados de operadora, município e UF; acessos do SICI. |
| `tools_grupo.py` | Grupo econômico (mercado, regulatório e técnico). |
| `tools_historico.py` | Evolução no tempo e o que mudou entre snapshots (`data/history/`). |
| `tools_bgp.py` | Análise de roteamento, estabilidade BGP e RPKI. |
| `tools_politica.py` | Política de roteamento nos route servers do IX.br: rejeições e communities. |
| `tools_interconexao.py` | O que os dados públicos mostram sobre a interconexão de um AS. |
| `tools_instalacoes.py` | Instalações do PeeringDB e portas nos PTTs. |
| `tools_bloqueios.py` | Bloqueios medidos pelo OONI. |
| `tools_radar.py` | Cloudflare Radar por ASN e por UF. |
| `tools_exposicao.py` | Exposição de serviços por ASN e por UF. |
| `tools_contratos.py` | Contratos públicos de operadoras. |
| `tools_financiamento.py` | Crédito público (BNDES) e sanções (CEIS e CNEP). |
| `tools_infra.py` | Infraestrutura física perto de um ponto (resumo das camadas do mapa). |
| `tools_visualizacao.py` | Blobs GeoJSON e Hilbert (avançadas): resumo por padrão, `full=true` sob demanda. |

Tool nova: nome de domínio em `nomes.py`, linha em `guia.py`, descrição em `descricoes.py` e chamada de exemplo no contrato do T5
(`tests/products/mcp_contract.py`); ver `AGENTS.md`, seção "Como testar".
