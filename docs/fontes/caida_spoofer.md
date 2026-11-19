<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# CAIDA Spoofer — validação de endereço de origem (SAV)

`caida_spoofer` · tipo **bruta** · ativa

Sessões de teste do Spoofer do CAIDA (cliente voluntário que envia pacotes com origem forjada: privada e roteada, em IPv6 e IPv4) do Brasil, agregadas por ASN em janela de 12 meses: sessões, sessões conclusivas fora de NAT, % em que a rede barrou os dois testes, % em que o pacote privado ou roteado chegou, última sessão. O endereço do cliente (/24) que a API devolve é descartado antes de gravar qualquer coisa.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.caida_spoofer.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 14d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/caida_spoofer/` |

## Origem e licença

- **URL:** https://api.spoofer.caida.org/sessions?country=bra
- **Formato:** JSON Hydra paginado (itemsPerPage=500), sem chave; filtro `timestamp[after]`
- **Licença:** CAIDA Public AUA
- **Uso comercial:** `permitido`
- **Termos:** https://www.caida.org/about/legal/aua/public_aua/
- **Evidência / ressalvas:** Public AUA lida em 2026-11-02: licença limitada para copiar, modificar e usar; citar "The CAIDA UCSD [Dataset Name] - [datas usadas], https://catalog.caida.org/dataset/[url]" e comunicar a publicação ao CAIDA (data-info@caida.org) com um link. A página da "Public Data API" do Spoofer não foi lida. A página do projeto diz que o financiamento do Spoofer acabou (cliente 1.5.0 lançado em 2026-07): a coleta pode parar. Uso liberado com citação e comunicação ao CAIDA.

## Saídas

- **Normalizado (normalized/):** `summary/caida_spoofer.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[].sessoes / sessoes_v4 / sessoes_v6 / pct_nat_v4 / ultima_sessao` | int / float / data | Sessões atribuídas ao ASN na janela de 12 meses (por família), percentual das sessões IPv4 atrás de NAT e data da última. | Sessão que mede IPv6 e IPv4 conta uma vez em `sessoes` e uma vez em cada família. | — |
| `asns[].conclusivas / conclusivas_v4 / conclusivas_v6 / suficiente` | int / bool | Sessões conclusivas (algum teste `blocked` ou `received`) fora de NAT em IPv6 e em IPv4, e se atingem o mínimo (5) para o ASN ter pontuação neste pilar. | `rewritten` (NAT reescreveu a origem) e `unknown` não contam; IPv4 atrás de NAT não conta, porque o resultado não fala da rede do ASN. | — |
| `asns[].pct_bloqueado / pct_recebido_privado / pct_recebido_roteado` | float | % das sessões conclusivas em que nenhum pacote forjado chegou; % dos testes conclusivos com origem privada e com origem roteada em que o pacote chegou. | — | — |
| `resumo / citacao / novas_sessoes` | dict | Sessões na janela, ASNs com dado e suficientes, janela e mínimo; a citação exigida pelo CAIDA; sessões novas baixadas nesta execução. | — | — |

## Limites

O Spoofer é voluntário e concentrado em poucos ASNs (hoje 553 dos 9.123 ASNs brasileiros têm alguma sessão em 12 meses). Resultado `blocked` de sessão atrás de NAT não prova que a rede do ASN filtra. O projeto está sem financiamento e a coleta pode parar; sem sessões novas o pilar fica com a última janela e a data da última sessão.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `prontidao`

## Pendências (nao_verificado)

- Comunicar a publicação ao CAIDA (data-info@caida.org) depois do deploy, com o link da página que cita o dataset.
- Ler a página da "Public Data API" do Spoofer (termos específicos do Spoofer, se houver).
