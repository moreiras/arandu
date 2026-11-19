<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Bloqueios e interferência medidos pelo OONI, por ASN (CC BY-NC-SA 4.0)

`bloqueios` · produto

Para cada ASN do Brasil com sondas do OONI, por teste (WhatsApp, Telegram, Signal, Facebook Messenger, Tor, Psiphon e, por amostra, Web Connectivity), quantas medições a janela tem e quantas a PRÓPRIA sonda declarou anômalas. Veredito da sonda, não do backend do OONI; não é prova de censura. Só célula com 10 ou mais medições; nenhum site, sonda ou ranking. Dados do OONI sob CC BY-NC-SA 4.0, com atribuição no arquivo.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.bloqueios.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ooni_bloqueios](../fontes/ooni_bloqueios.md) — uso comercial: `restrito`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `bloqueios/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].testes[teste]` | dict | Medições (`n`), anomalias declaradas pela sonda (`anomalias`, `pct_anomalia`), componentes (`partes`) e, no Tor, fração de alvos acessíveis por tipo (`alvos_acessiveis_pct`). O `webconnectivity` traz `amostra=true`. | Veredito da própria sonda (ooni/spec), rotulado como tal; mínimo de 10 medições na janela; viés de voluntários e de sondas; CC BY-NC-SA 4.0. | bloqueios → bloqueios/asns.json.gz#asns |
| `janela / minimo_medicoes / testes / web_amostra` | dict | Primeiro e último dia agregados, mínimo por célula, resumo por teste (medições, ASNs publicados, abaixo do mínimo, critério) e o tamanho da amostra do webconnectivity. | Cobertura declarada para não confundir ausência de sonda com ausência de bloqueio. | bloqueios → bloqueios/asns.json.gz#janela; bloqueios → bloqueios/asns.json.gz#minimo_medicoes; bloqueios → bloqueios/asns.json.gz#testes; bloqueios → bloqueios/asns.json.gz#web_amostra |
| `fonte / licenca / aviso / limites / coletado_em` | dict | Fonte, licença CC BY-NC-SA 4.0 e atribuição, aviso de que o veredito é da sonda, limites e instante da coleta. | — | bloqueios → bloqueios/asns.json.gz#fonte; bloqueios → bloqueios/asns.json.gz#licenca; bloqueios → bloqueios/asns.json.gz#aviso; bloqueios → bloqueios/asns.json.gz#limites; bloqueios → bloqueios/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | bloqueios → bloqueios/asns.json.gz#snapshot_date; bloqueios → bloqueios/asns.json.gz#generated_at |
