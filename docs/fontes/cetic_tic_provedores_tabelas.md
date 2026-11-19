<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# TIC Provedores — tabelas oficiais (Cetic.br)

`cetic_tic_provedores_tabelas` · tipo **bruta** · ativa

Tabelas oficiais da pesquisa TIC Provedores (setor de provimento de serviços de Internet no Brasil), edição vigente: proporção, total e margens de erro por região, porte do provedor e classes de número de acessos e de clientes, em formato longo. Cobre empresas com licença SCM da Anatel que são provedoras de acesso.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.cetic_tic_provedores_tabelas.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | anual |
| Coleta hoje → alvo | semanal → mensal |
| Frescor máximo | 400d |
| Chaves | `uf` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/cetic/` |

## Origem e licença

- **URL:** https://cetic.br/pt/pesquisa/provedores/microdados/
- **Formato:** ZIP com quatro planilhas XLSX (proporção, margem de erro, total e margem de erro do total), uma aba por indicador
- **Licença:** CC BY 4.0
- **Uso comercial:** `permitido`
- **Termos:** https://creativecommons.org/licenses/by/4.0/deed.pt_BR
- **Evidência / ressalvas:** Citar "Cetic.br|NIC.br, TIC Provedores AAAA" (CC BY 4.0). Não há API nem URL estável: a página lista os links diretos da edição vigente e o coletor os descobre por ela. O robots.txt do cetic.br libera tudo e não pede Crawl-delay; o coletor faz 3 requisições por execução, com pausa de 2 s e User-Agent identificado.

## Saídas

- **Bruto (raw/):** `summary/tic_provedores_AAAA_*_xlsx_v1.0.zip`
- **Normalizado (normalized/):** `summary/cetic_tic_provedores.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `edicao / fonte / url / sha256` | int / str | Ano da edição, citação, endereço do ZIP de origem e hash do arquivo guardado. | A edição é a mais recente listada na página do Cetic.br; as anteriores não ficam disponíveis ali. | — |
| `tabelas[aba]` | object | Código, título, universo (a quem a pergunta se aplica) e notas de cada tabela da pesquisa. | O texto vem da planilha; as marcas de nota de rodapé do título são retiradas. | — |
| `linhas[].proporcao / margem_proporcao` | float | Percentual da resposta dentro do recorte e a margem de erro da estimativa, em pontos percentuais. | Estimativa amostral publicada pelo Cetic.br; vazio quando a planilha não traz o valor (nunca zero inventado). | — |
| `linhas[].total / margem_total` | float | Empresas provedoras que dão a resposta no recorte, estimados pela amostra, e a margem de erro dessa estimativa. | Estimativa expandida pelos pesos da pesquisa, não contagem. | — |
| `linhas[].dimensao / recorte / item / resposta` | str | Como a linha se abre: dimensão do recorte (Total, Região, Porte do provedor, Classe de número de clientes), categoria dentro dela, item da pergunta quando a pergunta tem vários itens e a resposta. | — | — |

## Limites

Autodeclaração de uma amostra de empresas, com margem de erro; só Brasil e grandes regiões (não há UF nem empresa individual). Não identifica provedores: o cruzamento com o que o Arandurapé mede (ASN, IX.br) é por classes de porte, no 1.5.4d.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `cetic`

## Pendências (nao_verificado)

- Microdados: a base pública de domicílios é a fonte `cetic_tic_domicilios_microdados`; os sob Termo de Acesso estão fora do escopo.
