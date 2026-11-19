<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Eventos do ciclo de vida do IPv4 (delegated-extended do LACNIC)

`ipv4_delegated` · tipo **derivada** · ativa

Diff diário do `delegated-lacnic-extended` (blocos IPv4 com país, status, data e `opaque-id` da organização) em eventos observados: `titularidade` (o `opaque-id` mudou), `recuperacao` (allocated/assigned → reserved), `liberacao` (reserved → allocated/assigned), `novo`, `removido` e `pais`. Compara por intervalo de endereços: dividir ou juntar blocos da mesma organização não é evento. Lê o histórico do backfill (2020 em diante) e o bruto diário; grava os eventos em data/ipv4/eventos/ (derivado, reconstruível) e o resumo do dia no normalizado, com a validação cruzada contra as transferências diretas do Registro.br.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ipv4_delegated.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 3d |
| Chaves | `prefixo`, `pais` |
| Entradas | `lacnic_delegated`, `lacnic_historico` |
| Amostra de teste | `tests/fixtures/raw/ipv4_listas/` |

## Origem e licença

- **URL:** https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest e archive/AAAA/
- **Formato:** texto delimitado por | (RIR Statistics Exchange Format, extended)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://ftp.lacnic.net/pub/stats/lacnic/README
- **Evidência / ressalvas:** README do diretório (2004) não declara termos; o `opaque-id` é público no arquivo e não traz nome. Decisão do mantenedor (2026-11-02): publicar derivados; confirmar os termos com o LACNIC. Um evento é uma diferença observada entre duas fotos, sem causa nem intenção.

## Saídas

- **Normalizado (normalized/):** `summary/ipv4_delegated.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ultima_foto / por_status` | str / dict | Data da última foto processada e, por status (allocated, assigned, reserved), blocos e endereços no LACNIC e no Brasil. | — | — |
| `eventos_por_tipo / eventos_ultimos_dias` | dict / int | Eventos dos últimos 30 dias por tipo. | Diferença observada entre fotos diárias, sem causa nem intenção; a data é a da foto em que apareceu (`visto_entre` quando faltou uma foto). | — |
| `validacao_cruzada` | dict | Das transferências diretas BR → BR do Registro.br desde 2020, quantas aparecem como mudança de `opaque-id` no `delegated` (mesmo bloco, de 3 dias antes a 45 dias depois). | — | — |
| `processamento` | dict | Fotos processadas, eventos novos, dias sem arquivo (lacunas) e reorganizações de blocos que não são evento. | — | — |

## Limites

Reserved no `delegated` não diz o motivo (recuperação, reserva técnica ou pool). A organização é só o `opaque-id` (sem nome); o nome vem das transferências e do casamento com o ASN. O estado e os eventos são derivados: apagar data/ipv4/ e rodar com `--backfill-desde` reconstrói.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `ipv4`, `ipv4_uso`

## Pendências (nao_verificado)

- Termos de uso do delegated do LACNIC não declarados; confirmar (decisão do mantenedor de 2026-11-02: publicar derivados enquanto isso).
