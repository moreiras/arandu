<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Penetração de banda larga fixa e mercado não visto

`penetracao` · produto

Acessos fixos declarados (SICI) sobre os domicílios do Censo 2022 projetados pelo crescimento de domicílios da UF na PNAD, por município, UF e país, e uma estimativa do mercado não visto (domicílios com internet pela PNAD menos acessos de pessoa física).

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.penetracao.build` |
| Chaves de junção | `ibge`, `uf` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [ibge_censo_pnad](../fontes/ibge_censo_pnad.md) — uso comercial: `nao_verificado`
- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`

## Saídas

- **Publicado:** `territorio/municipios.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge].domicilios_projetados / fator_projecao_uf` | int / float | Domicílios do Censo 2022 × crescimento de domicílios da UF entre 2022 e o ano mais recente da PNAD. | PROJEÇÃO. Supõe o mesmo crescimento em todos os municípios da UF; sem a série da PNAD fica no nível do Censo e sem o fator. | penetracao → territorio/municipios.json.gz#municipios |
| `municipios[ibge].penetracao / penetracao_pf / penetracao_censo` | float | Acessos fixos declarados (e só os de pessoa física) por domicílio projetado; `penetracao_censo` usa os domicílios do Censo, sem projeção. | Acesso não é domicílio; pode passar de 1. Ausente quando o município não tem domicílios no IBGE. | penetracao → territorio/municipios.json.gz#municipios |
| `municipios[ibge].nao_visto / nao_visto_pct / domicilios_com_internet_est` | int / float | max(0, domicílios projetados × taxa de internet da UF − acessos de pessoa física); a taxa é a da PNAD ("havia utilização de internet"). | ESTIMATIVA. Inclui quem usa só o celular; a taxa é da UF aplicada ao município. Fórmula e limites no próprio artefato. | penetracao → territorio/municipios.json.gz#municipios |
| `ufs[uf] / brasil` | dict | Soma dos municípios e a taxa da PNAD com o coeficiente de variação da UF. | — | penetracao → territorio/municipios.json.gz#ufs |
| `casamento` | dict | Quantos municípios do SICI casaram com o IBGE e quais ficaram sem código no IBGE. | — | penetracao → territorio/municipios.json.gz#casamento |
| `limites / formulas` | str / dict | Texto das limitações e as fórmulas usadas. | — | penetracao → territorio/municipios.json.gz#limites |
