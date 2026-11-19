<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Bogons (IANA e Team Cymru)

`bogons` · tipo **bruta** · ativa

Espaço de endereços e números de AS que não deveriam aparecer na tabela de rotas pública, a partir dos registros de uso especial da IANA (IPv6, IPv4 e AS) e das listas fullbogons do Team Cymru (reservados e ainda não alocados por nenhum RIR).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.bogons.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 10d |
| Chaves | `prefixo`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/bogons/` |

## Origem e licença

- **URL:** https://www.iana.org/assignments/iana-ipv4-special-registry/
- **Formato:** CSV da IANA e texto de um CIDR por linha do Team Cymru
- **Licença:** registros da IANA são de uso livre; Team Cymru publica as listas como "Free. Forever." sem cláusula de redistribuição
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.team-cymru.com/bogon-reference-http
- **Evidência / ressalvas:** Só o derivado (prefixo anunciado dentro de bogon) é publicado, com a fonte e a data da lista; a lista inteira não é republicada.

## Saídas

- **Normalizado (normalized/):** `summary/bogons.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `iana.v6[] / iana.v4[]` | list[dict] | Blocos de uso especial não alcançáveis globalmente (privados, documentação, loopback etc.) com nome e RFC. | — | — |
| `iana.asns[]` | list[dict] | Faixas de ASN reservadas (documentação, uso privado, AS_TRANS etc.) com o motivo. | — | — |
| `cymru.v6[] / cymru.v4[]` | list[str] | Fullbogons (reservados mais espaço ainda não alocado por nenhum RIR). | A lista de espaço não alocado muda todo dia; vale a data da lista (cymru.as_of). | — |

## Limites

O fullbogons IPv6 tem ~158 mil linhas (arquivo de ~0,4 MB comprimido). Um prefixo "não alocado" pode ter sido alocado horas antes da atualização da lista.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `prontidao`, `seguranca_asn`

## Pendências (nao_verificado)

- Redistribuição das listas do Team Cymru não é tratada nos termos publicados; publicar só o derivado.
