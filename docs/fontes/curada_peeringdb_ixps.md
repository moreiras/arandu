<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# IXPs consultados no PeeringDB (config/peeringdb_ixps.yaml)

`curada_peeringdb_ixps` · tipo **curada** · ativa

IDs de IX do PeeringDB (pdb_ix_id) dos IXPs externos exibidos e dos IXPs do IX.br usados no cruzamento.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `config/peeringdb_ixps.yaml` |
| Publicável | sim (exposição: aberta) |
| Política de falha | critica |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → sob_demanda |
| Frescor máximo | 400d |
| Chaves | `ixp`, `pais` |
| Entradas | — |

## Origem e licença

- **URL:** —
- **Formato:** YAML mantido à mão em config/
- **Licença:** Curadoria do projeto (dados factuais; fontes citadas)
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** IDs validados em 2026-06-09 via GET /api/ix do PeeringDB.

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `external[].code / name / city / country` | str | Identificação do IXP externo exibido. | — | ixp_docs → external-ixps/{ixp}.json |
| `external[].pdb_ix_id` | int | Identificador do IX no PeeringDB. | — | ixp_docs → external-ixps/{ixp}.json#pdb_ix_id |
| `ixbr[]` | list | IXPs do IX.br com ID no PeeringDB, para cruzamento do cadastro. | Operacional. | — |

## Limites

IDs podem mudar no PeeringDB; revalidar periodicamente.

## Retenção

- **normalizado:** git

## Quem usa

- **Fontes derivadas:** `peeringdb_ixps`
- **Produtos:** `ixp_docs`

## Pendências (nao_verificado)

- IDs vêm do PeeringDB (AUP); ver peeringdb_ixps.
