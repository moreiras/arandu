<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Geolocalização de ASNs internacionais (PeeringDB org + Nominatim)

`peeringdb_intl_geo` · tipo **derivada** · ativa

Posição de ASNs não brasileiros: coordenadas da organização no PeeringDB (org_coords) ou centroide da cidade via Nominatim.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.peeringdb_intl_geo.enrich` |
| Publicável | sim (exposição: aberta) |
| Decisão sobre a exposição | Aberta por decisão do projeto (D9, 2026-11-24; PTT externo revisto em 2026-11-25): o que a fonte alimenta é servido sem login na interface, na API e no MCP, e a abertura é intencional, não um padrão esquecido. Mistura OpenStreetMap (ODbL 1.0, via Nominatim) e coordenadas de organização do PeeringDB; o projeto publica só a posição por ASN, sem contatos. |
| Atribuição exigida | Fonte: PeeringDB. Geocodificação: © colaboradores do OpenStreetMap, ODbL 1.0 (Nominatim). |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn`, `pais`, `ponto` |
| Entradas | `ixbr_api`, `peeringdb_networks` |
| Amostra de teste | `tests/fixtures/raw/nominatim/` |

## Origem e licença

- **URL:** https://nominatim.openstreetmap.org/search
- **Formato:** JSON (geocodificação)
- **Licença:** ODbL 1.0 (dados OpenStreetMap)
- **Uso comercial:** `restrito`
- **Termos:** https://operations.osmfoundation.org/policies/nominatim/
- **Evidência / ressalvas:** Política de uso do Nominatim público (verificada em 2026-10-13): máximo absoluto de 1 req/s, User-Agent identificado, atribuição visível; dados sob ODbL com share-alike (extrações pequenas tendem a ser uso justo). O código aceita NOMINATIM_URL para instância própria (padrão de localhost:8088).

## Saídas

- **Normalizado (normalized/):** `summary/geo_intl_asns.json.gz`, `../geo_cache/peeringdb_intl.json.gz`, `../geo_cache/peeringdb_intl_nom.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].name / city / country` | str | Nome da organização, cidade e país no PeeringDB. | — | asn_docs → asns/{asn}.json#geo_org |
| `asns[asn].lat / lon` | float | Coordenadas da organização (PeeringDB) ou da cidade (Nominatim); nulas quando desconhecidas. | — | mapas_prefixos → maps/asns.geojson |
| `asns[asn].geo_confidence` | str | org_coords, city_centroid ou unknown. | Rótulo do método. | — |

## Limites

Posição da sede/organização, não da rede; ~288 ASNs internacionais no snapshot de 2026-10-11, vários 'unknown'.

## Retenção

- **normalizado:** 52 semanas; cache permanente

## Quem usa

- **Produtos:** `asn_docs`, `mapas_prefixos`

## Pendências (nao_verificado)

- Confirmar atribuição OSM/ODbL na interface e se o resultado geocodificado publicado é obra derivada com share-alike; avaliar instância própria do Nominatim.
- Uso do PeeringDB (org/net) segue a AUP descrita em peeringdb_networks (restrito).
