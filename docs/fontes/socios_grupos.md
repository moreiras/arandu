<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Grupos societários entre operadoras (cruzamento do QSA)

`socios_grupos` · tipo **derivada** · ativa

Cruza o quadro societário das operadoras SCM/SMP/STFC/SeAC: propriedade direta entre CNPJs da base e sócios em comum, classificando relações em 'mesmo_grupo' (quadro idêntico ou controle exclusivo) e 'relacionadas_parcial'. Holdings externas têm o cadastro resolvido via BrasilAPI.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.socios_grupos.enrich` |
| Publicável | sim (exposição: aberta) |
| Política de falha | opcional |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | semanal → semanal |
| Frescor máximo | 8d |
| Chaves | `cnpj`, `grupo` |
| Entradas | `receita_socios`, `anatel_scm`, `anatel_smp`, `anatel_stfc`, `anatel_seac` |
| Amostra de teste | `tests/fixtures/raw/receita_socios/` |

## Origem e licença

- **URL:** https://brasilapi.com.br/api/cnpj/v1/{cnpj}
- **Formato:** JSON (holdings externas)
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://brasilapi.com.br/
- **Evidência / ressalvas:** Só para holdings externas à base; ver cnpj_geo. A base do quadro societário vem de receita_socios.

## Saídas

- **Normalizado (normalized/):** `summary/grupos_societarios.json.gz`, `../holdings_cache/cartoes.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `grupos[].grupo_id` | str | Identificador do grupo (determinístico a partir dos CNPJs básicos ordenados). | — | grupos_societarios → grupos_societarios.json.gz#grupos |
| `grupos[].classificacao` | str | Rótulo do tipo de relação que formou o grupo. | Inferido; transitividade não é aplicada dentro do grupo. | grupos_societarios → grupos_societarios.json.gz#grupos |
| `by_cnpj[cnpj].mesmo_grupo` | list | CNPJs com quadro de sócios idêntico ou controlador exclusivo. | Relação TOTAL, não inferida por transitividade. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].relacionadas_parcial` | list[dict] | CNPJs com sócios em comum, com a contagem e os nomes dos sócios PJ em comum (pessoa física só conta). | PARCIAL: pode haver falso positivo por colisão de nome + CPF mascarado. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].holdings_externas` | list[dict] | Cadastro completo (BrasilAPI) das controladoras fora do universo de outorgas. | — | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj[cnpj].socios` ⚠️ dado pessoal/contato | list[dict] | Quadro de sócios do CNPJ; nome e CNPJ básico só de sócio PJ. | LGPD: sócio pessoa física ou estrangeiro sai só com tipo e qualificação, sem nome nem CPF (core.cpf.sem_socios_pessoa_fisica). | grupos_societarios → grupos_societarios.json.gz#by_cnpj |

## Limites

CPF mascarado pela Receita: nomes comuns podem colidir (falso positivo). Sócio indireto/oculto não aparece. 'Grupo' é hipótese baseada em quadro societário, não afirmação sobre controle econômico.

## Retenção

- **normalizado:** 52 semanas

## Quem usa

- **Produtos:** `grupos_societarios`, `sici_indicadores`

## Pendências (nao_verificado)

- Nome de sócio PF não é gravado nem servido; o cruzamento continua usando nome + CPF mascarado em memória.
- Linguagem de evidência antes de qualquer afirmação sobre empresas.
