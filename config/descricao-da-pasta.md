# config/ — configuração estática

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Configuração versionada do pipeline, da API e do MCP. Segredos (chaves de API, tokens, senhas) **nunca** ficam aqui: vão no `.env`
(modelo em `.env.example`). Os YAML gerais são carregados por `core/common.py` (`load_settings()`, `load_ixps()`,
`load_peeringdb_ixps_config()`); os demais, por quem os usa.

## Arquivos

| Arquivo | Papel |
|---|---|
| `settings.yaml` | Parâmetros gerais do pipeline (diretório de dados, paralelismo e timeouts da coleta). |
| `ixps.yaml` | Os 40 PTTs do IX.br: código, nome, cidade, UF, host e porta Telnet do looking glass e timeout. Fonte da coleta do LG e dos códigos de PTT do MCP. |
| `peeringdb_ixps.yaml` | IXPs consultados no PeeringDB: os externos acompanhados (`external`) e os do IX.br com o `pdb_ix_id` (`ixbr`). |
| `pix.yaml` | Localização física dos PIX do IX.br (curada; gerada por `scripts/scrape_pix_locations.py` e completada por `scripts/geocode_pix_entries.py` e `scripts/inject_pix_from_llm.py`). |
| `cdns.yaml` | CDNs e grandes provedores de conteúdo acompanhados e seus ASNs. |
| `bgp_communities.yaml` | Communities BGP conhecidas de operadores brasileiros, com o texto legível de cada uma. |
| `as_relationships.yaml` | Parâmetros do algoritmo de inferência de relações entre ASNs (produto `as_relationships`; metodologia em `docs/metodologia-relacoes-asns.md`). |
| `curada_marcas_operadoras.yaml` | Tabela curada marca → raiz do CNPJ, usada para atribuir reclamações e marcas a operadoras (`core/marcas.py`). |
| `municipios-centroides.json` | Centroides dos municípios (mesma fonte do frontend); gerado por `scripts/build-municipio-centroides.py`. |
| `municipios-referencia.json` | Nomes e códigos IBGE dos municípios para a busca universal; gerado por `scripts/build-municipios-referencia.py`. |
| `paginas_publicas.json` | Páginas do menu e fixas para o sitemap e o `llms.txt`; gerado por `scripts/gen_sitemap.py`. |
| `vex.openvex.json` | Exceções da verificação de vulnerabilidades (`scripts/sbom.sh`, formato OpenVEX): componente afetado no papel e não na prática, cada um com a justificativa. Vazio = nenhuma exceção. |

## Observações

- PTT novo do IX.br: edite `ixps.yaml` e a seção `ixbr` de `peeringdb_ixps.yaml`.
- IXP externo novo: só a seção `external` de `peeringdb_ixps.yaml`.
- Os JSON são gerados: rode o script correspondente em vez de editá-los à mão.
