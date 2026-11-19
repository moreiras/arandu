<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Segurança de roteamento por ASN, parte A

`seguranca_asn` · produto

Sinais de segurança de roteamento por ASN do Brasil (validação RPKI e DNSSEC medidas pelo APNIC, rank e cone do CAIDA, prefixos em espaço bogon) e agregados por UF e faixa de porte. Medições e fatos de terceiros, com fonte e data; sem veredito.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.seguranca.build` |
| Chaves de junção | `asn`, `uf` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [apnic_irov](../fontes/apnic_irov.md) — uso comercial: `nao_verificado`
- fonte [apnic_dnssec](../fontes/apnic_dnssec.md) — uso comercial: `nao_verificado`
- fonte [caida_asrank](../fontes/caida_asrank.md) — uso comercial: `nao_verificado`
- fonte [bogons](../fontes/bogons.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `seguranca/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].rov / dnssec` | dict | Percentual medido pelo APNIC (validates_pct; DNSSEC também parcial_pct) e o tamanho da amostra. | Medição por amostragem, não declaração da rede; alto = valida; ASN com poucas amostras fica fora dos agregados. | seguranca_asn → seguranca/asns.json.gz#asns |
| `asns[asn].asrank` | dict | Rank, grau e cone de clientes segundo o CAIDA AS Rank. | Inferência do CAIDA; rotulada como estimada. | seguranca_asn → seguranca/asns.json.gz#asns |
| `asns[asn].prefixos_em_bogon / n_prefixos_bogon / asn_reservado` | list / int / str | Prefixos originados pelo ASN dentro de espaço reservado (IANA) ou não alocado (Team Cymru, na data da lista) e ASN em faixa reservada. | Fato verificável contra as listas citadas; bloco recém-alocado pode aparecer como não alocado por horas. | seguranca_asn → seguranca/asns.json.gz#asns |
| `por_uf / por_faixa_porte / brasil` | dict | Contagem de ASNs, mediana e média ponderada de ROV e DNSSEC e distribuição em faixas neutras (até 10, 10 a 90, acima de 90), por UF e por porte (usuários estimados do APNIC; a faixa de acessos declarados ao SICI do CNPJ fica em `faixa_acessos_sici` de cada ASN). | Só ASNs com pelo menos 100 amostras; não é ranking de empresas. | seguranca_asn → seguranca/asns.json.gz#por_uf |
| `fontes / parametros / limites` | dict | Fonte, data e janela de cada sinal, parâmetros do cálculo e as limitações. | — | seguranca_asn → seguranca/asns.json.gz#fontes |
