<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Mapas de prefixos, ASNs e curvas de Hilbert

`mapas_prefixos` · produto

GeoJSON de prefixos BR, prefixos globais vistos nos IXPs e ASNs geolocalizados; mapas de ocupação do espaço IPv6/IPv4 (curva de Hilbert).

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `prefixo`, `asn`, `ponto` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [prefix_geo](../fontes/prefix_geo.md) — uso comercial: `permitido`
- fonte [global_prefix_geo](../fontes/global_prefix_geo.md) — uso comercial: `permitido`
- fonte [cnpj_geo](../fontes/cnpj_geo.md) — uso comercial: `nao_verificado`
- fonte [peeringdb_intl_geo](../fontes/peeringdb_intl_geo.md) — uso comercial: `restrito`
- fonte [fulltable_routeviews](../fontes/fulltable_routeviews.md) — uso comercial: `nao_verificado`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- produto [bgp_ixp_normalizado](bgp_ixp_normalizado.md)
- fonte [curada_pix](../fontes/curada_pix.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `maps/prefixes.geojson`, `maps/global_prefixes.geojson`, `maps/global_prefixes.col`, `maps/asns.geojson`, `hilbert_v6.json`, `hilbert_v4.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `legacy` | dict | Bloco LEGACY do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#legacy |
| `lacnic` | dict | Bloco LACNIC do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#lacnic |
| `arin` | dict | Bloco ARIN do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#arin |
| `ripe` | dict | Bloco RIPE do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#ripe |
| `apnic` | dict | Bloco APNIC do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#apnic |
| `afrinic` | dict | Bloco AFRINIC do IPv6: camadas por célula /32 (rir_br, global_br, global_all, ixp_all, rir_br_visible; índices esparsos). | — | mapas_prefixos → hilbert_v6.json#afrinic |
| `hilbert_v4.rir_br / global_br / global_all / ixp_all / rir_br_visible` | list[int] | Células de 65.536 posições da curva de Hilbert sobre o IPv4: ocupação alocada ao BR, anunciada, global, vista em IXP e BR visível. | Contagens por célula (/16 agregado). | mapas_prefixos → hilbert_v4.json |
| `rir_br` | list[int] | Por célula /16: espaço alocado ao BR pelo Registro.br. | — | mapas_prefixos → hilbert_v4.json#rir_br |
| `global_br` | list[int] | Por célula /16: espaço BR anunciado na tabela global. | — | mapas_prefixos → hilbert_v4.json#global_br |
| `global_all` | list[int] | Por célula /16: espaço anunciado na tabela global (todos os países). | — | mapas_prefixos → hilbert_v4.json#global_all |
| `ixp_all` | list[int] | Por célula /16: espaço visto nos IXPs. | — | mapas_prefixos → hilbert_v4.json#ixp_all |
| `rir_br_visible` | list[int] | Por célula /16: espaço alocado ao BR que é visível (anunciado) na tabela global. | — | mapas_prefixos → hilbert_v4.json#rir_br_visible |
| `type` | str | Tipo GeoJSON (FeatureCollection). | — | mapas_prefixos → maps/asns.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_prefixos → maps/asns.geojson#snapshot_date |
| `features` | list | Um ponto por ASN geolocalizado (properties: asn, name, cnpj, razao_social, uf, city, geo_confidence). | — | mapas_prefixos → maps/asns.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_prefixos → maps/prefixes.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_prefixos → maps/prefixes.geojson#snapshot_date |
| `features` | list | Um ponto por prefixo BR geolocalizado (properties: prefix, ip_version, origin_asn, city, uf, geo_confidence). | — | mapas_prefixos → maps/prefixes.geojson#features |
| `type` | str | Tipo GeoJSON. | — | mapas_prefixos → maps/global_prefixes.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | mapas_prefixos → maps/global_prefixes.geojson#snapshot_date |
| `features` | list | Um ponto por prefixo visto nos IXPs (properties: prefix, origin_asn, ixps_seen, city, uf, geo_confidence). | — | mapas_prefixos → maps/global_prefixes.geojson#features |

## Limites

Localização por IP (DB-IP) é centroide de cidade; ASN geolocalizado = sede da organização.
