<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# ASNs delegados ao Brasil (LACNIC delegated-extended)

`lacnic_delegated` · tipo **bruta** · ativa

Arquivo de estatísticas de delegação do LACNIC, filtrado para ASNs com country=BR (status allocated/assigned). Fonte autoritativa de 'quais ASNs são brasileiros'.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.lacnic_delegated.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `pais` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/lacnic_delegated/` |

## Origem e licença

- **URL:** https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest
- **Formato:** texto delimitado por | (RIR Statistics Exchange Format)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** README do diretório (2026-10-13) não declara termos; formato descrito em RIR-Statistics-Exchange-Format.txt. Arquivo público do LACNIC.

## Saídas

- **Bruto (raw/):** `summary/delegated-lacnic-extended-{as_of}.txt.gz`, `summary/delegated-lacnic-extended-{as_of}.txt`
- **Normalizado (normalized/):** `summary/lacnic_delegated.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `br_asns` | list[int] | ASNs com country=BR e status allocated ou assigned no LACNIC. | 'assigned' incluído para capturar transferências. | asn_docs → asns/{asn}.json#is_br |
| `total_br_asns` | int | Quantidade de ASNs brasileiros. | Base do universo de consulta do peeringdb_networks. | — |
| `source_sha256` | str | SHA-256 do arquivo bruto. | — | — |

## Limites

Reflete a delegação inicial/RIR; ASN transferido a outra economia pode demorar a refletir. Não inclui transferências inter-RIR detalhadas.

## Retenção

- **bruto:** 90 dias (alvo)
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `ipv4_delegated`, `peeringdb_networks`
- **Produtos:** `asn_docs`, `ixp_docs`

## Pendências (nao_verificado)

- Termos de uso das estatísticas do LACNIC não localizados.
