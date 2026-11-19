# core/ — núcleo compartilhado

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Código usado por mais de uma camada (coleta, produtos, publicação, API, MCP). Não importa `api`, `mcp_server` nem `products`: as
regras de camada estão em `.importlinter` e a ligação por referência entre camadas em `plugins.py`.

## Infraestrutura

| Arquivo | Papel |
|---|---|
| `common.py` | Utilitários de todo o pipeline: caminhos de `data/`, logging, YAML, JSON gzip, `app_version()` (lê `VERSION`) e o bruto do LG por data de origem (`raw_bgp_ixp`). |
| `site.py` | Identidade pública do site (nome, URL, esquema de URI do MCP, prefixo dos arquivos baixados, endereço do código-fonte), lida do `.env`; `com_identidade` troca o marcador "Arandurapé" na saída. |
| `telnet.py` | Cliente Telnet assíncrono dos looking glasses do IX.br. |
| `layout.py` | Leitura de `published/<data>/` nos dois formatos (`layout_version` 1 e 2, compactado). |
| `integridade.py` | Checksums dos artefatos publicados: o manifesto cobre tudo o que está em `published/<data>/`. |
| `intermediarios.py` | Entregas entre produtos do build, em `build/<data>/intermediarios/`. |
| `compose.py` | Fragmentos e montagem (`compose`) do documento de ASN: um bloco novo exige só um produto novo. |
| `chaves_registro.py` | Nomes das contagens do Registro.br no resumo, no manifesto e no detalhe do snapshot: `registro_br_*` e, ao lado, `m3_*` (nome mantido por compatibilidade); a API completa o par que faltar. |
| `jsonio.py` | Leitura tolerante de JSON dos artefatos de build (ausente ou ilegível devolve o padrão). |
| `colunar.py` | Tabela colunar de um arquivo só, lida por `mmap`, para coleções grandes (`maps/global_prefixes.col`). |
| `plugins.py` | Ligação por referência entre camadas: a camada de serviço não importa `products`. |
| `capacidades.py` | Capacidades declaradas em `serve/capabilities/<entidade>.yaml`: o que cada entidade oferece, escrito uma vez. |
| `cobertura.py` | Matriz de cobertura API × MCP × interface: toda rota de dados existe, ou tem justificativa, no MCP e na interface (`docs/cobertura.md`). |
| `consulta_outorgas.py` | Consulta às outorgas, comum à REST e ao MCP gerados das capacidades. |
| `rodizio.py` | Peças comuns da coleta em rodízio: fontes que não cabem numa execução e cobrem o universo ao longo dos dias. |
| `vigia_diretorios.py` | Vigia dos diretórios do Registro.br e do LACNIC: arquivo novo, padrão de nome novo e mudança de cabeçalho. |
| `xlsx_leve.py` | Leitor mínimo de XLSX só com a biblioteca padrão. |
| `geo.py` | Funções geográficas (distância haversine e afins), usadas pelo `Store`, pela consulta e pelos alertas. |
| `geoip.py` | Leitura da base de geolocalização por IP (DB-IP City Lite). |
| `cpf.py` | Máscara do CPF embutido em nomes empresariais e remoção de sócios pessoa física. |
| `universo_telecom.py` | Universo de CNPJs (raiz de 8 dígitos) de telecom: outorgas, SICI e recorte da Receita. |
| `outorgas.py` | Registro dos serviços de outorga da Anatel (SCM, SMP, STFC, SeAC): a única lista, da qual coleta, publicação, API e manifesto derivam. |
| `marcas.py` | Ligação marca → raiz do CNPJ (`config/curada_marcas_operadoras.yaml`). |
| `ixp_peers.py` | Estatísticas por peer direto de um PTT. |
| `prontidao_agregado.py` | Agregação do índice de prontidão em segurança de roteamento: por grupo de ASNs, classes, média ponderada e cobertura dos pilares. |

## Regras de leitura de fontes

Formato de arquivo e recorte de cada fonte, compartilhados pelo coletor (`sources/`) e pelo produto (`products/`):

| Arquivo | Fonte |
|---|---|
| `cetic.py`, `cetic_microdados.py` | Pesquisas TIC do Cetic.br (tabelas oficiais; estimativas por UF a partir dos microdados, com erro-padrão por réplicas). |
| `consumidor.py` | Consumidor.gov.br (arquivo mensal de reclamações finalizadas). |
| `reclamacoes.py`, `rqual.py` | Reclamações e indicadores de qualidade (RQUAL) da Anatel. |
| `erbs.py` | Estações do SMP licenciadas na Anatel (uma linha por estação). |
| `fust.py`, `multas.py`, `pdff.py`, `satelites.py` | FUST, multas constituídas, atribuição de faixas (PDFF) e satélites, da Anatel. |
| `financiamento.py` | BNDES e sanções da CGU (CEIS e CNEP). |
| `receita_cnpj.py` | Dados abertos do CNPJ da Receita Federal. |
| `siasg.py` | Contratos públicos (Compras.gov.br / PNCP). |
| `ipv4_listas.py`, `listas_numeracao.py`, `ipv4_eventos.py` | Listas de numeração do Registro.br e do LACNIC (transferências, recuperação, `delegated-extended`) e o diff diário em eventos do IPv4. |
| `ipv4_subasignacao.py` | Sub-asignações de IPv4: adaptador com esquema **hipotético**, pronto e desativado até a fonte existir. |
| `irr.py` | Dumps de IRR (RPSL): `route`/`route6` e `aut-num` dos ASNs brasileiros, em fluxo. |
| `ixbr_communities.py` | Communities do IX.br pelo dicionário do Alice-LG. |
| `manrs.py` | Participantes do MANRS. |
| `ooni.py` | Medições do OONI: classificação e agregação por ASN. |
| `radar.py` | Cloudflare Radar (formatos da API v4). |
| `shodan.py` | Shodan: constantes e classes de risco. |
| `spoofer.py` | CAIDA Spoofer: agregados por ASN, sem o endereço do cliente. |

## Subpastas

| Pasta | Papel |
|---|---|
| `catalog/` | Esquema (`schema.py`), carregador e validador (`loader.py`) e cobertura do dicionário de dados (`coverage.py`) do catálogo; os YAML ficam em `catalog/` na raiz. |
| `store/` | Armazém de versões de fonte em `data/sources/<id>/<as_of>/`: registro e resolução de versões (`versions.py`), ponte com o catálogo (`fontes.py`), bloco `sources[]` do manifesto (`manifesto.py`) e índice dos snapshots anteriores ao armazém (`legado.py`). |
