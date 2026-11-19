# dbip — DB-IP City Lite (mmdb) — SINTÉTICO
O banco real (~120 MB, CC BY 4.0, https://db-ip.com/db/download/ip-to-city-lite) é baixado sem chave. Esta amostra é um
**MMDB binário válido gerado por `cut_fixtures.py`** (biblioteca `mmdb-writer`) com o esquema do DB-IP: estado só pelo nome
(`subdivisions[].names.en`, sem `iso_code`), cidade só em inglês, bairro no lugar da cidade e coordenadas públicas de centros de
cidades; não contém registros do DB-IP. Redes: 200.160.0.0/20 (Pinheiros, São Paulo), 200.192.0.0/18 (Rio), 177.129.168.0/22
(sem cidade), 201.6.0.0/16 (sem coordenadas), 2804:8f8::/32 (Curitiba), 8.8.8.0/24 (EUA).
