<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Listas de numeração IPv4 normalizadas (transferências, recuperação, recuperados)

`ipv4_listas` · tipo **derivada** · ativa

Transferências diretas do Registro.br (com o conjunto original e a data do registro original), log de transferências do LACNIC, blocos e ASNs em recuperação e já recuperados, lidos do bruto do dia e normalizados: CIDR abreviado corrigido, Latin-1 decodificado, blocos e endereços somados, e a primeira data de snapshot em que cada registro apareceu (`primeira_vez_visto`; o que já estava na primeira data coletada leva `anterior_a_coleta`). Linha que não casa com o formato é contada, não descartada em silêncio.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ipv4_listas.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 3d |
| Chaves | `prefixo`, `asn`, `pais` |
| Entradas | `registrobr_listas`, `lacnic_listas` |
| Amostra de teste | `tests/fixtures/raw/ipv4_listas/` |

## Origem e licença

- **URL:** https://ftp.registro.br/pub/numeracao/ e https://ftp.lacnic.net/pub/stats/lacnic/transfers/
- **Formato:** texto delimitado por | (Latin-1, Registro.br) e JSON (LACNIC)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://ftp.lacnic.net/pub/stats/lacnic/README
- **Evidência / ressalvas:** Os diretórios não declaram termos de uso (estudo de 2026-10-09, README do LACNIC de 2004). Decisão do mantenedor (2026-11-02): publicar derivados; confirmar os termos com o NIC.br e o LACNIC e registrar aqui. Nome de pessoa física provável é mascarado na saída pública e no MCP (`core/ipv4_listas.py`); o normalizado guarda o nome como vem e não é servido.

## Saídas

- **Normalizado (normalized/):** `summary/ipv4_listas.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `transferencias_registrobr[]` | lista | Transferência direta do Registro.br: data, origem e destino (nome, RIR, país), blocos CIDR, endereços, conjunto original e data do registro original (quando a lista traz), `primeira_vez_visto`. | Nome como vem da fonte (pode ser pessoa física); a publicação mascara. Um lote de blocos na mesma data e partes aparece em várias linhas (agrupado por operação no produto). | — |
| `transferencias_lacnic[]` | lista | Transferência do log do LACNIC (todas as de IPv4 da região, não só as do Brasil), com blocos originais e transferidos. | Registro com endereço nulo é ignorado e contado em `resumo`. | — |
| `recuperacao[] / recuperados[]` | lista | Recurso (bloco IPv6, bloco IPv4 ou ASN) em recuperação com a janela, e recurso já recuperado. | — | — |
| `resumo` | dict | Por lista, registros lidos, linhas ignoradas, primeira data coletada e novos na data. | — | — |

## Limites

As listas do Registro.br só têm a versão atual: o histórico anterior à nossa coleta (junho de 2026) não existe, e `primeira_vez_visto` de registros antigos é a primeira data coletada. O log do LACNIC tem as datas de transferência.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `ipv4`, `ipv4_subasig`, `ipv4_uso`

## Pendências (nao_verificado)

- Termos de uso das listas do Registro.br e do LACNIC não declarados nos diretórios; confirmar com o NIC.br e o LACNIC (decisão do mantenedor de 2026-11-02: publicar derivados enquanto isso).
