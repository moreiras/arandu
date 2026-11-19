<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# TIC Domicílios — tabelas oficiais (Cetic.br)

`cetic_tic_domicilios_tabelas` · tipo **bruta** · ativa

Tabelas oficiais da pesquisa TIC Domicílios (uso das tecnologias de informação e comunicação nos domicílios brasileiros), edição vigente: proporção, total e margens de erro por região, área, classe social e renda familiar, em formato longo.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.cetic_tic_domicilios_tabelas.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | anual |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 400d |
| Chaves | `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/cetic/` |

## Origem e licença

- **URL:** https://cetic.br/pt/pesquisa/domicilios/microdados/
- **Formato:** ZIP com quatro planilhas XLSX (proporção, margem de erro, total e margem de erro do total), uma aba por indicador
- **Licença:** CC BY 4.0
- **Uso comercial:** `permitido`
- **Termos:** https://creativecommons.org/licenses/by/4.0/deed.pt_BR
- **Evidência / ressalvas:** Citar "Cetic.br|NIC.br, TIC Domicílios AAAA" (CC BY 4.0). Não há API nem URL estável: a página lista os links diretos da edição vigente e o coletor os descobre por ela. O robots.txt do cetic.br libera tudo e não pede Crawl-delay; o coletor faz 3 requisições por execução, com pausa de 2 s e User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/tic_domicilios_AAAA_*_xlsx_v1.0.zip`
- **Normalizado (normalized/):** `summary/cetic_tic_domicilios.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `edicao / fonte / url / sha256` | int / str | Ano da edição, citação, endereço do ZIP de origem e hash do arquivo guardado. | A edição é a mais recente listada na página do Cetic.br; as anteriores não ficam disponíveis ali. | — |
| `tabelas[aba]` | object | Código, título, universo (a quem a pergunta se aplica) e notas de cada tabela da pesquisa. | O texto vem da planilha; as marcas de nota de rodapé do título são retiradas. | — |
| `linhas[].proporcao / margem_proporcao` | float | Percentual da resposta dentro do recorte e a margem de erro da estimativa, em pontos percentuais. | Estimativa amostral publicada pelo Cetic.br; vazio quando a planilha não traz o valor (nunca zero inventado). | — |
| `linhas[].total / margem_total` | float | Domicílios que dão a resposta no recorte, estimados pela amostra, e a margem de erro dessa estimativa. | Estimativa expandida pelos pesos da pesquisa, não contagem. | — |
| `linhas[].dimensao / recorte / item / resposta` | str | Como a linha se abre: dimensão do recorte (Total, Região, Área, Classe social, Renda familiar), categoria dentro dela, item da pergunta quando a pergunta tem vários itens e a resposta. | — | — |

## Limites

Estimativas amostrais com margem de erro; o recorte mais fino das tabelas é a grande região (não há UF nas tabelas públicas: ela vem dos microdados). Proporção de domicílios, não de pessoas, salvo onde a tabela diz. O ano de referência é o da pesquisa (coleta no ano anterior à publicação).

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `cetic`

## Pendências (nao_verificado)

- Microdados: a base pública de domicílios é a fonte `cetic_tic_domicilios_microdados`; os sob Termo de Acesso estão fora do escopo.
