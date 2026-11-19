<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Servidores C2 de botnets por ASN (abuse.ch, Feodo Tracker)

`abusech` · tipo **bruta** · ativa

Lista de servidores de comando e controle de botnets do Feodo Tracker (abuse.ch), reduzida na coleta a contagens por ASN (total e online, por família de malware). O IP, a porta e o hostname são descartados. Uma requisição por coleta. O URLhaus NÃO é coletado (exige Auth-Key, cadastro).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.abusech.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 10d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/abusech/` |

## Origem e licença

- **URL:** https://feodotracker.abuse.ch/downloads/ipblocklist.json
- **Formato:** JSON (array de {ip_address, port, status, as_number, country, malware, first_seen, last_online})
- **Licença:** CC0 (Feodo Tracker)
- **Uso comercial:** `permitido`
- **Termos:** https://feodotracker.abuse.ch/blocklist/
- **Evidência / ressalvas:** robots.txt do feodotracker.abuse.ch libera tudo (2026-11-06). Em 2026-11-06 a lista tem 5 entradas (a própria página diz "datasets currently empty"), nenhuma no Brasil. URLhaus: o arquivo csv_recent responde 410 e a API exige Auth-Key; a documentação limita ao uso "fair use" e pede assinatura para uso comercial: sem cadastro, sem coleta.

## Saídas

- **Normalizado (normalized/):** `summary/abusech.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `feodo.asns[asn].c2_total` | int | Servidores C2 do Feodo Tracker em prefixos do ASN (instantâneo da lista, que cobre os últimos 30 dias). | Contagem; o ASN que hospeda não é dono do servidor. | — |
| `feodo.asns[asn].c2_online` | int | Quantos deles estavam online na coleta. | — | — |
| `feodo.asns[asn].malware` | dict | Contagem por família (Dridex, Emotet, TrickBot, QakBot, BazarLoader). | — | — |

## Limites

Lista quase vazia desde 2026; não cobre outras famílias; ausência não é prova de rede limpa. Sem IPs gravados.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `abuso_agregado`

## Pendências (nao_verificado)

- URLhaus bloqueado por exigir cadastro (Auth-Key) e pela cláusula de uso; reavaliar se o mantenedor autorizar o cadastro.
