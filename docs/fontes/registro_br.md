<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Blocos e ASNs do Registro.br (nicbr-asn-blk)

`registro_br` · tipo **bruta** · ativa

Compilação diária do NIC.br/Registro.br de ASNs com nome da organização, CNPJ e prefixos IP originados (whois público). Fonte do universo de prefixos alocados ao Brasil e do vínculo ASN↔CNPJ.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.registro_br.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 8d |
| Chaves | `asn`, `cnpj`, `prefixo` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/registro_br/` |

## Origem e licença

- **URL:** https://ftp.registro.br/pub/numeracao/origin/nicbr-asn-blk-latest.txt
- **Formato:** texto delimitado por | (ASN|Org|CNPJ|prefixos...)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** 00README (2026-10-13): 'Compilation of public whois available ASN Prefix origin information from Nic.br NIR registry'. Sem termos de uso explícitos. O FTP guarda só cerca de 2 semanas de versões diárias (dias úteis); latest.txt aponta a mais recente.

## Saídas

- **Bruto (raw/):** `summary/nicbr-asn-blk-{as_of}.txt.gz`, `summary/nicbr-asn-blk-{as_of}.txt`
- **Normalizado (normalized/):** `summary/registro_br.json.gz`, `summary/registro_br_diff.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[].asn` | int | Número do sistema autônomo registrado no NIC.br. | — | asn_docs → asns/{asn}.json#asn |
| `asns[].name` | str | Nome da organização titular do ASN no whois do NIC.br. | — | asn_docs → asns/{asn}.json#name |
| `asns[].cnpj` | str | CNPJ (14 dígitos) da organização; chave de junção com Anatel e Receita. | Vazio quando o whois não informa. | asn_docs → asns/{asn}.json#cnpj |
| `asns[].prefixes_v6` | list[str] | Prefixos IPv6 alocados à organização no whois. | — | asn_docs → asns/{asn}.json#rir_prefixes_v6 |
| `asns[].prefixes_v4` | list[str] | Prefixos IPv4 alocados à organização no whois. | — | asn_docs → asns/{asn}.json#rir_prefixes_v4 |
| `total_asns / total_prefixes_v6 / total_prefixes_v4` | int | Totais do arquivo do dia. | Checados por publish.coleta_checks (variação máxima entre coletas). | — |
| `source_sha256` | str | SHA-256 do arquivo bruto baixado; prova de proveniência. | — | — |
| `registro_br_diff.{added,removed,changed}` | list | Diferença entre este arquivo e o do snapshot anterior (ASNs incluídos, removidos e alterados). | Gerado só quando há snapshot anterior (use --no-diff para omitir). | — |

## Limites

Mapeia ASN→prefixos e inclui ASNs estrangeiros que receberam blocos BR (ex.: AS174); 'brasileiro' é definido pelo LACNIC (lacnic_delegated), não por este arquivo. Não traz transferências nem histórico.

## Retenção

- **bruto:** 365 dias (o FTP guarda ~2 semanas)
- **normalizado:** 52 semanas

## Quem usa

- **Fontes derivadas:** `bgp_updates_routeviews`, `fulltable_routeviews`, `irr_route_objects`, `prefix_geo`, `rdap`
- **Produtos:** `as_relationships`, `asn_docs`, `ixp_docs`, `mapas_prefixos`, `outorgas`, `regiao_municipios`, `routing_analysis`, `sici`, `snapshot`, `transito`

## Pendências (nao_verificado)

- Termos de uso/licença do nicbr-asn-blk não declarados em 00README; confirmar com o NIC.br.
