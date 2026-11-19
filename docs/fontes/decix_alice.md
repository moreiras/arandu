<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Route servers do DE-CIX Rio de Janeiro e São Paulo (Alice-LG, níveis 0, 1 e 3)

`decix_alice` · tipo **bruta** · ativa

Estado dos 8 route servers do DE-CIX no Brasil (Rio de Janeiro e São Paulo, rs1 e rs2, IPv6 e IPv4) e de cada sessão BGP dos membros, vistos pela API do Alice-LG do `lg.de-cix.net` (níveis 0 e 1, no mesmo esquema do `ixbr_alice`), e, em rodízio por vizinho, a leitura de `routes/received` (nível 3): total de rotas do vizinho e rotas lidas por ASN de origem. Base para os ASNs diretos e originadores do DE-CIX e para a comparação por cidade com o IX.br.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.decix_alice.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 10d |
| Chaves | `ixp`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/decix_alice/` |

## Origem e licença

- **URL:** https://lg.de-cix.net/api/v1/ (status, routeservers, routeservers/{id}/neighbors, routeservers/{id}/neighbors/{id}/routes/received)
- **Formato:** JSON (Alice-LG 6.2.0; os route servers são BIRD)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.de-cix.net/en/services/looking-glass
- **Evidência / ressalvas:** API pública do Looking Glass do DE-CIX. O `robots.txt` do lg.de-cix.net é `Disallow: /` (lido em 2026-11-06); a página do serviço diz "You can use the API in your own scripts" e o mantenedor liberou a coleta deste host (exceção documentada à regra do robots.txt, só para ele). Condições: User-Agent identificado (`arandurape/<versão> (+SITE_URL)`, `core/site.py`), uma requisição por vez, no mínimo 1 s entre requisições nos níveis 0 e 1 e **10 s no nível 3** (`ARANDU_DECIX_PAUSA_ROTAS_S`; a 28ª requisição a ~0,25 req/s levou 429), orçamento de 60 requisições por rodada diária (`ARANDU_DECIX_ORCAMENTO`), parada no primeiro sinal de bloqueio (HTTP 403 ou 429, conexão derrubada), com registro no documento e sem nova tentativa por 7 dias (só `--ignorar-bloqueio`). Se o DE-CIX pedir, a coleta para. Os "API Terms of Use" (PDF de 2020) não citam o Alice; se valessem, o dever de apagar dados a pedido conflita com snapshots imutáveis (pergunta jurídica em aberto). Só route servers de Rio e São Paulo; o resto do DE-CIX nunca é consultado. Escopo da página do serviço: GlobePEER.

## Saídas

- **Normalizado (normalized/):** `summary/decix_rs_sessions.json.gz`, `summary/decix_rs_rotas.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `rs[].estado_rotas` | str | Estado do cache de ROTAS do Alice para o route server (READY, BUSY ou ERROR), do `/status` (ligado pelo nome do RS); não diz nada das sessões. | A leitura de rotas usa o rs1 se o cache estiver READY, senão o rs2. | — |
| `rs[].vizinhos_em` | str | Instante em que o Alice atualizou o cache de vizinhos do route server (`cache_status.cached_at` da resposta do `neighbors`). | — | — |
| `sessoes[]` | list | Uma linha por sessão BGP no route server (ixp = decix-sp ou decix-rj, família, ASN, IP na LAN, estado, último erro, rotas recebidas, aceitas e filtradas, limite de importação) e o `id_vizinho` do Alice. | Sessão up no route server = o ASN faz peering multilateral naquele PTT; não diz nada de peering bilateral. O nome é o rótulo público do LG (organização, não pessoa). | — |
| `vizinhos[].origens` | dict | decix_rs_rotas: {ASN de origem (último do AS_PATH): nº de rotas lidas} do vizinho, nas páginas de `routes/received` lidas. | Um piso, não o conjunto: vizinho com mais de `paginas_max_vizinho` páginas de 250 rotas fica `completo: false`. O produto rotula o conjunto de originadores como parcial. | — |
| `vizinhos[].total` | int | Número de rotas recebidas do vizinho (`pagination.total_results` do Alice); `lidas` é quantas entraram na contagem de origens. | — | — |
| `vizinhos[].herdado` | bool | Verdadeiro se o vizinho não coube no orçamento desta rodada e vem da rodada anterior, com o `coletado_em` original (idade máxima 35 dias). | — | — |
| `cobertura_rodizio` | dict | `total` e `por_ptt`: vizinhos elegíveis, lidos na rodada, herdados, sem leitura e idade máxima da leitura em dias. | — | — |
| `bloqueio` | dict | Presente quando o servidor respondeu 403/429 ou derrubou a conexão: instante, motivo e caminho. A coleta parou na hora e não tenta de novo por 7 dias. | — | — |

## Limites

Sessão up não é tráfego nem relação comercial. O bruto não é guardado (derivados apenas). A leitura de rotas é por vizinho em rodízio e limitada a `ARANDU_DECIX_PAGINAS_MAX` páginas (padrão 8, 2.000 rotas): vizinho de centenas de milhares de rotas (medido em 2026-11-10: um vizinho do Rio rs1 IPv4 tem 100.072 de 104.058 rotas importadas) fica parcial. Sem o `config` do Alice (as communities do DE-CIX não são decodificadas). O cache de rotas do Alice pode estar atrasado (a base da busca global tem até 30 minutos de defasagem, segundo a página do serviço).

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `decix_rs`

## Pendências (nao_verificado)

- Termos de uso: o DE-CIX não declara limite de taxa; PDF "API Terms of Use" (2020) e termos locais (BR) não valem ou não foram lidos.
- Medir quantas requisições e quantos dias o rodízio leva para ler todos os vizinhos de Rio e São Paulo (8 páginas por vizinho no máximo).
