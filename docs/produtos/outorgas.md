<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Outorgas Anatel (SCM, SMP, STFC, SeAC) e mapas

`outorgas` · produto

Quatro arquivos de outorgas, cada um com lista, índice por CNPJ, vínculo CNPJ↔ASN, bloco SICI resumido e coordenadas; mais os mapas GeoJSON.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `publish.snapshot_builder` |
| Chaves de junção | `cnpj`, `asn`, `uf`, `ibge` |
| Cenários de teste (dataset sintético) | `scm_sem_sici`, `cnpj_dois_asns`, `contatos_fora_do_published` |

## Entradas

- fonte [anatel_scm](../fontes/anatel_scm.md) — uso comercial: `permitido`
- fonte [anatel_seac](../fontes/anatel_seac.md) — uso comercial: `permitido`
- fonte [anatel_smp](../fontes/anatel_smp.md) — uso comercial: `permitido`
- fonte [anatel_stfc](../fontes/anatel_stfc.md) — uso comercial: `permitido`
- fonte [scm_geo](../fontes/scm_geo.md) — uso comercial: `restrito`
- fonte [seac_geo](../fontes/seac_geo.md) — uso comercial: `restrito`
- fonte [smp_geo](../fontes/smp_geo.md) — uso comercial: `restrito`
- fonte [stfc_geo](../fontes/stfc_geo.md) — uso comercial: `restrito`
- fonte [registro_br](../fontes/registro_br.md) — uso comercial: `nao_verificado`
- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `scm.json.gz`, `seac.json.gz`, `smp.json.gz`, `stfc.json.gz`, `maps/scms.geojson`, `maps/seacs.geojson`, `maps/smps.geojson`, `maps/stfcs.geojson`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `scms[].asns` | list[int] | ASNs vinculados ao CNPJ pelo Registro.br. | — | outorgas → scm.json.gz#scms |
| `scms[].sici_ativo / sici_mes_referencia / sici_acessos / sici_pf / sici_pj` | bool\|str\|int | Resumo do SICI do CNPJ copiado para a outorga. | Sem soma por ASN; um CNPJ com vários ASNs não deve ser somado duas vezes. | outorgas → scm.json.gz#scms |
| `scms[].sici_municipios / sici_capacidade_mbps / sici_tecnologia / sici_empresa` | int\|float\|str | Municípios atendidos, capacidade contratada, tecnologia predominante e nome no SICI. | — | outorgas → scm.json.gz#scms |
| `matched_asns / cnpj_to_asns` | int / dict | Quantidade de CNPJs ligados a ASN e o mapa CNPJ→ASNs. | — | outorgas → scm.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → scm.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → scm.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → scm.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → scm.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → scm.json.gz#matched_asns |
| `scms` | list[dict] | Registros de outorga SCM (um por CNPJ/endereço). | — | outorgas → scm.json.gz#scms |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → scm.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → scm.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → seac.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → seac.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → seac.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → seac.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → seac.json.gz#matched_asns |
| `seacs` | list[dict] | Registros de outorga SeAC. | — | outorgas → seac.json.gz#seacs |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → seac.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → seac.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → smp.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → smp.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → smp.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → smp.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → smp.json.gz#matched_asns |
| `smps` | list[dict] | Registros de outorga SMP. | — | outorgas → smp.json.gz#smps |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → smp.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → smp.json.gz#cnpj_to_asns |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → stfc.json.gz#snapshot_date |
| `generated_at` | str | Instante UTC em que o arquivo foi gerado. | — | outorgas → stfc.json.gz#generated_at |
| `total` | int | Quantidade de registros de outorga. | — | outorgas → stfc.json.gz#total |
| `unique_cnpjs` | int | CNPJs distintos. | — | outorgas → stfc.json.gz#unique_cnpjs |
| `matched_asns` | int | CNPJs com ASN vinculado. | — | outorgas → stfc.json.gz#matched_asns |
| `stfcs` | list[dict] | Registros de outorga STFC. | — | outorgas → stfc.json.gz#stfcs |
| `by_cnpj` | dict | Índice CNPJ → registros de outorga. | — | outorgas → stfc.json.gz#by_cnpj |
| `cnpj_to_asns` | dict | CNPJ → ASNs do Registro.br. | — | outorgas → stfc.json.gz#cnpj_to_asns |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/scms.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/scms.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga SCM geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/scms.geojson#features |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/seacs.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/seacs.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga SeAC geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/seacs.geojson#features |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/smps.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/smps.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga SMP geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/smps.geojson#features |
| `type` | str | Tipo GeoJSON. | — | outorgas → maps/stfcs.geojson#type |
| `snapshot_date` | str | Data do snapshot (AAAA-MM-DD) a que o arquivo pertence. | — | outorgas → maps/stfcs.geojson#snapshot_date |
| `features` | list | Um ponto por CNPJ com outorga STFC geolocalizado (properties: cnpj, razao_social, municipio, uf, asns, has_asn, geo_confidence; SCM acrescenta sici_*). | — | outorgas → maps/stfcs.geojson#features |

## Limites

Uma outorga por (CNPJ, serviço, endereço): CNPJ pode aparecer várias vezes. E-mail/telefone presentes no arquivo e removidos das rotas públicas.
