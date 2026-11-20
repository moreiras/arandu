# products/ — produtos: análises e documentos publicados

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Cada pasta é um produto: lê o que a coleta deixou em `normalized/` (e o armazém de fontes), calcula e grava em `published/{date}/`
ou em `build/{date}/`. A descrição, as entradas, as saídas e os campos de cada produto estão no catálogo (`catalog/products/<id>.yaml`)
e, em texto, em [docs/produtos/](../docs/produtos/); a ordem de execução vem do grafo do catálogo (`python -m arandu plan`).

Convenção: `build.py` é o ponto de entrada (`python -m products.<pasta>.build --date AAAA-MM-DD`), idempotente e com escrita atômica.

## Arquivos na raiz

| Arquivo | Papel |
|---|---|
| `passos.py` | Passos do build do snapshot, um por produto, na ordem única conferida contra o catálogo; cada passo roda sozinho (`python -m products.passos --passo <id> --date AAAA-MM-DD`). |

## Pastas

| Pasta | Produto do catálogo | O que gera |
|---|---|---|
| `bgp_routes/` | `bgp_ixp_normalizado` | Parser do texto dos looking glasses do IX.br: rotas, prefixos por origem e relações por IXP. |
| `ixp_metrics/` | `ixp_docs`, `asn_docs` | Métricas por IXP e por ASN a partir das rotas normalizadas e das fontes cadastrais. |
| `ixp_docs/` | `ixp_docs` | Documentos por IXP do IX.br, o agregado e os IXPs externos. |
| `asn_docs/` | `asn_docs` | Documento por ASN, índice e nomes. |
| `asn_saude/` | `asn_saude` | Fragmento de saúde do ASN: RPKI (ROAs, validação por prefixo, ASPA) e alertas. |
| `alerts/` | (parte de `asn_saude`) | Pontos de atenção por ASN, uma regra por arquivo, versionadas. |
| `routing_analysis/` | `routing_analysis` | Composição do espaço brasileiro na tabela global, tamanhos, mais-específicos e agregação. |
| `bgp_stability/` | `bgp_stability` | Estabilidade BGP dos ASNs brasileiros (7 dias de updates) e diagnóstico aprofundado dos mais ruidosos. |
| `as_relationships/` | `as_relationships` | Relações provedor-cliente, par e irmãos entre ASNs, inferidas com evidência, probabilidade e nível (metodologia em `docs/metodologia-relacoes-asns.md`). |
| `transito/` | `transito` | Provedores de trânsito por UF e cone de clientes (inferidos). |
| `as2org/` | `as2org`, `abuso_agregado` | Organização por ASN (CAIDA) e abuso agregado (Feodo Tracker). |
| `seguranca/` | `seguranca_asn` | Sinais de segurança de roteamento por ASN (RPKI, DNSSEC, rank e cone, IRR). |
| `prontidao/` | `prontidao` | Índice de prontidão em segurança de roteamento por ASN, em quatro pilares. |
| `manrs/` | `manrs_agregado` | Participação no MANRS, agregada. |
| `route_servers/` | `route_servers` | Route servers do IX.br: sessões BGP dos membros × cadastro. |
| `rs_policy/` | `rs_policy` | Rejeições, communities e política de roteamento nos route servers do IX.br. |
| `decix_rs/` | `decix_rs` | Route servers do DE-CIX Rio e São Paulo (estende os IXPs externos). |
| `instalacoes/` | `instalacoes` | Instalações do PeeringDB, vínculos, atributos das redes e portas externas. |
| `cdns/` | `cdns` | Presença de CDNs nos IXPs. |
| `bloqueios/` | `bloqueios` | Bloqueios e interferência medidos pelo OONI, por ASN. |
| `radar/` | `radar` | Cloudflare Radar por ASN e UF. |
| `exposicao/` | `exposicao` | Exposição de serviços por ASN e UF (contagens do Shodan). |
| `ipv4/` | `ipv4` | Mercado de IPv4: transferências, recuperação e blocos do Brasil. |
| `ipv4_uso/` | `ipv4_uso` | Espaço IPv4 sem uso e hipóteses de uso por terceiros. |
| `ipv4_subasig/` | `ipv4_subasig` | Sub-asignações de IPv4 (política LAC-2025-5): estado da publicação oficial. |
| `outorgas/` | `outorgas` | Outorgas da Anatel (SCM, SMP, STFC, SeAC) e seus mapas. |
| `sici/` | `sici` | Acessos declarados ao SICI (fixo e móvel), por CNPJ e município, e divergência APNIC × Anatel. |
| `sici_indicadores/` | `sici_indicadores` | Share, HHI, variações e parada de declaração; outorgas SCM sem acessos declarados. |
| `penetracao/` | `penetracao` | Penetração de banda larga fixa e mercado não visto. |
| `demanda_oferta/` | `demanda_oferta` | Demanda × oferta de banda larga fixa. |
| `rede_territorio/` | `rede_territorio` | IPv6 estimado por município, usuários atrás de ROV e dependência de trânsito. |
| `regiao/` | `regiao_municipios` | ASNs por município e o que se sabe deles (PTTs, trânsito). |
| `erbs/` | `erbs` | Estações do SMP licenciadas por município, UF e operadora. |
| `qualidade/` | `qualidade` | Indicadores de qualidade (RQUAL) e reclamações da Anatel. |
| `consumidor/` | `consumidor` | Reclamações finalizadas no Consumidor.gov.br. |
| `regulatorio/` | `regulatorio` | FUST, multas, faixas de frequência e satélites. |
| `cadastro_empresas/` | `cadastro_empresas` | Cadastro das empresas de telecom (Receita Federal) cruzado com o SICI. |
| `grupos_societarios/` | `grupos_societarios` | Grupos societários a partir do quadro de sócios (sem sócios pessoa física). |
| `financiamento_sancoes/` | `financiamento_sancoes` | Crédito público (BNDES) e sanções (CEIS e CNEP) por operadora. |
| `contratos/` | `contratos` | Contratos públicos de operadoras (PNCP). |
| `cetic/` | `cetic` | Tabelas oficiais das pesquisas TIC do Cetic.br em formato longo. |
| `mapas_prefixos/` | `mapas_prefixos` | GeoJSON de prefixos e ASNs e curvas de Hilbert do espaço IP; tabela colunar dos prefixos globais; camadas de prefixos de cada PTT (`maps/ixp_prefixes/`, `ixp_prefixos.py`, que também preenche snapshots já publicados). |
| `mapas_infraestrutura/` | `mapas_infraestrutura` | Camadas de infraestrutura: cabos submarinos, enlaces, linhas de transmissão e rodovias. |
| `history/` | `history` | Camada de histórico (`data/history/`): séries por entidade e log de eventos derivados dos snapshots. |
| `snapshot/` | `snapshot` | Resumo e detalhe pré-calculado do snapshot; o manifesto é a última etapa, em `publish/`. |
