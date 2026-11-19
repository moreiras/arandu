<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Organização por ASN (CAIDA) e irmãos do Brasil

`as2org` · produto

Para cada ASN do Brasil conhecido pelo CAIDA AS Rank, a organização (nome, país, número de ASNs no mundo) e os outros ASNs do Brasil da mesma organização ("irmãos"), mais a cobertura em relação aos ASNs do Brasil do snapshot. Organização inferida pelo CAIDA a partir do WHOIS; não é grupo societário.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.as2org.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [caida_as2org](../fontes/caida_as2org.md) — uso comercial: `nao_verificado`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `as2org/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].org_nome / org_id / org_pais / membros_total` | dict | Organização do ASN no CAIDA AS Rank. | Inferência do CAIDA a partir do WHOIS; pode agrupar filiais sob uma 'Parent'; rotulada como do CAIDA. | as2org → as2org/asns.json.gz#asns |
| `asns[asn].irmaos_br` | list[int] | Outros ASNs do Brasil com a mesma organização. | Só ASNs do Brasil; a organização pode ter ASNs em outros países (membros_total). | as2org → as2org/asns.json.gz#asns |
| `cobertura` | dict | ASNs do Brasil do snapshot, quantos têm organização, percentual e número de organizações com mais de um ASN do Brasil. | Medida de cobertura da fonte, não de qualidade do dado. | as2org → as2org/asns.json.gz#cobertura |
| `fonte / limites / coletado_em` | dict | Fonte, citação exigida, limitações e instante da coleta. | — | as2org → as2org/asns.json.gz#fonte; as2org → as2org/asns.json.gz#limites; as2org → as2org/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | as2org → as2org/asns.json.gz#snapshot_date; as2org → as2org/asns.json.gz#generated_at |
