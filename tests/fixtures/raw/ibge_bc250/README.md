# ibge_bc250 — BC250 `rod_trecho_rodoviario_l` (shapefile)
Origem: https://geoftp.ibge.gov.br/…/bc_250_shapefiles_2026_03_03.zip (761 MB; o coletor lê 3 membros por HTTP Range).
Os 3 arquivos (.shp/.shx/.dbf) são um shapefile **binário válido** gerado por `cut_fixtures.py` com 3 trechos reais
de `normalized/2026-09-20/summary/ibge_rodovias.json.gz` (PolyLine, campos dBASE de 10 caracteres como o IBGE).
Os testes os empacotam em um ZIP servido com suporte a `Range`.
