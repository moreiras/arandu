<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Cloudflare Radar por ASN e UF (CC BY-NC 4.0)

`radar` · produto

Para cada ASN do Brasil do snapshot, o percentual de IPv6 das requisições de pessoas vistas pela Cloudflare (com a data da leitura), a participação no tráfego e a velocidade/latência (só os ASNs de topo) e o papel nos eventos de BGP dos últimos 28 dias; por UF, agregado derivado dos ASNs. Cobertura declarada; ausência de dado não é zero; sem ranking. Dados do Cloudflare Radar sob CC BY-NC 4.0, com atribuição no arquivo.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.radar.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [cloudflare_radar](../fontes/cloudflare_radar.md) — uso comercial: `restrito`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `radar/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn]` | dict | `ipv6` (`pct` e `em`), `trafego_pct_do_brasil`, `velocidade` (download, upload, latências, jitter, testes) e `bgp` (vazou, no_caminho_de_vazamento, sequestrou, vitima_de_sequestro), só do que existe para o ASN. | Ausência não é zero. IPv6 mede quem usa a Cloudflare; velocidade e tráfego só dos ASNs de topo; eventos de BGP não provam intenção nem dano. | radar → radar/asns.json.gz#asns |
| `por_uf` | dict | Por UF, ASNs do cadastro, ASNs com IPv6, mediana de IPv6, IPv6 ponderado pelo tráfego (só ASNs com os dois números, com a contagem) e soma dos papéis de BGP. | DERIVADO dos ASNs pelo mapeamento ASN → UF do projeto; o Radar não tem recorte por UF. | radar → radar/asns.json.gz#por_uf |
| `cobertura / bgp / quedas` | dict | Cobertura (ASNs no snapshot, na lista do Radar, lidos, com dado, datas da leitura mais antiga e mais recente, ASNs de topo), resumo e critério dos eventos de BGP e a consulta de quedas do país. | Declarados para não confundir ausência de leitura com ausência de problema; "sem quedas" é o que a consulta devolveu na data. | radar → radar/asns.json.gz#cobertura; radar → radar/asns.json.gz#bgp; radar → radar/asns.json.gz#quedas |
| `fonte / licenca / aviso / limites / coletado_em / janela_ipv6` | dict | Fonte, licença CC BY-NC 4.0 e atribuição, avisos, limites, instante da coleta e janela do IPv6. | — | radar → radar/asns.json.gz#fonte; radar → radar/asns.json.gz#licenca; radar → radar/asns.json.gz#aviso; radar → radar/asns.json.gz#limites; radar → radar/asns.json.gz#coletado_em; radar → radar/asns.json.gz#janela_ipv6 |
| `snapshot_date / generated_at` | str | Data do snapshot e instante da geração. | — | radar → radar/asns.json.gz#snapshot_date; radar → radar/asns.json.gz#generated_at |
