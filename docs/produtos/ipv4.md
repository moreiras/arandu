<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Mercado de IPv4 (transferências, recuperação e blocos do Brasil)

`ipv4` · produto

Operações de transferência de IPv4 com o Brasil (Registro.br e LACNIC), agrupadas por dia e partes, com casamento bloco → ASN; resumo do mercado por ano, direção e tamanho; recursos em recuperação; blocos IPv4 do Brasil com o estado no delegated. Diferenças observadas, sem causa nem intenção.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.ipv4.build` |
| Chaves de junção | `prefixo`, `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ipv4_listas](../fontes/ipv4_listas.md) — uso comercial: `nao_verificado`
- fonte [ipv4_delegated](../fontes/ipv4_delegated.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `ipv4/transferencias.json.gz`, `ipv4/mercado.json.gz`, `ipv4/recuperacao.json.gz`, `ipv4/blocos_br.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `transferencias.operacoes[]` | lista | Operação com data, origem e destino (nome, país, RIR, pessoa), blocos, endereços, classe de tamanho, direção (br_br, br_exterior, exterior_br), fontes (registrobr, lacnic), primeira vez visto, defasagem e o ASN atual do destino. | Nome de pessoa física provável é omitido (Pessoa física). Operação é o mesmo dia e as mesmas partes; `anterior_a_coleta` marca o que já estava na primeira lista coletada (a data real de entrada na lista é anterior). | ipv4 → ipv4/transferencias.json.gz#operacoes |
| `mercado.por_ano / por_tamanho / concentracao / maior_operacao / defasagem / casamento` | dict | Operações, blocos e endereços por ano e direção; por classe de tamanho; as 10 maiores partes; a maior operação; a defasagem mediana de publicação; o percentual de destinos casados com ASN. | — | ipv4 → ipv4/mercado.json.gz#por_ano; ipv4 → ipv4/mercado.json.gz#por_tamanho; ipv4 → ipv4/mercado.json.gz#concentracao; ipv4 → ipv4/mercado.json.gz#maior_operacao; ipv4 → ipv4/mercado.json.gz#defasagem; ipv4 → ipv4/mercado.json.gz#casamento |
| `mercado.operacoes / blocos / enderecos / periodo` | int / list | Totais do mercado e o período coberto. | — | ipv4 → ipv4/mercado.json.gz#operacoes; ipv4 → ipv4/mercado.json.gz#blocos; ipv4 → ipv4/mercado.json.gz#enderecos; ipv4 → ipv4/mercado.json.gz#periodo |
| `recuperacao.em_recuperacao / recuperados / eventos_por_mes` | dict | Recursos em recuperação (com a janela e o status atual do bloco no delegated), recuperados por tipo e eventos de recuperação e liberação por mês. | — | ipv4 → ipv4/recuperacao.json.gz#em_recuperacao; ipv4 → ipv4/recuperacao.json.gz#recuperados; ipv4 → ipv4/recuperacao.json.gz#eventos_por_mes |
| `blocos_br.blocos[] / colunas / ultima_foto` | lista | Blocos IPv4 do Brasil na última foto do delegated: início, quantidade de endereços, status, data de registro, `opaque-id`, ASN e organização. | O `opaque-id` é público e não traz nome; a organização vem do casamento com o ASN do snapshot. | ipv4 → ipv4/blocos_br.json.gz#blocos; ipv4 → ipv4/blocos_br.json.gz#colunas; ipv4 → ipv4/blocos_br.json.gz#ultima_foto |
| `snapshot_date / generated_at / natureza / fonte / limites / total` | str | Metadados comuns dos artefatos, o rótulo de natureza (observado) e as limitações. | — | ipv4 → ipv4/transferencias.json.gz#limites; ipv4 → ipv4/transferencias.json.gz#natureza; ipv4 → ipv4/transferencias.json.gz#fonte; ipv4 → ipv4/transferencias.json.gz#total; ipv4 → ipv4/mercado.json.gz#limites; ipv4 → ipv4/mercado.json.gz#natureza; ipv4 → ipv4/mercado.json.gz#fonte; ipv4 → ipv4/recuperacao.json.gz#limites; ipv4 → ipv4/recuperacao.json.gz#natureza; ipv4 → ipv4/recuperacao.json.gz#fonte; ipv4 → ipv4/blocos_br.json.gz#limites; ipv4 → ipv4/blocos_br.json.gz#natureza; ipv4 → ipv4/blocos_br.json.gz#fonte |
