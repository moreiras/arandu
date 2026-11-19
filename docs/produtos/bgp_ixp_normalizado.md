<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Tabelas BGP normalizadas por IXP

`bgp_ixp_normalizado` · produto

Parser do texto bruto dos Looking Glasses: rotas, conjunto de prefixos, prefixos por origem e relações (diretos, originadores, stubs) de cada IXP.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.bgp_routes.build` |
| Chaves de junção | `ixp`, `asn`, `prefixo` |
| Cenários de teste (dataset sintético) | `ptt_coleta_parcial` |

## Entradas

- fonte [lg_ixbr](../fontes/lg_ixbr.md) — uso comercial: `nao_verificado`

## Saídas

- **Normalizado:** `{ixp}/routes-{afi}.json.gz`, `{ixp}/prefix-set-{afi}.json.gz`, `{ixp}/origin-prefixes-{afi}.json.gz`, `{ixp}/peers-{afi}.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `peers-{afi}.json.gz` | dict | Por peer direto (primeiro AS do AS-PATH): prefixos próprios e de terceiros, ASNs originadores distintos e espaço em /48 (v6) ou /24 (v4). Calculado pela etapa bgp_ixp (core/ixp_peers.py) para a API não reler as rotas do PTT inteiro (1.4.2.1). | — | — |
| `routes[].prefix / status / aspath / origin / nexthop` | dict | Rota vista no Route Server: prefixo, status BGP, AS-PATH, origem e next-hop. | — | — |
| `relationships.asn_direct` | list[int] | ASNs com sessão BGP direta com o Route Server (primeiro AS do AS-PATH). | Definição de 'direto' do glossário do MCP. | — |
| `relationships.asn_origin` | list[int] | ASNs que aparecem como origem de rotas no IXP (inclui os alcançados por terceiros). | 'Originador' ≠ presente fisicamente. | — |
| `relationships.asn_stub` | list[int] | ASNs diretos que só originam o próprio espaço (sem trânsito). | Inferido do AS-PATH. | — |

## Limites

Depende do formato textual do firmware do LG; falha de um IXP não derruba os demais.
