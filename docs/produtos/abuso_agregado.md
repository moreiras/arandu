<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Abuso agregado por ASN (Feodo Tracker)

`abuso_agregado` · produto

Contagem, por ASN do Brasil, de servidores de comando e controle de botnets do Feodo Tracker (abuse.ch, CC0), total e online, por família. Sem IPs. Só entram os ASNs com pelo menos um C2; ausência não quer dizer rede limpa. O URLhaus não é coletado (exige cadastro).

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.as2org.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [abusech](../fontes/abusech.md) — uso comercial: `permitido`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `abuso_agregado/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].feodo_c2 / feodo_c2_online / feodo_malware` | dict | Servidores C2 do Feodo Tracker em prefixos do ASN, quantos online e por família. | Contagem de terceiros na data da coleta; o ASN que hospeda não é dono do servidor; sem veredito. | abuso_agregado → abuso_agregado/asns.json.gz#asns |
| `feodo_total_mundo / feodo_online_mundo / feodo_asns_br / feodo_c2_br` | int | Totais da lista no mundo e no Brasil. | — | abuso_agregado → abuso_agregado/asns.json.gz#feodo_total_mundo; abuso_agregado → abuso_agregado/asns.json.gz#feodo_online_mundo; abuso_agregado → abuso_agregado/asns.json.gz#feodo_asns_br; abuso_agregado → abuso_agregado/asns.json.gz#feodo_c2_br |
| `fonte / urlhaus / limites / coletado_em` | dict | Fonte e licença, estado do URLhaus (indisponível), limitações e instante da coleta. | — | abuso_agregado → abuso_agregado/asns.json.gz#fonte; abuso_agregado → abuso_agregado/asns.json.gz#urlhaus; abuso_agregado → abuso_agregado/asns.json.gz#limites; abuso_agregado → abuso_agregado/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante UTC de geração. | — | abuso_agregado → abuso_agregado/asns.json.gz#snapshot_date; abuso_agregado → abuso_agregado/asns.json.gz#generated_at |
