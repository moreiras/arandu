<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# VRPs e ASPA publicados (cópia direta do coletor)

`rpki` · produto

O coletor grava em published/ diretamente; este produto só registra a saída para o grafo (sem build próprio).

## Resumo

| | |
|---|---|
| Módulo (hoje) | `sources.rpki_collector.collect` |
| Chaves de junção | `asn`, `prefixo` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [rpki_collector](../fontes/rpki_collector.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `rpki/vrp_list.json.gz`, `rpki/aspa_list.json.gz`

## Dicionário de campos

_Sem dicionário de campos declarado._

## Limites

Ver rpki_collector.
