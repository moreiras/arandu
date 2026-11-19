<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Exposição de serviços por ASN e UF (contagens do Shodan, atribuição obrigatória)

`exposicao` · produto

Para cada ASN do Brasil já lido, os serviços que o Shodan observou (total, portas mais vistas, serviços em portas de risco por classe e, se o plano tiver a faceta, as CVEs mais vistas), com a data da leitura; por UF, agregado derivado dos ASNs. Cobertura declarada; ausência de leitura não é zero; sem ranking; nunca lista de IPs. Contagem observada pelo Shodan não é prova de vulnerabilidade.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.exposicao.build` |
| Chaves de junção | `asn` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [shodan_exposicao](../fontes/shodan_exposicao.md) — uso comercial: `nao_verificado`
- produto [asn_docs](asn_docs.md)

## Saídas

- **Publicado:** `exposicao/asns.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `asns[asn]` | dict | `lido_em`, `servicos_observados`, `portas_mais_vistas`, `risco` (serviços de risco, % dos observados e totais por classe com as portas) e `vulnerabilidades` (CVEs mais vistas, ou "não disponível no plano"). | Só ASNs lidos pelo rodízio; sem leitura = ausente (não zero). `sem_servico_observado` = o Shodan não viu serviço. Banners, não hosts únicos. | exposicao → exposicao/asns.json.gz#asns |
| `por_uf` | dict | Por UF, ASNs do cadastro, com leitura e com serviços, serviços observados, serviços de risco (total, % e por classe e serviço). | DERIVADO dos ASNs pelo mapeamento ASN → UF do projeto, só com os ASNs lidos (a cobertura vai junto); sem CVEs. | exposicao → exposicao/asns.json.gz#por_uf |
| `cobertura / plano / classes` | dict | ASNs do Brasil no snapshot, com leitura e com serviços, datas da leitura mais antiga e mais recente; facetas do plano; classes de risco e portas (definição do projeto). | Declarados para não confundir ausência de leitura com ausência de exposição. | exposicao → exposicao/asns.json.gz#cobertura; exposicao → exposicao/asns.json.gz#plano; exposicao → exposicao/asns.json.gz#classes |
| `fonte / licenca / aviso / limites / coletado_em` | dict | Fonte, atribuição ao Shodan, avisos, limites e instante da coleta. | — | exposicao → exposicao/asns.json.gz#fonte; exposicao → exposicao/asns.json.gz#licenca; exposicao → exposicao/asns.json.gz#aviso; exposicao → exposicao/asns.json.gz#limites; exposicao → exposicao/asns.json.gz#coletado_em |
| `snapshot_date / generated_at` | str | Data do snapshot e instante da geração. | — | exposicao → exposicao/asns.json.gz#snapshot_date; exposicao → exposicao/asns.json.gz#generated_at |
