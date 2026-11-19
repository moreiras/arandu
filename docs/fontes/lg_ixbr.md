<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Looking Glasses do IX.br (tabelas BGP dos Route Servers)

`lg_ixbr` · tipo **bruta** · ativa

Sessão Telnet em cada um dos 40 Looking Glasses do IX.br (lg.{ixp}.ix.br, porta 23) que executa `show ip bgp` / `show bgp ipv6` e guarda o texto bruto. Mostra o que os Route Servers do IXP enxergam (ASNs com sessão BGP ativa), base da distinção entre presença direta e originador.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.lg_ixbr.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → diaria |
| Frescor máximo | 8d |
| Chaves | `ixp`, `asn`, `prefixo` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/lg_ixbr/` |

## Origem e licença

- **URL:** telnet://lg.{ixp}.ix.br:23
- **Formato:** texto do CLI (FRR/Quagga), v6 e v4
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Looking Glass público do IX.br. Nenhum termo de uso localizado no repositório nem em ix.br (verificado em 2026-10-13: a página lista apenas Política de Privacidade e Termos de Uso do site, sem tratar de dados de LG). Combinar janelas e limites com a engenharia do IX.br.

## Saídas

- **Bruto (raw/):** `{ixp}/bgp-v4-{ixp}-{as_of}.txt.gz`, `{ixp}/bgp-v6-{ixp}-{as_of}.txt.gz`, `{ixp}/bgp-v4-{ixp}-{as_of}.txt`, `{ixp}/bgp-v6-{ixp}-{as_of}.txt`, `collection_manifest.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `collection_manifest.ixps[].v6/v4` | dict | Resultado da coleta de uma família de endereços em um IXP (ok, tamanho, tentativas, erro). | — | snapshot → manifest.json#ixps_collected; snapshot → manifest.json#ixps_failed |
| `bgp-v{4,6}-{ixp}-{as_of}.txt` | texto | Saída literal do comando de tabela BGP do Route Server do IXP, uma linha por rota. | Parseado por products.bgp_routes.build (produto bgp_ixp_normalizado). | — |

## Limites

Uma única sessão por IXP, em um instante; enxerga só o que o Route Server aprende (membros bilaterais ficam invisíveis). Variação de firmware (FRR/Quagga) muda o comando v6. Coleta falha em um IXP não derruba os demais (AP falhou em 2026-10-11).

## Retenção

- **bruto:** 90 dias, comprimido

## Quem usa

- **Produtos:** `as_relationships`, `bgp_ixp_normalizado`

## Pendências (nao_verificado)

- Licença/termos de uso dos Looking Glasses do IX.br não localizados.
- Frescor e janelas diárias dependem de acordo com o IX.br.
