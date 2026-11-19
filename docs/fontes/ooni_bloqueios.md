<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# OONI — medições de interferência no Brasil, agregadas por ASN (bucket aberto)

`ooni_bloqueios` · tipo **bruta** · ativa

Medições de rede do OONI (Open Observatory of Network Interference) feitas por sondas de voluntários no Brasil, lidas do bucket público de dados abertos `ooni-data-eu-fra` (Amazon Open Data) e agregadas por ASN × teste × dia EM FLUXO: o bruto é descartado, nada de medição por sonda, `report_id`, input, IP da sonda ou nome de rede. Fase A: testes leves (whatsapp, telegram, signal, facebookmessenger, tor, psiphon), todos os arquivos do dia. Fase B: webconnectivity por AMOSTRA (3 horas UTC por dia, teto de 3 GB por execução). O veredito é o da própria sonda (ooni/spec), não o do backend do OONI: não é prova de censura.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ooni_bloqueios.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | continua |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 21d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ooni/` |

## Origem e licença

- **URL:** https://ooni-data-eu-fra.s3.amazonaws.com/
- **Formato:** S3 público, listagem anônima por HTTPS (`?list-type=2&prefix=raw/AAAAMMDD/HH/BR/`); objetos `raw/AAAAMMDD/HH/BR/<teste>/AAAAMMDDHH_BR_<teste>.<host>.<n>.jsonl.gz` (JSONL, uma medição por linha); os `.tar.gz` duplicados são ignorados
- **Licença:** CC BY-NC-SA 4.0 (OONI; registro AWS awslabs/open-data-registry datasets/ooni.yaml; ooni/license data/LICENSE.md)
- **Uso comercial:** `restrito`
- **Termos:** https://github.com/ooni/license/blob/master/data/LICENSE.md
- **Evidência / ressalvas:** Canal indicado pelo OONI a pesquisadores (docs.ooni.org/data). O `robots.txt` de api.ooni.io proíbe a agregação e fixa Crawl-delay 300: a API NÃO é usada, nem docs.ooni.org (atrás de desafio anti-bot). Licença lida em 2026-11-07: atribuição (BY), uso não comercial (NC) e compartilhamento pela mesma licença do material adaptado (SA). Dado e código têm políticas distintas (código AGPL; dados por fonte, como a TeleGeography): os agregados derivados saem sob a MESMA CC BY-NC-SA 4.0, com atribuição, em todo canal, o que cumpre o SA. Resta em aberto só o NC (se o apoio por PIX e institucional é uso comercial; X7, X14). Coletor com User-Agent identificado, uma requisição por vez, pausa de 1 s. Volume do Brasil em 2026-11-01: webconnectivity ~1,44 GB/dia e os demais testes juntos ~45 MB/dia (.jsonl.gz).

## Saídas

- **Normalizado (normalized/):** `summary/ooni_bloqueios.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `dias[AAAA-MM-DD].testes[teste][asn]` | dict | Medições válidas (`n`), com anomalia declarada pela sonda (`anom`), por componente (`partes`) e, no tor, alvos totais/acessíveis por tipo (`alvos`). O dia é o da pasta do bucket (lote do dia, UTC). | Veredito da PRÓPRIA sonda segundo o ooni/spec (ts-015, ts-018, ts-019, ts-020, ts-023, ts-029); não é o do backend do OONI. Medição do signal com test_version <= 0.2.3 é descartada (falsos positivos documentados). | — |
| `dias[AAAA-MM-DD].web` | dict | webconnectivity por ASN no dia, só da AMOSTRA de horas: `n`, `anom` (blocking = dns, tcp_ip, http-failure ou http-diff), `partes`, `sem_veredito`, `inacessivel`. Nenhum domínio, URL ou categoria. | Amostra rotulada; veredito da sonda; https nunca recebe veredito de bloqueio pela sonda (ts-017), então a taxa é um piso. | — |
| `dias[AAAA-MM-DD].web_amostra` | dict | Horas UTC amostradas, arquivos lidos e esperados, bytes e se a amostra do dia ficou completa (o teto de GB pode cortá-la). | — | — |
| `ultima_execucao` | dict | Custo da última execução (dias baixados, requisições, bytes baixados, arquivos, medições lidas e descartadas, segundos). | — | — |
| `licenca / atribuicao` | str | CC BY-NC-SA 4.0 e o texto de atribuição, que acompanham todo derivado. | — | — |

## Limites

Sondas são de voluntários (viés de quem instala e de onde), poucas por ASN e concentradas em redes grandes; célula com menos de 10 medições na janela não é publicada. O veredito é da sonda, pode ser filtro do próprio cliente (controle parental, rede corporativa, VPN) e falso positivo. webconnectivity é amostra. Cobertura por ASN, não por município. Uma execução leva dezenas de minutos (1 s de pausa por requisição).

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `bloqueios`

## Pendências (nao_verificado)

- Decisão do mantenedor (2026-11-07): tratar o OONI como a TeleGeography: fonte ATIVA, licença própria declarada (CC BY-NC-SA 4.0, uso_comercial restrito) e atribuição em todas as saídas. A questão jurídica do NC continua registrada e a consulta jurídica pode mudar isso. Para desligar: `OONI_ATIVO=0` no ambiente (a etapa sai sem requisição) e apagar `published/{data}/bloqueios/`.
- Comunicar a atribuição ao OONI (contact@openobservatory.org), se o mantenedor quiser.
