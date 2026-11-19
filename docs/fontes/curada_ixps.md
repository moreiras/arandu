<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Localidades do IX.br (config/ixps.yaml)

`curada_ixps` · tipo **curada** · ativa

Lista das 40 localidades ativas do IX.br com código, nome, UF, host do Looking Glass, porta, timeout e CEP aproximado para geolocalização.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `config/ixps.yaml` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → sob_demanda |
| Frescor máximo | 400d |
| Chaves | `ixp`, `uf` |
| Entradas | — |

## Origem e licença

- **URL:** —
- **Formato:** YAML mantido à mão em config/
- **Licença:** Curadoria do projeto (dados factuais; fontes citadas)
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Fonte factual: https://ix.br/localidades/atuais (verificada manualmente em 2026-09-28).

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `ixps[].code` | str | Código curto do IXP (minúsculas; ex.: sp, rj, vix). | Chave de junção em todo o sistema. | ixp_docs → ixps/index.json#code |
| `ixps[].name / uf` | str | Cidade-sede e UF da localidade. | — | ixp_docs → ixps/index.json#name |
| `ixps[].telnet_host / telnet_port / timeout` | str\|int | Host e porta do Looking Glass e tempo máximo de leitura da tabela. | Operacional; não publicado. | — |
| `ixps[].cep` | str | CEP aproximado usado para posicionar a localidade. | Aproximação; PIX têm coordenadas próprias em pix.yaml. | — |

## Limites

Edição humana: nova localidade exige atualizar o arquivo e o frontend. Verificação manual datada.

## Retenção

- **normalizado:** git

## Quem usa

- **Fontes derivadas:** `curada_pix`
- **Produtos:** `ixp_docs`

## Pendências (nao_verificado)

- Licença/termos dos dados do IX.br.
