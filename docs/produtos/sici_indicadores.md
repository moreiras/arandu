<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Indicadores do SICI e outorgas sem declaração

`sici_indicadores` · produto

Share, HHI, variações, declínio contínuo e parada de declaração por operadora, UF e município; outorgas SCM sem acessos declarados, com os usuários estimados (APNIC) dos ASNs do CNPJ.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.sici_indicadores.build` |
| Chaves de junção | `cnpj`, `asn`, `ibge`, `uf`, `mes_referencia` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_sici](../fontes/anatel_sici.md) — uso comercial: `permitido`
- fonte [apnic_pop](../fontes/apnic_pop.md) — uso comercial: `nao_verificado`
- fonte [anatel_scm](../fontes/anatel_scm.md) — uso comercial: `permitido`
- fonte [socios_grupos](../fontes/socios_grupos.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `sici_indicadores.json.gz`, `sici_serie_municipio.json.gz`, `mercado_grupos.json.gz`, `omissao_sici.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `municipios[ibge].hhi_cnpj / hhi_grupo / faixa_cnpj / faixa_grupo; ufs[uf]; resumo.mudam_de_faixa` | int / str | HHI do mercado fixo por CNPJ e por grupo econômico (CNPJs do mesmo grupo contam como um) em cada município e UF, a faixa (competitivo, moderado, concentrado) e quantos municípios mudam de faixa. | INFERIDO (o grupo é inferência do quadro societário em comum); sobre acessos declarados, não receita; só `grupos[].cnpjs` e `grupo_id` são lidos, nenhum dado de sócio. | sici_indicadores → mercado_grupos.json.gz#municipios |
| `sobreposicao[cnpj][]` | list[dict] | As 10 operadoras que mais aparecem nos mesmos municípios, com municípios em comum e os acessos de cada lado ali. | Presença nos mesmos municípios, não rivalidade nem disputa de clientes. | sici_indicadores → mercado_grupos.json.gz#sobreposicao |
| `municipios[ibge].acessos / hhi / lideres[].share (série de 13 meses)` | list[int\|null] / list[int\|null] / list[float\|null] | Série mensal de acessos declarados, HHI e participação das 4 maiores operadoras do mês de referência, por município. | Sobre acessos declarados, não sobre receita; mês ausente do cache fica vazio (null), nunca zero; a operadora que ainda não existia no mês conta zero na participação. | sici_indicadores → sici_serie_municipio.json.gz#municipios |
| `operadoras[cnpj].share_br / posicao_br` | float / int | Parcela dos acessos fixos declarados no país e a posição por acessos. | Sobre acessos declarados, não sobre receita; dado declarado. | sici_indicadores → sici_indicadores.json.gz#operadoras |
| `operadoras[cnpj].var_mm / var_aa` | dict | Variação absoluta e percentual de acessos contra o mês anterior e contra o mesmo mês do ano anterior. | — | sici_indicadores → sici_indicadores.json.gz#operadoras |
| `operadoras[cnpj].meses_declinio / em_declinio` | int / bool | Meses seguidos de queda até o mês de referência; verdadeiro quando chega ao limite dos parâmetros. | — | sici_indicadores → sici_indicadores.json.gz#operadoras |
| `parou_de_declarar[cnpj]` | dict | CNPJ que declarou antes e está sem declaração há pelo menos a janela dos parâmetros. | Fato sobre a declaração (último mês declarado), sem causa. | sici_indicadores → sici_indicadores.json.gz#parou_de_declarar |
| `ufs[uf] / municipios[ibge] / brasil` | dict | Acessos, HHI, número de operadoras, líder, variações, ganho e perda do ano. | HHI sobre acessos declarados. | sici_indicadores → sici_indicadores.json.gz#municipios |
| `parametros` | dict | Janelas e limiares usados no cálculo. | — | sici_indicadores → sici_indicadores.json.gz#parametros |
| `itens[cnpj].classe / usuarios_apnic` | str / int | Outorga SCM sem acessos declarados no mês e a classe pelos usuários estimados dos ASNs do CNPJ. | Usuários APNIC são estimativa (medição estatística); a classe nao_comparavel é CNPJ sem ASN. | sici_indicadores → omissao_sici.json.gz#itens |
| `itens[cnpj].grupo_declara` | bool | Outro CNPJ do mesmo grupo societário declarou acessos no mês. | Evidência para quem lê a linha; grupo parcial não prova controle. | sici_indicadores → omissao_sici.json.gz#itens |
| `por_uf` | dict | Contagem por UF das outorgas sem declaração, por classe, e soma dos usuários estimados. | — | sici_indicadores → omissao_sici.json.gz#por_uf |
| `snapshot_date / mes_referencia` | str | Data do snapshot e mês de referência da declaração. | — | sici_indicadores → sici_indicadores.json.gz#mes_referencia; sici_indicadores → omissao_sici.json.gz#mes_referencia |
| `snapshot_date / generated_at / mes_referencia / natureza / fonte / limites / faixas / resumo / ufs` | str / dict | Cabeçalho do cruzamento de mercado: data do snapshot, mês de referência, natureza (inferido), fonte, limites, as faixas de HHI, o resumo de municípios que mudam de faixa e o HHI por UF. | — | sici_indicadores → mercado_grupos.json.gz#snapshot_date; sici_indicadores → mercado_grupos.json.gz#generated_at; sici_indicadores → mercado_grupos.json.gz#mes_referencia; sici_indicadores → mercado_grupos.json.gz#natureza; sici_indicadores → mercado_grupos.json.gz#fonte; sici_indicadores → mercado_grupos.json.gz#limites; sici_indicadores → mercado_grupos.json.gz#faixas; sici_indicadores → mercado_grupos.json.gz#resumo; sici_indicadores → mercado_grupos.json.gz#ufs |
| `snapshot_date / generated_at / mes_referencia / meses / fonte / parametros` | str / dict | Cabeçalho da série de participação por município: snapshot, mês de referência, os 13 meses da janela, fonte e parâmetros (meses e líderes). | — | sici_indicadores → sici_serie_municipio.json.gz#snapshot_date; sici_indicadores → sici_serie_municipio.json.gz#generated_at; sici_indicadores → sici_serie_municipio.json.gz#mes_referencia; sici_indicadores → sici_serie_municipio.json.gz#meses; sici_indicadores → sici_serie_municipio.json.gz#fonte; sici_indicadores → sici_serie_municipio.json.gz#parametros |
