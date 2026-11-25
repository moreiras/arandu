<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Geolocalização das outorgas SEAC (Nominatim)

`seac_geo` · tipo **derivada** · ativa

Geocodifica o endereço da sede de cada outorga SEAC (endereço completo → CEP → município) com cache persistente em geo_cache/seac.json.gz, adicionando lat/lon e rótulo de confiança.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.seac_geo.enrich` |
| Publicável | sim (exposição: aberta) |
| Decisão sobre a exposição | Aberta por decisão do projeto (D9, 2026-11-24): o que a fonte alimenta é servido sem login na interface, na API e no MCP, salvo o que está dito a seguir, e a abertura é intencional, não um padrão esquecido. Posição geocodificada da sede das outorgas (endereço do cadastro da Anatel), com a licença ODbL 1.0 do OpenStreetMap; a atribuição é obrigatória. |
| Atribuição exigida | Endereços das outorgas: Anatel, dados abertos. Geocodificação: © colaboradores do OpenStreetMap, ODbL 1.0 (Nominatim). |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `cnpj`, `ponto`, `ibge` |
| Entradas | `anatel_seac` |
| Amostra de teste | `tests/fixtures/raw/nominatim/` |

## Origem e licença

- **URL:** https://nominatim.openstreetmap.org/search
- **Formato:** JSON (geocodificação)
- **Licença:** ODbL 1.0 (dados OpenStreetMap)
- **Uso comercial:** `restrito`
- **Termos:** https://operations.osmfoundation.org/policies/nominatim/
- **Evidência / ressalvas:** Política de uso do Nominatim público (verificada em 2026-10-13): máximo absoluto de 1 req/s, User-Agent identificado, atribuição visível; dados sob ODbL com share-alike (extrações pequenas tendem a ser uso justo). O código aceita NOMINATIM_URL para instância própria (padrão de localhost:8088).

## Saídas

- **Normalizado (normalized/):** `summary/anatel_seac_geo.json.gz`, `../geo_cache/seac.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `lat / lon` | float | Coordenadas geocodificadas do endereço da sede. | Posição do endereço (ou centroide), não da área de cobertura. | outorgas → maps/seacs.geojson |
| `geo_confidence` | str | Confiança da geocodificação: exact_address, cep_centroid, city_centroid ou unknown. | Rótulo do método; não é erro em metros. | — |
| `geo_source` | str | Origem da coordenada (nominatim ou cache). | — | outorgas → maps/seacs.geojson |
| `geolocated / cached / unknown` | int | Contagens do lote: geocodificados, vindos do cache e sem resultado. | — | — |

## Limites

Geocodificação best-effort por texto de endereço: endereços ambíguos caem em centroide de CEP/município; 'unknown' não entra no mapa.

## Retenção

- **normalizado:** 52 semanas; cache permanente

## Quem usa

- **Produtos:** `outorgas`

## Pendências (nao_verificado)

- Confirmar atribuição OSM/ODbL na interface e se o resultado geocodificado publicado é obra derivada com share-alike; avaliar instância própria do Nominatim.
