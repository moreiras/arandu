<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Prontidão em segurança de roteamento por ASN

`prontidao` · produto

Índice de 0 a 100 por ASN do Brasil em quatro pilares (filtragem, anti-spoofing, coordenação e validação global), com classe (pronto, em progresso, atrasado, sem dados), os componentes e as regras versionadas. Medições e fatos de terceiros com fonte e data; não é veredito sobre a empresa e não usa o nome de nenhuma iniciativa.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.prontidao.build` |
| Chaves de junção | `asn`, `uf`, `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [caida_spoofer](../fontes/caida_spoofer.md) — uso comercial: `permitido`
- fonte [irr_route_objects](../fontes/irr_route_objects.md) — uso comercial: `nao_verificado`
- fonte [apnic_irov](../fontes/apnic_irov.md) — uso comercial: `nao_verificado`
- fonte [bogons](../fontes/bogons.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `prontidao/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn].total / classe / pilares_sem_dado` | float / str / lista | Índice (0 a 100) com os pilares que tinham dado, a classe (pronto ≥ 80, em progresso ≥ 50, atrasado, ou sem dados quando há menos de dois pilares) e os pilares que ficaram de fora. | Pesos de componentes e pilares se renormalizam pelo que existe; o índice sempre diz quais pilares entraram. | prontidao → prontidao/asns.json.gz#asns |
| `asns[asn].pilares[pilar].componentes` | dict | Valor (0 a 100), peso e detalhe de cada componente (ROV, bogons, Spoofer, PeeringDB, aut-num, as-set, ROA, IRR, ASPA). | Cada componente cita a fonte nas regras; o objeto IRR documenta política e pode ter sido criado por terceiro; ASPA só conta a favor. | — |
| `brasil / por_uf / por_faixa_porte / por_operadora` | dict | Por grupo (país, UF, porte por usuários estimados do APNIC, operadora), ASNs por classe, média ponderada pelos usuários estimados, mediana e cobertura de cada pilar. | Agregados; não há lista nominal dos piores. Operadora = raiz do CNPJ do ASN. | prontidao → prontidao/asns.json.gz#por_uf; prontidao → prontidao/asns.json.gz#por_faixa_porte; prontidao → prontidao/asns.json.gz#por_operadora; prontidao → prontidao/asns.json.gz#brasil |
| `regras / fontes / limites / natureza` | dict | Versão e hash das regras, pesos e descrição de cada pilar e componente, fonte e data de cada insumo, e as limitações. | — | prontidao → prontidao/asns.json.gz#regras; prontidao → prontidao/asns.json.gz#fontes; prontidao → prontidao/asns.json.gz#limites; prontidao → prontidao/asns.json.gz#natureza |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | prontidao → prontidao/asns.json.gz#snapshot_date; prontidao → prontidao/asns.json.gz#generated_at |
