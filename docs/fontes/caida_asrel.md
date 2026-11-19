<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Relações entre ASNs (CAIDA as-rel2)

`caida_asrel` · tipo **bruta** · ativa

Dataset serial-2 do CAIDA (algoritmo AS-Rank sobre RIBs públicas), com relações provedor-cliente e par-par entre ASNs, um arquivo por mês. Entra como prior e régua do produto as_relationships, nunca como verdade (usa os mesmos coletores que a coleta própria).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.caida_asrel.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 45d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/caida_asrel/` |

## Origem e licença

- **URL:** https://publicdata.caida.org/datasets/as-relationships/serial-2/AAAAMMDD.as-rel2.txt.bz2
- **Formato:** texto 'provedor|cliente|-1' e 'par|par|0|fonte' (bz2)
- **Licença:** CAIDA AUA (Acceptable Use Agreement), atribuição obrigatória
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.caida.org/about/legal/aua/
- **Evidência / ressalvas:** Citação exigida: "The CAIDA AS Relationships Dataset, <período>". O arquivo bruto não é redistribuído; só as relações derivadas entram, rotuladas como inferidas.

## Saídas

- **Bruto (raw/):** `summary/caida-asrel-{as_of}.txt.gz`
- **Normalizado (normalized/):** `summary/caida_asrel.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `p2c[]` | list[int] | Par [provedor, cliente] segundo o CAIDA. | Inferência do CAIDA (AS-Rank), não contrato. | — |
| `p2p[]` | list[int] | Par [menor ASN, maior ASN] em relação de peering segundo o CAIDA. | Inferência do CAIDA; inclui pares vistos em looking glasses de IXPs. | — |
| `as_of` | str | Data do arquivo mensal usado (pode ser até um mês anterior ao snapshot). | — | — |

## Limites

Mensal, defasado até ~1 mês; sem probabilidade; cobre ~81 mil ASNs; relações híbridas e parciais são achatadas. Contra o ASPA global tem precisão 0,90 e recall 0,52 (estudo de 2026-10-25).

## Quem usa

- **Produtos:** `as_relationships`, `rede_territorio`

## Pendências (nao_verificado)

- Uso comercial do dataset não verificado (AUA).
- Confirmar que servir as relações derivadas (rotuladas como inferidas, com a atribuição) é compatível com o AUA; o arquivo bruto não é redistribuído.
