<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Validação de DNSSEC por ASN (APNIC)

`apnic_dnssec` · tipo **bruta** · ativa

Percentual de clientes de cada ASN do Brasil que validam DNSSEC (total e parcial), medido pelo APNIC na janela de 1 dia.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.apnic_dnssec.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 10d |
| Chaves | `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/apnic_labs/` |

## Origem e licença

- **URL:** https://stats.labs.apnic.net/dnssec/BR
- **Formato:** HTML com a tabela por ASN embutida em JavaScript (as mesmas medições do JSON por ASN, que pesa 4 MB por chamada)
- **Licença:** reuso com atribuição (campo copyright do JSON do APNIC)
- **Uso comercial:** `nao_verificado`
- **Termos:** https://data1.labs.apnic.net/ipv6-data-format.html
- **Evidência / ressalvas:** O JSON do APNIC traz "(c) APNIC Pty/Ltd. re-use with attribution permitted"; a página HTML mostra a mesma medição. Citar APNIC Labs como fonte. Uso comercial não foi confirmado além dessa frase.

## Saídas

- **Bruto (raw/):** `summary/apnic-dnssec-BR-{as_of}.html.gz`
- **Normalizado (normalized/):** `summary/apnic_dnssec.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].validates_pct` | float | Percentual de clientes que validam DNSSEC ("DNSSEC Validates"); "Partial Validation" vai em parcial_pct. | Medição por amostragem (anúncios em experimentos de usuários); alto = valida. Não é declaração da rede. | — |
| `asns[asn].amostras` | int | Tamanho da amostra da janela; com poucas amostras o percentual é instável. | — | — |
| `as_of` | str | Último dia da série da página (a janela termina nele). | — | — |

## Limites

ASN sem amostras suficientes não aparece (a página lista ASNs sem medição com valor vazio). A janela é de 1 dia(s). Se o layout da página mudar a coleta falha (o cabeçalho das colunas é conferido); o JSON por ASN é o plano B, mais pesado.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `seguranca_asn`

## Pendências (nao_verificado)

- Uso comercial dos dados do APNIC Labs.
