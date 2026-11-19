<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Presença de CDNs nos IXPs

`cdns` · produto

Cruza a lista curada de CDNs com a presença dos ASNs em IXPs do IX.br e externos.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `asn`, `ixp` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [curada_cdns](../fontes/curada_cdns.md) — uso comercial: `nao_verificado`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `cdns.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cdns[].ixbr / external` | list[str] | IXPs do IX.br e externos em que algum ASN do CDN está presente. | — | cdns → cdns.json#cdns |
| `cdns[].ixbr_count / external_count` | int | Quantidade de IXPs de cada tipo. | — | cdns → cdns.json#cdns |
| `ixbr_columns / external_columns` | list[dict] | Colunas da matriz: IXP e quantos CDNs estão presentes. | — | cdns → cdns.json#ixbr_columns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | cdns → cdns.json#snapshot_date |
| `external_columns` | list[dict] | Colunas da matriz para IXPs externos: código, nome e CDNs presentes. | — | cdns → cdns.json#external_columns |

## Limites

Presença = qualquer ASN do grupo; lista de CDNs curada e incompleta.
