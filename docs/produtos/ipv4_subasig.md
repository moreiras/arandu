<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Sub-asignações de IPv4 (aluguel regulado)

`ipv4_subasig` · produto

Estado das sub-asignações da política LAC-2025-5: aguardando a publicação oficial (com o estado do vigia de diretórios) ou, com a fonte ativada, os registros com as validações da política e o indicador de anúncios de terceiros com e sem registro oficial.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.ipv4_subasig.build` |
| Chaves de junção | `prefixo`, `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ipv4_subasignacao](../fontes/ipv4_subasignacao.md) — uso comercial: `nao_verificado`
- fonte [ipv4_listas](../fontes/ipv4_listas.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `ipv4/subasignacoes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ativa / aguardando / aviso / politica` | bool / str / dict | Se a fonte oficial está ativa, a mensagem "aguardando a publicação oficial" e o estado da política LAC-2025-5. | — | ipv4_subasig → ipv4/subasignacoes.json.gz#ativa; ipv4_subasig → ipv4/subasignacoes.json.gz#aguardando; ipv4_subasig → ipv4/subasignacoes.json.gz#aviso; ipv4_subasig → ipv4/subasignacoes.json.gz#politica |
| `vigia` | dict | Data da última varredura dos diretórios do Registro.br e do LACNIC e os alertas dos últimos 30 dias (arquivo novo, mudança de formato). | — | ipv4_subasig → ipv4/subasignacoes.json.gz#vigia |
| `subasignacoes[] / eventos[] / ignoradas` | lista | Registros (bloco, receptor, início, fim, validações com True, False ou null, em conformidade e pendentes) e eventos subasignacao_inicio e subasignacao_fim vistos entre snapshots. | Vazio até a fonte oficial existir. Esquema hipotético. | ipv4_subasig → ipv4/subasignacoes.json.gz#subasignacoes; ipv4_subasig → ipv4/subasignacoes.json.gz#eventos; ipv4_subasig → ipv4/subasignacoes.json.gz#ignoradas |
| `indicador_terceiros` | dict | Blocos com sinal S1 ou S3 (anúncio de terceiro) cujo anunciante tem sub-asignação registrada e os demais; nulo sem fonte oficial. | Hipótese, não acusação. | ipv4_subasig → ipv4/subasignacoes.json.gz#indicador_terceiros |
| `snapshot_date / generated_at / natureza / validacoes / esquema_hipotetico` | str / dict / bool | Metadados, a lista de validações da política e a marca de que o esquema é hipotético. | — | ipv4_subasig → ipv4/subasignacoes.json.gz#natureza; ipv4_subasig → ipv4/subasignacoes.json.gz#validacoes; ipv4_subasig → ipv4/subasignacoes.json.gz#esquema_hipotetico |
