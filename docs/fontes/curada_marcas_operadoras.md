<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Marca → raiz do CNPJ (config/curada_marcas_operadoras.yaml)

`curada_marcas_operadoras` · tipo **curada** · ativa

Tabela curada que liga o nome da marca ou da prestadora, como aparece no RQUAL e nas reclamações da Anatel, à raiz do CNPJ (8 dígitos). Feita à mão com a razão social e o nome fantasia das outorgas da Anatel e os grupos do SICI; marca fora da tabela só casa por nome fantasia único (regra automática, rotulada) e, sem casamento, fica sem CNPJ. Usada também pelo Consumidor.gov.br.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `config/curada_marcas_operadoras.yaml` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | irregular |
| Coleta hoje → alvo | semanal → sob_demanda |
| Frescor máximo | 400d |
| Chaves | `cnpj` |
| Entradas | `anatel_scm`, `anatel_smp`, `anatel_stfc`, `anatel_seac` |

## Origem e licença

- **URL:** —
- **Formato:** YAML mantido à mão em config/
- **Licença:** Curadoria do projeto (dados públicos; nada de pessoa física)
- **Uso comercial:** `permitido`
- **Evidência / ressalvas:** Criada em 2026-11-06 sobre as outorgas do snapshot 2026-11-05. Cada linha traz a base do vínculo (razão social ou grupo do SICI). Correções pelo contato do site, na página Sobre (política editorial).

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `marcas[].marca / raizes / base` | str / lista / str | Marca como na fonte, raízes de CNPJ (8 dígitos) a que ela se liga e o que sustenta o vínculo. | Uma marca pode ter várias raízes (grupo econômico). Casamento sempre rotulado como curado ou automático; sem casamento a marca fica sem CNPJ. | qualidade → qualidade/rqual.json.gz#prestadoras; qualidade → qualidade/reclamacoes.json.gz#marcas |

## Limites

Cobre as marcas de maior volume e as do RQUAL; as demais só casam por nome fantasia único. O grupo econômico da marca pode ser maior do que as raízes listadas.

## Retenção

- **normalizado:** git
