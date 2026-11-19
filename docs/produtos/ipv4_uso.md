<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Espaço IPv4 sem uso e hipóteses de uso por terceiros

`ipv4_uso` · produto

Classe de cada bloco IPv4 do Brasil pela tabela de origens do snapshot, duração observada sem anúncio e sinais de uso por terceiros (S1 a S4). Não anunciado não é sem uso; sinal é hipótese, nunca aluguel.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.ipv4_uso.build` |
| Chaves de junção | `prefixo`, `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ipv4_delegated](../fontes/ipv4_delegated.md) — uso comercial: `nao_verificado`
- fonte [ipv4_listas](../fontes/ipv4_listas.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `ipv4/ips_sem_uso.json.gz`, `ipv4/uso_por_terceiros.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ips_sem_uso.resumo / duracao` | dict | Blocos e endereços por classe e por UF, maiores titulares sem anúncio e as tabelas de origem anteriores consultadas para a duração. | INFERIDO da tabela de origens do snapshot. A duração só conta as tabelas de origem distintas que temos (a tabela é semanal). | ipv4_uso → ipv4/ips_sem_uso.json.gz#resumo; ipv4_uso → ipv4/ips_sem_uso.json.gz#duracao |
| `ips_sem_uso.blocos[] / colunas` | lista | Blocos não anunciados, parciais, com ROA sem anúncio ou em recuperação: início, endereços, classe, % anunciado, titular (ASN e organização), UF, tabelas de origem sem anúncio, desde quando e ano de registro. | — | ipv4_uso → ipv4/ips_sem_uso.json.gz#blocos; ipv4_uso → ipv4/ips_sem_uso.json.gz#colunas |
| `uso_por_terceiros.itens[]` | lista | Blocos com ao menos um sinal (S1 a S4), com titular, origens, ROAs, sinais com confiança e evidência e a confiança do bloco. | HIPÓTESE de uso por terceiros, com os falsos positivos de cada sinal; dois ou mais sinais sobem a confiança um nível. | ipv4_uso → ipv4/uso_por_terceiros.json.gz#itens |
| `uso_por_terceiros.sinais / por_sinal / por_confianca / rotulo / blocos_avaliados / total` | dict | Catálogo dos sinais S1 a S7 (o que é, falsos positivos, ou por que não foi avaliado) e as contagens. | — | ipv4_uso → ipv4/uso_por_terceiros.json.gz#sinais; ipv4_uso → ipv4/uso_por_terceiros.json.gz#por_sinal; ipv4_uso → ipv4/uso_por_terceiros.json.gz#por_confianca; ipv4_uso → ipv4/uso_por_terceiros.json.gz#rotulo; ipv4_uso → ipv4/uso_por_terceiros.json.gz#blocos_avaliados; ipv4_uso → ipv4/uso_por_terceiros.json.gz#total |
| `snapshot_date / generated_at / natureza / fonte / limites / ultima_foto` | str | Metadados, rótulo de natureza (inferido), fonte, limites e a data da última foto do delegated. | — | ipv4_uso → ipv4/ips_sem_uso.json.gz#natureza; ipv4_uso → ipv4/ips_sem_uso.json.gz#fonte; ipv4_uso → ipv4/ips_sem_uso.json.gz#limites; ipv4_uso → ipv4/ips_sem_uso.json.gz#ultima_foto; ipv4_uso → ipv4/uso_por_terceiros.json.gz#natureza; ipv4_uso → ipv4/uso_por_terceiros.json.gz#fonte; ipv4_uso → ipv4/uso_por_terceiros.json.gz#limites; ipv4_uso → ipv4/uso_por_terceiros.json.gz#ultima_foto |
