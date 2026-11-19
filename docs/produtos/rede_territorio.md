<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Rede no território (IPv6, ROV e trânsito)

`rede_territorio` · produto

IPv6 estimado por município (acessos do SICI × adoção de IPv6 do AS), usuários estimados atrás de ASNs que validam ROV por UF e dependência de trânsito (operadoras com um único provedor inferido), por município e UF.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.rede_territorio.build` |
| Chaves de junção | `ibge`, `uf`, `asn`, `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`
- fonte [apnic_pop](../fontes/apnic_pop.md) — uso comercial: `nao_verificado`
- fonte [apnic_irov](../fontes/apnic_irov.md) — uso comercial: `nao_verificado`
- fonte [caida_asrel](../fontes/caida_asrel.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `territorio/rede_territorio.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ipv6.municipios[ibge] / ufs / brasil` | dict | Acessos fixos declarados, acessos com estimativa, acessos em IPv6 estimados, percentual e a cobertura (parcela dos acessos que entrou). | ESTIMATIVA. Supõe que a adoção de IPv6 do AS (APNIC, ponderada pelos usuários) vale igual em todos os municípios da operadora; operadora sem ASN ou sem medida fica de fora. | rede_territorio → territorio/rede_territorio.json.gz#ipv6 |
| `rov.ufs[uf] / brasil` | dict | Usuários estimados, os com medida de ROV e os atrás de ASNs que validam ROV, por UF da sede do ASN. | ESTIMATIVA. Fração de testes da APNIC em que o AS valida ROV (mínimo de 100 amostras) × usuários estimados; a UF é a da sede do ASN. | rede_territorio → territorio/rede_territorio.json.gz#rov |
| `transito.municipios[ibge] / ufs` | dict | Parcela dos acessos (das operadoras com relação inferida) cujos ASNs têm um único provedor de trânsito, e o provedor do qual mais acessos dependem. | INFERIDO (relações p2c do ARC em nível provável ou superior); operadora sem relação inferida fica de fora, e um provedor só pode ser falta de observação. | rede_territorio → territorio/rede_territorio.json.gz#transito |
| `snapshot_date / generated_at / natureza / limites / fontes` | str / dict | Cabeçalho do produto: snapshot, natureza (estimado), limites e a suposição, e o período de cada fonte. | — | rede_territorio → territorio/rede_territorio.json.gz#snapshot_date; rede_territorio → territorio/rede_territorio.json.gz#generated_at; rede_territorio → territorio/rede_territorio.json.gz#natureza; rede_territorio → territorio/rede_territorio.json.gz#limites; rede_territorio → territorio/rede_territorio.json.gz#fontes |
