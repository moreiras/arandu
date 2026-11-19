<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Geolocalização dos prefixos do Registro.br (DB-IP City Lite)

`prefix_geo` · tipo **derivada** · ativa

Geolocaliza o primeiro endereço de cada prefixo alocado ao BR (≈ 22 mil) com o DB-IP City Lite local (baixado uma vez por mês).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.prefix_geo.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | mensal → mensal |
| Frescor máximo | 45d |
| Chaves | `prefixo`, `ponto`, `uf` |
| Entradas | `registro_br` |
| Amostra de teste | `tests/fixtures/raw/dbip/` |

## Origem e licença

- **URL:** https://download.db-ip.com/free/dbip-city-lite-{AAAA-MM}.mmdb.gz
- **Formato:** MMDB (DB-IP City Lite, mensal)
- **Licença:** CC BY 4.0 (DB-IP); dados do GeoNames sob CC BY
- **Uso comercial:** `permitido`
- **Termos:** https://db-ip.com/db/lite.php
- **Evidência / ressalvas:** Lido em 2026-10-31: "licensed under a Creative Commons Attribution 4.0 International License"; atribuição obrigatória, com link para db-ip.com nas páginas que exibem resultados da base ("IP Geolocation by DB-IP") e atribuição ao GeoNames. A cláusula que proíbe oferecer API de geolocalização vale só para a licença paga, mas o Arandurapé não expõe consulta por IP ou bloco. Sem chave de licença. Snapshot gerado com o GeoLite2 (MaxMind) guarda valores derivados dele.

## Saídas

- **Bruto (raw/):** `../dbip/dbip-city-lite-{AAAA-MM}.mmdb`
- **Normalizado (normalized/):** `summary/geo_prefixes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `prefixes[prefix].lat / lon` | float | Coordenadas do centroide da cidade que o DB-IP associa ao prefixo. | Sempre centroide de cidade. | asn_docs → asns/{asn}.json#geo_prefixes_v4; mapas_prefixos → maps/prefixes.geojson |
| `prefixes[prefix].city / country / uf` | str | Cidade, país e UF segundo o DB-IP (município derivado das coordenadas). | — | asn_docs → asns/{asn}.json#geo_prefixes_v4 |
| `prefixes[prefix].geo_confidence` | str | Sempre 'city_centroid'. | Geolocalização de IP é aproximada. | — |
| `prefixes[prefix].geo_source / mmdb_month` | str | Versão do banco usada (dbip-lite-AAAA-MM). | — | snapshot → manifest.json#geolite2_version |

## Limites

IP→local é estatístico: o provedor pode estar longe do cliente e o prefixo pode ser usado em várias cidades. Não é localização de usuário.

## Retenção

- **bruto:** 12 meses (alvo)
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `global_prefix_geo`
- **Produtos:** `asn_docs`, `mapas_prefixos`, `regiao_municipios`

## Pendências (nao_verificado)

- Exibir a atribuição 'IP Geolocation by DB-IP' (link para db-ip.com) onde a geolocalização aparecer (Fontes, mapas, página de prefixo).
