<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Nomes de ASNs (RIPE NCC, bulk global)

`asn_names` · tipo **bruta** · ativa

Arquivo asn.txt do RIPE NCC compilado do whois dos cinco RIRs; ~128 mil ASNs com nome. Usado para dar nome a ASNs não brasileiros que aparecem em AS-PATHs.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.asn_names.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/asn_names/` |

## Origem e licença

- **URL:** https://ftp.ripe.net/ripe/asnames/asn.txt
- **Formato:** texto 'ASN nome, CC'
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Sem termos no diretório (2026-10-13). Derivado do whois dos RIRs; termos do RIPE Database não verificados para este arquivo.

## Saídas

- **Bruto (raw/):** `summary/asn-names-{as_of}.txt.gz`
- **Normalizado (normalized/):** `summary/asn_names.json.gz`
- **Publicado direto (published/):** `asns/names.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `{asn}` | str | Nome do ASN (descrição curta do whois, com código de país ao final). | Chaves string; o publicado traz só os ASNs presentes no snapshot. | asn_docs → asns/names.json#* |

## Limites

Nome é texto livre do whois; pode estar desatualizado ou ser genérico. Em 2026-10-11 a origem serviu o arquivo em outro formato (128.261 nomes, 32% no formato 'HANDLE - Descrição' contra 68%); o bruto agora é guardado e o check asn_names do manifesto marca o snapshot como parcial quando isso se repete.

## Retenção

- **bruto:** 4 versões
- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `asn_docs`, `bgp_stability`, `routing_analysis`

## Pendências (nao_verificado)

- Termos de uso de ftp.ripe.net/ripe/asnames/asn.txt não localizados.
