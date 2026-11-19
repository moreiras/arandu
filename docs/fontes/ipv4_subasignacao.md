<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Bitácora de sub-asignações de IPv4 (política LAC-2025-5, esquema hipotético)

`ipv4_subasignacao` · tipo **bruta** · inativa

Registros públicos de sub-asignação de IPv4 (aluguel regulado) que o LACNIC e o Registro.br publicarão depois que a política LAC-2025-5 (ratificada em 24/03/2026; produção prevista até o fim de 2026) entrar em produção. NÃO EXISTE fonte oficial até 2026-11-02: o adaptador está pronto e DESATIVADO, com um esquema hipotético (bloco, ASN do receptor, início, fim, cedente, RIR). Ele só roda com ARANDU_SUBASIGNACAO_URL definida, depois que o formato real for conferido e o `parse` ajustado. O vigia de diretórios (ipv4_vigia) avisa no dia em que surgir arquivo novo.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ipv4_subasignacao.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | nao_verificado |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | nao_verificado |
| Chaves | `prefixo`, `asn` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ipv4_listas/` |

## Origem e licença

- **URL:** nao_verificado
- **Formato:** desconhecido (esquema hipotético em core/ipv4_subasignacao.py)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Fonte inexistente em 2026-11-02. Quando surgir: conferir formato, termos e cadência; ajustar `parse`; definir ARANDU_SUBASIGNACAO_URL; ativar (`ativa: true`) e registrar a decisão.

## Saídas

- **Normalizado (normalized/):** `summary/ipv4_subasignacoes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `registros[]` | lista | Sub-asignação no esquema hipotético: bloco, ASN do receptor, início, fim (opcional), ASN do cedente (opcional) e RIR. | ESQUEMA HIPOTÉTICO; nada é publicado como fato enquanto a fonte não estiver ativada e o formato real conferido. | — |

## Limites

Sem fonte oficial, o artefato publicado diz "aguardando a publicação oficial". As validações aceitam `None` (sem dado) e nunca inventam resultado.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `ipv4_subasig`

## Pendências (nao_verificado)

- Bitácora pública da LAC-2025-5 inexistente: formato, URL, termos e cadência a verificar quando surgir.
