<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Área de influência observada dos PTTs do IX.br

`area_influencia_ptt` · produto

Por PTT e em quatro visões (influência provável e alcance, cada uma para só os ASNs diretamente conectados ou para todos os que anunciam prefixo próprio no PTT), a que distância atuam as operadoras que aparecem nele, medida pelos acessos de banda larga fixa do SICI por município. Traz P50, P80 e P90 da distância ponderada por acessos, a mediana por operadora, as faixas por município e o PTT principal de cada município. Inferência, não cobertura de rede.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.area_influencia_ptt.build` |
| Chaves de junção | `ibge`, `asn`, `cnpj`, `ixp` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`
- fonte [lg_ixbr](../fontes/lg_ixbr.md) — uso comercial: `nao_verificado`
- fonte [curada_pix](../fontes/curada_pix.md) — uso comercial: `nao_verificado`
- fonte [ibge_malha_municipal](../fontes/ibge_malha_municipal.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `territorio/area_influencia_ptt.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ptts[code].visoes[diretos|todos|alcance_diretos|alcance_todos]` | dict | Operadoras (CNPJs), municípios e acessos atribuídos ao PTT; P50, P80 e P90 da distância em km (peso por acessos); mediana por operadora (cada operadora conta 1); municípios e acessos por faixa; e, por município, os acessos atribuídos e a faixa (1 até o P50, 2 até o P80, 3 além). `null` quando nenhuma operadora é atribuída ao PTT na visão. As visões `alcance_*` valem só por PTT (não entram em `municipios` nem em `totais`). | INFERIDO. Em `diretos` e `todos`, os acessos de cada par (município, CNPJ) vão para o PTT mais próximo entre os que o CNPJ enxerga na visão (união dos PTTs dos ASNs ligados ao CNPJ pelo SICI); cada acesso conta uma vez, mesmo num CNPJ com vários ASNs. Linha reta do centroide do município ao PIX mais próximo. Sem exclusão de operadoras. Em `alcance_diretos` e `alcance_todos` (mesma participação de `diretos` e `todos`) não há disputa, e todo par (município, CNPJ) cuja operadora está no PTT entra no alcance dele, mesmo com outro PTT mais próximo, e um município pode estar no alcance de vários PTTs (os acessos contam em cada um, sem somar entre PTTs); percentis e faixas pesam pelos acessos do alcance total. Nenhum nome de operadora é publicado, só contagens. | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#ptts |
| `ptts[code].pix` | dict | Quantos PIX do PTT têm coordenada no cadastro, quantos foram posicionados no centroide do município do endereço e quantos no da sede, se o posicionamento é aproximado, e os pontos usados no cálculo. | PIX sem coordenada em `config/pix.yaml` vai para o centroide do município do endereço; sem endereço reconhecível, para o da sede do PTT. PTT sem PIX no cadastro usa a sede. | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#ptts |
| `municipios[diretos|todos][ibge]` | list | [PTT principal, faixa nesse PTT, acessos atribuídos ao principal, acessos atribuídos no município, nº de PTTs que recebem acessos do município]. Principal é o PTT com mais acessos do município. | INFERIDO. Município sem operadora atribuída a PTT na visão não consta. | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#municipios |
| `municipios_nomes[ibge]` | str | "Nome/UF" dos municípios que aparecem nas listas, para a tabela de alternativa textual ao mapa. | — | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#municipios_nomes |
| `totais[diretos|todos]` | dict | Acessos do SICI no país, atribuídos a algum PTT, sem PTT visível para a operadora e em município sem centroide; CNPJs com mais de um ASN. | — | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#totais |
| `ptts_com_pix_aproximado / faixas / metodo / limites / fontes / natureza / snapshot_date / generated_at` | list / dict / str | PTTs com algum PIX posicionado por centroide, definição das faixas, método em texto, limites, o mês do SICI e o rótulo de natureza. | — | area_influencia_ptt → territorio/area_influencia_ptt.json.gz#ptts_com_pix_aproximado; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#faixas; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#metodo; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#limites; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#fontes; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#natureza; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#snapshot_date; area_influencia_ptt → territorio/area_influencia_ptt.json.gz#generated_at |

## Limites

Mostra onde as operadoras que aparecem no PTT declaram acessos ao SICI, não onde a rede delas chega nem por onde passa o tráfego. O mês do SICI difere da data do snapshot. O vínculo CNPJ ↔ ASN é o do SICI (registro do ASN); operadora sem ASN ligado fica de fora. Distância em linha reta, sem considerar rodovias ou fibra.
