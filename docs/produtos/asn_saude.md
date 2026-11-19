<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Saúde do ASN: RPKI e alertas

`asn_saude` · produto

Fragmento gravado dentro de asns/{asn}.json depois do RPKI: ROAs que cobrem o AS, validação por prefixo, objetos ASPA e alertas. Roda depois do índice de ASNs porque usa os VRPs do snapshot e o índice publicado.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder (--asn-health-only); api/asn_health.py` |
| Chaves de junção | `asn`, `prefixo` |
| Cenários de teste (dataset sintético) | `rpki_invalido_moas`, `mudanca_de_origem` |

## Entradas

- produto [asn_docs](asn_docs.md)
- fonte [rpki_collector](../fontes/rpki_collector.md) — uso comercial: `nao_verificado`
- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `asns/{asn}.json`
- **Fragmentos:** `asn.saude (alerts, roa_list, rpki_validation, aspa_providers, aspa_customers)`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `roa_list` | list[dict] | VRPs que cobrem os prefixos do AS. | — | asn_saude → asns/{asn}.json#roa_list |
| `rpki_validation[prefix]` | str | Estado RPKI do prefixo anunciado: valid, invalid ou not_found. | Calculado no pipeline (etapa saude_asn) contra os VRPs do snapshot. | asn_saude → asns/{asn}.json#rpki_validation |
| `alerts[].id / category / severity / title / detail / refs` | dict | Achados de saúde do AS (presença, roteamento, RPKI, redundância). | Regras de api/asn_health; achado negativo é observação, não prova. | asn_saude → asns/{asn}.json#alerts |
| `aspa_providers` | list[int] | Provedores autorizados pelo objeto ASPA do próprio AS (RPKI). | — | asn_saude → asns/{asn}.json#aspa_providers |
| `aspa_customers` | list[int] | ASNs que declaram este AS como provedor em seus objetos ASPA. | — | asn_saude → asns/{asn}.json#aspa_customers |

## Limites

Não fatal: se falhar, a API calcula sob demanda (memoizado). O arquivo asns/{asn}.json é reescrito no lugar (única exceção ao 'escrito uma vez').
