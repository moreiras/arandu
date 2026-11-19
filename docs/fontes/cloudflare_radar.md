<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cloudflare Radar — IPv6, tráfego, velocidade, BGP e quedas do Brasil (CC BY-NC 4.0)

`cloudflare_radar` · tipo **bruta** · ativa

Séries do Cloudflare Radar para o Brasil: percentual de IPv6 das requisições HTTP de pessoas por ASN (rodízio de dias: todos os ASNs do Brasil conhecidos pelo Radar, ~9,2 mil), participação no tráfego e velocidade/latência dos ASNs de topo, vazamentos e sequestros de BGP dos últimos 28 dias com ASN do Brasil e a consulta de quedas e anomalias do país. Requer token de conta com `Account → Radar → Read`.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.cloudflare_radar.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | usar_ultima_valida |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 10d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/cloudflare_radar/` |

## Origem e licença

- **URL:** https://api.cloudflare.com/client/v4/radar/
- **Formato:** JSON (API v4; `result` e `result_info`)
- **Licença:** CC BY-NC 4.0 (Cloudflare Radar)
- **Uso comercial:** `restrito`
- **Termos:** https://developers.cloudflare.com/radar/
- **Evidência / ressalvas:** API gratuita com token (sem ele responde "Authentication error"). Cota de 1.200 requisições por 5 minutos (cabeçalho `Ratelimit`). Limites de página medidos em 2026-11-09: 100 em `entities/asns`, 300 nos `top/ases`, 50 nos eventos de BGP. Atribuição obrigatória em todo derivado; a pergunta do NC (apoio por PIX e institucional) segue em aberto, como no OONI. Coletor com User-Agent identificado, uma requisição por vez e pausa de 0,5 s. O token só vive no `.env` e chega ao worker pela variável `CLOUDFLARE_API_TOKEN`; nunca em log nem arquivo.

## Saídas

- **Normalizado (normalized/):** `summary/cloudflare_radar.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ipv6[asn]` | dict | Percentual de IPv6 das requisições HTTP de pessoas (`botClass=LIKELY_HUMAN`) do ASN nos últimos 28 dias (`v6`) e a data da leitura (`em`). `v6` nulo = o Radar não devolveu dado para o ASN. | Rodízio de `RADAR_ASNS_POR_EXECUCAO` ASNs por execução (padrão 1.400), os sem leitura primeiro e depois os de leitura mais antiga; cada ASN leva a sua data. Mede quem usa a Cloudflare. | radar → radar/asns.json.gz#asns |
| `trafego.topo / velocidade.topo` | list | Os até 300 ASNs do Brasil com maior participação nas requisições HTTP (`pct`) e os até 300 com testes de velocidade (download, upload, latência ociosa e carregada, jitter, `testes`). | Só existe para os ASNs das listas; fora delas não há número (não é zero). A lista de velocidade veio com 179 ASNs em 2026-11-09. | radar → radar/asns.json.gz#asns |
| `bgp.vazamentos / bgp.sequestros` | dict | Eventos dos últimos 28 dias com ASN do Brasil: vazamentos (vazador, caminho, prefixos) e sequestros (sequestrador, vítimas, nº de prefixos, RPKI inválido). Prefixos só em contagem. | Reduzidos ao necessário para atribuir o papel de cada ASN; o critério do país (`involvedCountry=BR`) pega qualquer evento com ASN do Brasil no caminho, por isso o produto usa o papel. | radar → radar/asns.json.gz#asns; radar → radar/asns.json.gz#bgp |
| `quedas` | dict | Consulta de anomalias de tráfego e de quedas anotadas do Brasil em 52 semanas (contagens) e a data da consulta. | Em 2026-11-09 o Brasil não aparece em nenhum dos dois rankings do Radar (67 e 49 países). Sem série; publica-se o resultado da consulta. | radar → radar/asns.json.gz#quedas |
| `licenca / atribuicao` | str | CC BY-NC 4.0 e o texto de atribuição, que acompanham todo derivado. | — | radar → radar/asns.json.gz#licenca; radar → radar/asns.json.gz#fonte |

## Limites

Cobre quem usa a Cloudflare, não a rede toda. Velocidade e tráfego só para os ASNs de topo. IPv6 em rodízio (até ~7 dias de idade, 28 dias de janela). Quedas só de escala ampla. O Radar não tem recorte por UF.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `radar`

## Pendências (nao_verificado)

- A questão do NC segue em aberto, como no OONI. Para desligar: apagar `CLOUDFLARE_API_TOKEN` do `.env` (a etapa falha com "token ausente" e reaproveita a última coleta) e apagar `published/{data}/radar/`.
