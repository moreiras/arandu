<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Validação RPKI por ASN (APNIC I-RoV)

`apnic_irov` · tipo **bruta** · ativa

Percentual das medições do APNIC em que a rede de cada ASN do Brasil não alcança destinos de rota RPKI-inválida ("RPKI Validates"), com a amostra da janela de 7 dias. Sinal de ROV por ASN, medido, sem declaração da rede.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.apnic_irov.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 10d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/apnic_labs/` |

## Origem e licença

- **URL:** https://stats.labs.apnic.net/rpki/BR
- **Formato:** HTML com a tabela por ASN embutida em JavaScript (as mesmas medições do JSON por ASN, que pesa 0,8 MB por chamada)
- **Licença:** reuso com atribuição (campo copyright do JSON do APNIC)
- **Uso comercial:** `nao_verificado`
- **Termos:** https://data1.labs.apnic.net/ipv6-data-format.html
- **Evidência / ressalvas:** O JSON do APNIC traz "(c) APNIC Pty/Ltd. re-use with attribution permitted"; a página HTML mostra a mesma medição. Citar APNIC Labs como fonte. Uso comercial não foi confirmado além dessa frase.

## Saídas

- **Bruto (raw/):** `summary/apnic-rpki-BR-{as_of}.html.gz`
- **Normalizado (normalized/):** `summary/apnic_irov.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].validates_pct` | float | Percentual de medições em que a rota RPKI-inválida não foi alcançada ("RPKI Validates"; campo filter_rate do JSON). | Medição por amostragem (anúncios em experimentos de usuários); alto = valida. Não é declaração da rede. | — |
| `asns[asn].amostras` | int | Tamanho da amostra da janela; com poucas amostras o percentual é instável. | — | — |
| `as_of` | str | Último dia da série da página (a janela termina nele). | — | — |

## Limites

ASN sem amostras suficientes não aparece (a página lista ASNs sem medição com valor vazio). A janela é de 7 dia(s). Se o layout da página mudar a coleta falha (o cabeçalho das colunas é conferido); o JSON por ASN é o plano B, mais pesado.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `prontidao`, `rede_territorio`, `seguranca_asn`

## Pendências (nao_verificado)

- Uso comercial dos dados do APNIC Labs.
