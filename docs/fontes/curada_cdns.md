<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# CDNs e grandes provedores de conteúdo (config/cdns.yaml)

`curada_cdns` · tipo **curada** · ativa

Agrupamento manual de ASNs por CDN/provedor de conteúdo (Cloudflare, Google/GGC, Akamai, Meta, Microsoft, AWS, Netflix/OCA…) para medir presença nos IXPs.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `config/cdns.yaml` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → sob_demanda |
| Frescor máximo | 400d |
| Chaves | `asn`, `ixp` |
| Entradas | — |

## Origem e licença

- **URL:** —
- **Formato:** YAML mantido à mão em config/
- **Licença:** Curadoria do projeto (dados factuais; fontes citadas)
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Pesquisa manual + PeeringDB (comentário do arquivo). Lista factual de ASNs.

## Saídas

- **Publicado direto (published/):** `cdns.json`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `cdns[].name` | str | Nome do provedor/CDN. | — | cdns → cdns.json#cdns |
| `cdns[].asns` | list[int] | ASNs atribuídos ao provedor. | Presença em um IXP = QUALQUER dos ASNs presente. | cdns → cdns.json#cdns |
| `cdns[].aka` | str | Nome do programa de cache (ex.: GGC, OCA). | — | cdns → cdns.json#cdns |

## Limites

Lista curada à mão, incompleta e subjetiva (o que é 'CDN'); ASN de CDN pode servir também outros propósitos.

## Retenção

- **normalizado:** git

## Quem usa

- **Produtos:** `cdns`

## Pendências (nao_verificado)

- Licença das informações originadas do PeeringDB (AUP) usadas na pesquisa.
