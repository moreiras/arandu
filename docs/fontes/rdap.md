<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Organizações BR a partir do Registro.br (ASN→nome/CNPJ)

`rdap` · tipo **derivada** · ativa

Reduz registro_br a um mapeamento compacto {asn: {name, cnpj}} usado pelas geocodificações e pelos produtos. Sem consulta externa (apesar do nome).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.rdap.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `cnpj` |
| Entradas | `registro_br` |
| Amostra de teste | `tests/fixtures/raw/registro_br/` |

## Saídas

- **Normalizado (normalized/):** `summary/orgs.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `orgs[asn].name` | str | Nome da organização titular do ASN no whois do NIC.br. | — | asn_docs → asns/{asn}.json#name |
| `orgs[asn].cnpj` | str | CNPJ da organização. | — | asn_docs → asns/{asn}.json#cnpj |
| `total / with_cnpj` | int | ASNs no mapeamento e quantos têm CNPJ. | — | — |

## Limites

Não consulta RDAP: o nome do módulo é histórico.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `cnpj_geo`, `rdap_contatos`, `shodan_exposicao`
- **Produtos:** `asn_docs`
