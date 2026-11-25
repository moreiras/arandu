# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Catálogo da camada de consulta (separado de `api/query.py` para manter os arquivos abaixo de 800 linhas): macro-região por UF, operadores,
`COLLECTIONS`, o schema de cada collection (`SCHEMA`), o guia de operadores e as receitas (pergunta → ferramentas).

Só dados e descrições; a validação e a avaliação ficam em `api/query.py`, que reexporta estes nomes (`api.query.SCHEMA`, `api.query.RECIPES`…).
"""
from __future__ import annotations

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Região por UF (macro-região do IBGE)
# ---------------------------------------------------------------------------

REGION_BY_UF: dict[str, str] = {
    # Norte
    "AC": "N", "AM": "N", "AP": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    # Nordeste
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE",
    "PI": "NE", "RN": "NE", "SE": "NE",
    # Centro-Oeste
    "DF": "CO", "GO": "CO", "MS": "CO", "MT": "CO",
    # Sudeste
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    # Sul
    "PR": "S", "RS": "S", "SC": "S",
}

# ---------------------------------------------------------------------------
# Operadores e funções de agregação suportados
# ---------------------------------------------------------------------------

_OPS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "nin", "contains", "ncontains",
        "exists", "within_radius"}
_AGG_FNS = {"count", "sum", "avg", "min", "max", "distinct"}


# ---------------------------------------------------------------------------
# Catálogo de schema — descreve cada collection para descoberta (LLM/dev)
# ---------------------------------------------------------------------------

COLLECTIONS = ("asns", "ixps", "external_ixps", "cdns", "prefixes",
               "global_prefixes", "scms", "operadoras", "acessos_municipio",
               "smps", "operadoras_movel", "acessos_movel_municipio", "socios", "stfcs", "seacs", "eventos", "series_asn", "indicadores_operadora", "sem_declaracao_sici", "municipios", "seguranca_asn", "rs_sessoes", "rs_communities", "rs_filtradas", "cetic_indicadores", "cetic_estimativas_uf", "demanda_oferta", "erbs_municipio", "fust_municipio", "prontidao_agregado", "prontidao_asn", "multas_empresa", "faixas_espectro", "satelites_direitos", "transferencias_ipv4", "recuperacao_ipv4", "eventos_bloco", "espaco_ipv4", "uso_por_terceiros_ipv4", "subasignacoes_ipv4", "organizacoes_asn", "qualidade_uf", "reclamacoes_marca", "consumidor_marca", "bloqueios_asn")

COLLECTIONS += ("transito_uf", "transito_asn")      # trânsito por UF e cone de clientes
COLLECTIONS += ("facilities", "facilidades_rede", "redes_peering")      # instalações do PeeringDB e atributos de peering

#: nomes antigos de collection (D12) → nome atual. A consulta por um nome antigo roda na collection nova e a resposta traz `aviso_obsoleta`.
COLECOES_ALIAS = {"omissao_sici": "sem_declaracao_sici"}


def aviso_colecao_obsoleta(antigo: str) -> str:
    return (f"A collection `{antigo}` foi renomeada para `{COLECOES_ALIAS[antigo]}` (D12); o nome antigo segue como alias por um período e será "
            f"removido depois de duas versões. Use `{COLECOES_ALIAS[antigo]}`.")


# Frase do índice do `describe_schema` quando a primeira frase da descrição, cortada em 140 caracteres, perderia o aviso do mês de
# referência do SICI (TRANSV-E17). Cada uma cabe em 140 e repete o aviso que a descrição completa traz.
RESUMO_INDICE = {
    "operadoras": "Operadoras de banda larga por CNPJ (outorga SCM, acessos SICI, ASNs). Acessos do mês de referência do SICI, NÃO da data do snapshot",
    "operadoras_movel": "Operadoras móveis por CNPJ (outorga SMP, acessos SICI, ASNs). Acessos do mês de referência do SICI, NÃO da data do snapshot",
    "indicadores_operadora": "Indicadores do SICI fixo por CNPJ: share, posição, variação, meses de queda. Mês de referência do SICI, NÃO a data do snapshot",
    "municipios": "Uma linha por município do IBGE: população, domicílios, acessos SICI, penetração, PTT próximo. Acessos do mês de referência do SICI",
}

# Sentinela para distinguir "sem exemplo" de "exemplo é None/false".
_MISSING_SENTINEL = object()

_REGIONS = ["N", "NE", "CO", "SE", "S"]
_PORTES = ["MICRO EMPRESA", "EMPRESA DE PEQUENO PORTE", "DEMAIS"]


def _f(name: str, type_: str, desc: str, *, enum: Optional[list] = None,
       example: Any = _MISSING_SENTINEL) -> dict:
    """Descreve um campo consultável. `enum` lista o domínio fechado (quando há);
    `example` dá um valor concreto — ambos ajudam a LLM a montar filtros válidos."""
    d: dict = {"name": name, "type": type_, "description": desc}
    if enum is not None:
        d["enum"] = enum
    if example is not _MISSING_SENTINEL:
        d["example"] = example
    return d


SCHEMA: dict[str, dict] = {
    "asns": {
        "key": "asn",
        "description": "Sistemas Autônomos (índice compacto + geo + membership em IXPs). Endereço e posição da sede não são servidos; o filtro `near` usa a posição por dentro.",
        "fields": [
            _f("asn", "int", "Número do AS", example=28604),
            _f("name", "string", "Nome do AS", example="Globo Comunicacao"),
            _f("is_br", "bool", "Registrado no Registro.br/LACNIC (BR)", example=True),
            _f("has_ipv6", "bool", "Possui prefixos IPv6 observados", example=True),
            _f("has_rpki", "bool", "Possui ao menos uma ROA (RPKI)", example=True),
            _f("has_aspa", "bool", "Possui ao menos um objeto ASPA publicado no RPKI", example=False),
            _f("rir_prefixes_v4_count", "int", "Prefixos IPv4 atribuídos pelo RIR"),
            _f("rir_prefixes_v6_count", "int", "Prefixos IPv6 atribuídos pelo RIR"),
            _f("global_prefixes_v4_count", "int", "Prefixos IPv4 na full table global"),
            _f("global_prefixes_v6_count", "int", "Prefixos IPv6 na full table global"),
            _f("ixps_direct_count", "int", "Nº de IXPs IX.br onde faz peering direto"),
            _f("ixps_origin_count", "int", "Nº de IXPs onde origina prefixos"),
            _f("ixps_origin_v4_count", "int", "Idem, IPv4"),
            _f("ixps_origin_v6_count", "int", "Idem, IPv6"),
            _f("external_ixps_count", "int", "Nº de PTTs externos onde é membro"),
            _f("apnic_users", "number", "Usuários finais estimados (APNIC), ou null"),
            _f("apnic_v6_users", "number", "Usuários IPv6 estimados (APNIC), ou null"),
            _f("pct_v6", "number", "% de usuários via IPv6 (APNIC), ou null"),
            _f("space_v4", "int", "Espaço IPv4 (endereços) global"),
            _f("space_v6", "int", "Espaço IPv6 (/64s) global"),
            _f("uf", "string", "UF da organização (via CNPJ→geo), ou null. Sigla de 2 letras MAIÚSCULAS", example="SP"),
            _f("city", "string", "Município da organização, ou null. Compare com `contains` (case-insensitive)", example="Vitória"),
            _f("region", "string", "Macro-região (IBGE), ou null", enum=_REGIONS),
            _f("cnpj", "string", "CNPJ do responsável (ASNs BR), ou null"),
            _f("cnpj_root", "string", "Raiz do CNPJ (8 primeiros dígitos) — agrupa filiais/ASNs da mesma empresa. Use em group_by para somar por organização"),
            _f("razao_social", "string", "Razão social"),
            _f("nome_fantasia", "string", "Nome fantasia, ou null"),
            _f("cnae", "string", "Atividade econômica principal (descrição CNAE). Use em group_by para agregar por tipo de empresa", example="Provedores de acesso às redes de comunicações"),
            _f("cnae_code", "int", "Código CNAE principal", example=6190601),
            _f("porte", "string", "Porte da empresa (CNPJ). Domínio fechado", enum=_PORTES),
            _f("natureza_juridica", "string", "Natureza jurídica (CNPJ)", example="Sociedade Empresária Limitada"),
            _f("ixps_direct", "array[string]", "Códigos dos IXPs IX.br onde é membro direto. Teste pertinência com `contains`/`ncontains` (ex.: contains \"sp\")", example=["sp", "rj"]),
            _f("ixps_origin", "array[string]", "Códigos dos IXPs onde origina prefixos BR. Teste com `contains`/`ncontains`", example=["sp"]),
        ],
        "geo": {"lat": "lat", "lon": "lon"},
    },
    "ixps": {
        "key": "code",
        "description": "PTTs do IX.br (os de config/ixps.yaml). Métricas por AFI acessíveis por dot-path: v4.*, v6.*",
        "fields": [
            _f("code", "string", "Código do IXP (minúsculo). Manaus=mao, Palmas=to, Vitória=vix, SP=sp, RJ=rj", example="sp"),
            _f("name", "string", "Nome/cidade do IXP"),
            _f("uf", "string", "UF", example="SP"),
            _f("status", "string", "Status de coleta", enum=["ok", "partial", "missing"]),
            _f("ixbr_members_count", "int", "Membros oficiais IX.br"),
            _f("asn_direct_union_count", "int", "ASes diretos (união v4∪v6)"),
            _f("asn_origin_union_count", "int", "ASes originadores, todos os países (união IPv6 ∪ IPv4; até 2026-11 era o maior dos dois)"),
            _f("br_asns_direct_union_count", "int", "ASes BR diretos (união)"),
            _f("br_asns_origin_union_count", "int", "ASes BR originadores (união)"),
            _f("v4.unique_prefixes", "int", "Prefixos IPv4 únicos anunciados"),
            _f("v4.br_prefix_coverage_pct", "number", "% do espaço BR (RIR) visível aqui (v4)"),
            _f("v4.ixp_vs_fulltable_space_pct", "number", "% do espaço global coberto (v4)"),
            _f("v6.unique_prefixes", "int", "Prefixos IPv6 únicos anunciados"),
            _f("v6.br_prefix_coverage_pct", "number", "% do espaço BR (RIR) visível aqui (v6)"),
        ],
    },
    "external_ixps": {
        "key": "code",
        "description": "PTTs externos ao IX.br (PeeringDB). Lista de membros via get_external_ixp.",
        "fields": [
            _f("code", "string", "Código do PTT externo (ex.: amsix)", example="amsix"),
            _f("name", "string", "Nome"),
            _f("city", "string", "Cidade"),
            _f("country", "string", "País (ISO 3166-1 alfa-2)", example="BR"),
            _f("redes", "int", "Redes (ASNs distintos) declaradas no PTT pelo PeeringDB"),
            _f("redes_br", "int", "Redes brasileiras (ASNs is_br, delegação LACNIC) declaradas no PTT"),
            _f("portas", "int", "Portas declaradas (linhas netixlan do PeeringDB); uma rede pode ter várias"),
            _f("member_count", "int", "Alias de `redes` (ASNs distintos; até 2026-11 contava portas)"),
            _f("br_member_count", "int", "Alias de `redes_br` (até 2026-11 contava portas)"),
            _f("pdb_ix_id", "int", "ID no PeeringDB"),
            _f("rs_sessoes_up", "int", "DE-CIX (decix-sp, decix-rj): sessões BGP up nos route servers (Alice-LG); nulo nos demais PTTs"),
            _f("rs_asn_direct_count", "int", "DE-CIX: ASNs com sessão up no route server (multilateral); nulo nos demais"),
            _f("rs_asn_origin_count", "int", "DE-CIX: ASNs de origem das rotas lidas por vizinho em rodízio (um piso, leitura parcial); nulo nos demais"),
        ],
    },
    "cdns": {
        "key": "name",
        "description": "CDNs/CAPs e sua presença nos IXPs (IX.br e externos).",
        "fields": [
            _f("name", "string", "Nome da CDN/CAP"),
            _f("asns", "array[int]", "ASNs da CDN/CAP"),
            _f("ixbr", "array[string]", "Códigos de IXPs do IX.br onde está presente"),
            _f("external", "array[string]", "Códigos de PTTs externos onde está presente"),
            _f("ixbr_count", "int", "Nº de IXPs IX.br"),
            _f("external_count", "int", "Nº de PTTs externos"),
        ],
    },
    "prefixes": {
        "key": "prefix",
        "description": "Prefixos BR (Registro.br) com UF e país. Latitude, longitude e cidade por prefixo não são servidas.",
        "fields": [
            _f("prefix", "string", "CIDR", example="177.75.0.0/20"),
            _f("ip_version", "int", "Versão IP", enum=[4, 6]),
            _f("origin_asn", "int", "AS a que o Registro.br associa o prefixo (detentor; não é a origem observada, que está em "
               "global_prefixes e em rota_prefixo)", example=28178),
            _f("uf", "string", "UF"),
            _f("country", "string", "País"),
            _f("geo_confidence", "string", "Confiança da geolocalização"),
            _f("geo_source", "string", "Fonte da geolocalização"),
        ],
    },
    "global_prefixes": {
        "key": "prefix",
        "description": (
            "Todos os prefixos únicos anunciados em qualquer IXP do IX.br, "
            "com o país (base DB-IP City Lite) e a lista dos IXPs onde foram observados. "
            "Cobre ~210k IPv4 + ~97k IPv6 — inclui prefixos não-BR. Latitude, longitude e cidade por prefixo não são servidas; "
            "o filtro `near` usa a posição por dentro."
        ),
        "fields": [
            _f("prefix", "string", "CIDR", example="8.8.8.0/24"),
            _f("ip_version", "int", "Versão IP", enum=[4, 6]),
            _f("origin_asn", "int", "ASN originador (último AS do caminho)", example=15169),
            _f("ixps_seen", "array[string]",
               "Códigos dos IXPs IX.br onde este prefixo foi observado. "
               "Use contains/ncontains (ex.: contains \"sp\")", example=["sp", "rj"]),
            _f("country", "string", "País do prefixo (DB-IP City Lite, ISO 3166-1 alfa-2)", example="IN"),
            _f("geo_confidence", "string", "Confiança da geolocalização",
               enum=["city_centroid", "unknown"]),
            _f("geo_source", "string", "Versão da base de geolocalização", example="dbip-lite-2026-10"),
        ],
        "geo": {"lat": "lat", "lon": "lon"},
    },
    "scms": {
        "key": "cnpj",
        "description": (
            "Outorgas do Serviço de Comunicação Multimídia (SCM) da Anatel, "
            "geolocalizadas e cruzadas com ASNs do Registro.br por CNPJ. Endereço e posição da sede não são servidos "
            "(ficam município e UF); o filtro `near` usa a posição por dentro."
        ),
        "fields": [
            _f("cnpj", "string", "CNPJ da operadora (14 dígitos)", example="12345678000190"),
            _f("razao_social", "string", "Razão social"),
            _f("nome_fantasia", "string", "Nome fantasia, ou vazio"),
            _f("data_outorga", "string", "Data de outorga (formato ANATEL, ex: 2010-05-15)"),
            _f("municipio", "string", "Município", example="São Paulo"),
            _f("uf", "string", "UF (sigla de 2 letras MAIÚSCULAS)", example="SP"),
            _f("codigo_ibge", "string", "Código do município no IBGE"),
            _f("situacao", "string", "Situação da outorga (ex: ATI=ativa, EXT=extinta)",
               enum=["ATI", "EXT", "SUS", "REV", "CAN"]),
            _f("asns", "array[int]",
               "ASNs do Registro.br com mesmo CNPJ. Use contains/ncontains para filtragem.",
               example=[12345]),
            _f("geo_confidence", "string", "Confiança da geolocalização",
               enum=["exact_address", "cep_centroid", "city_centroid", "unknown"]),
        ],
        "geo": {"lat": "lat", "lon": "lon"},
    },
    "operadoras": {
        "key": "cnpj",
        "description": (
            "Operadoras de banda larga, uma linha por CNPJ: cadastro da outorga SCM "
            "cruzado com os acessos declarados mensalmente à Anatel (SICI) e com os "
            "ASNs do Registro.br. Diferente de `scms`, que tem uma linha por OUTORGA. "
            "Inclui licenciados que não declaram operação (ativo=false) — metade da "
            "base. Os números são do mês de referência do SICI, que NÃO é a data do "
            "snapshot: cite as duas. A posição da sede não é servida; o filtro `near` usa a posição por dentro."
        ),
        "fields": [
            _f("cnpj", "string", "CNPJ da operadora (14 dígitos)", example="04573288000144"),
            _f("empresa", "string", "Nome comercial declarado ao SICI", example="PAINSONLINE"),
            _f("razao_social", "string", "Razão social (cadastro da outorga SCM)"),
            _f("nome_fantasia", "string", "Nome fantasia (cadastro da outorga SCM)"),
            _f("grupo_economico", "string",
               "Grupo econômico do SICI. Só 24 valores: consolida os grandes "
               "(OI, TELEFONICA, TELECOM AMERICAS...), e 'OUTROS' cobre 99,7% dos "
               "CNPJs — não serve como agrupador geral.", example="OUTROS"),
            _f("porte", "string", "Porte declarado da prestadora",
               enum=["Pequeno Porte", "Grande Porte"]),
            _f("uf_sede", "string", "UF da sede (cadastro SCM). NÃO é onde estão os "
               "clientes — para isso use a collection acessos_municipio.", example="MG"),
            _f("municipio_sede", "string", "Município da sede (cadastro SCM)"),
            _f("licenciado", "bool", "Tem outorga SCM na Anatel"),
            _f("ativo", "bool", "Declarou ao menos um acesso no mês de referência"),
            _f("acessos", "int", "Acessos em serviço no mês de referência", example=955),
            _f("acessos_pf", "int", "Acessos de Pessoa Física (B2C)"),
            _f("acessos_pj", "int", "Acessos de Pessoa Jurídica (B2B)"),
            _f("capacidade_mbps", "number",
               "Capacidade CONTRATADA (soma de velocidade × acessos), em Mbps. "
               "Não é capacidade de trânsito nem de backhaul."),
            _f("velocidade_media_mbps", "number", "Velocidade média contratada"),
            _f("velocidade_mediana_mbps", "number",
               "Mediana ponderada — preferível à média, que é distorcida por links "
               "de backbone declarados como acesso."),
            _f("municipios", "int", "Municípios atendidos"),
            _f("tecnologia", "string", "Tecnologia predominante", example="FTTH"),
            _f("meio", "string", "Meio de acesso predominante",
               enum=["Fibra", "Cabo Coaxial", "Rádio", "Satélite", "Cabo Metálico"]),
            _f("asns", "array[int]",
               "ASNs do Registro.br com o mesmo CNPJ (fato). Os ligados pela raiz ou pela marca estão em asns_vinculados. Use contains/ncontains.",
               example=[265394]),
            _f("asn_vinculo", "string",
               "Vínculo mais forte do CNPJ com algum ASN (decisão D5): cnpj = ASN registrado no Registro.br com o mesmo CNPJ (fato); "
               "raiz = com outro CNPJ da mesma raiz de 8 dígitos, matriz ou filial (inferido); marca = com a raiz de outra empresa da "
               "mesma marca na tabela curada (inferido); estrangeiro = AS de fora do Brasil ligado pela marca (inferido, ex.: Starlink); "
               "nenhum.", enum=["cnpj", "raiz", "marca", "estrangeiro", "nenhum"]),
            _f("asns_vinculados", "array[int]",
               "Todos os ASNs ligados ao CNPJ por qualquer vínculo de asn_vinculo (inclui os de `asns`). Use contains/ncontains."),
            _f("com_asn", "bool", "Tem ASN brasileiro vinculado: asn_vinculo é cnpj, raiz ou marca (estrangeiro e nenhum = falso)"),
            _f("acessos_compartilhados", "bool",
               "CNPJ com mais de um ASN: o total é atribuído integralmente a CADA um. "
               "NUNCA some ASes do mesmo CNPJ — conta o mesmo assinante várias vezes."),
            _f("outorgas", "int", "Número de outorgas SCM do CNPJ"),
            _f("mes_referencia", "string", "Mês da declaração ao SICI", example="2026-07"),
        ],
        "geo": {"lat": "lat", "lon": "lon"},
    },
    "acessos_municipio": {
        "key": "ibge",
        "description": (
            "Uma linha por (município, operadora): quantos acessos aquela operadora "
            "tem naquele município, com share e concentração. É a collection para "
            "'quem atende a cidade X', 'onde o operador Y está', 'municípios com "
            "pouca competição'."
        ),
        "fields": [
            _f("ibge", "string", "Código IBGE do município (7 dígitos)", example="3550308"),
            _f("municipio", "string", "Nome do município", example="São Paulo"),
            _f("uf", "string", "UF (2 letras MAIÚSCULAS)", example="SP"),
            _f("cnpj", "string", "CNPJ da operadora"),
            _f("empresa", "string", "Nome comercial da operadora"),
            _f("acessos", "int", "Acessos DESTA operadora NESTE município"),
            _f("share", "number", "Participação da operadora no município (%)"),
            _f("asns", "array[int]", "ASNs da operadora. Use contains/ncontains."),
            _f("asn_vinculo", "string",
               "Vínculo mais forte do CNPJ com algum ASN (decisão D5): cnpj = ASN registrado no Registro.br com o mesmo CNPJ (fato); "
               "raiz = com outro CNPJ da mesma raiz de 8 dígitos, matriz ou filial (inferido); marca = com a raiz de outra empresa da "
               "mesma marca na tabela curada (inferido); estrangeiro = AS de fora do Brasil ligado pela marca (inferido, ex.: Starlink); "
               "nenhum.", enum=["cnpj", "raiz", "marca", "estrangeiro", "nenhum"]),
            _f("asns_vinculados", "array[int]",
               "Todos os ASNs ligados ao CNPJ por qualquer vínculo de asn_vinculo (inclui os de `asns`). Use contains/ncontains."),
            _f("com_asn", "bool", "A operadora tem ASN brasileiro vinculado: asn_vinculo é cnpj, raiz ou marca"),
            _f("mes_referencia", "string", "Mês da declaração ao SICI (AAAA-MM) de que vêm os acessos", example="2026-09"),
            _f("municipio_acessos", "int", "Total de acessos do município (todas)"),
            _f("municipio_operadores", "int", "Quantas operadoras atendem o município"),
            _f("municipio_hhi", "int",
               "Concentração do município (HHI): 10000 = monopólio, <1500 = "
               "competitivo. Atenção: operadoras de satélite atendem todos os 5.570 "
               "municípios, então nenhum tem operador único."),
        ],
    },
    "smps": {
        "key": "cnpj",
        "description": (
            "Outorgas do Serviço Móvel Pessoal (SMP) da Anatel, geolocalizadas e "
            "cruzadas com ASNs do Registro.br por CNPJ. Universo pequeno (~30 CNPJs): "
            "as grandes operadoras móveis e MVNOs/M2M. Mesmo formato de `scms` (sem endereço nem posição da sede)."
        ),
        "fields": [
            _f("cnpj", "string", "CNPJ da operadora (14 dígitos)", example="02558157000162"),
            _f("razao_social", "string", "Razão social"),
            _f("nome_fantasia", "string", "Nome fantasia, ou vazio"),
            _f("data_outorga", "string", "Data de outorga"),
            _f("municipio", "string", "Município (sede da outorga)", example="São Paulo"),
            _f("uf", "string", "UF (sigla de 2 letras MAIÚSCULAS)", example="SP"),
            _f("codigo_ibge", "string", "Código do município no IBGE"),
            _f("situacao", "string", "Situação da outorga"),
            _f("asns", "array[int]",
               "ASNs do Registro.br com mesmo CNPJ. Use contains/ncontains.",
               example=[26599]),
            _f("geo_confidence", "string", "Confiança da geolocalização",
               enum=["exact_address", "cep_centroid", "city_centroid", "unknown"]),
        ],
        "geo": {"lat": "lat", "lon": "lon"},
    },
    "operadoras_movel": {
        "key": "cnpj",
        "description": (
            "Operadoras móveis, uma linha por CNPJ: cadastro da outorga SMP cruzado "
            "com os acessos móveis declarados mensalmente à Anatel (SICI) e com os "
            "ASNs do Registro.br. Espelha `operadoras`, mas para o universo móvel "
            "(bem menor, majoritariamente disjunto do de SCM). `acessos` já exclui "
            "M2M e PONTO_DE_SERVICO — só linhas pessoais/corporativas de voz/dados."
        ),
        "fields": [
            _f("cnpj", "string", "CNPJ da operadora (14 dígitos)"),
            _f("empresa", "string", "Nome comercial declarado ao SICI", example="VIVO"),
            _f("razao_social", "string", "Razão social (cadastro da outorga SMP)"),
            _f("grupo_economico", "string", "Grupo econômico do SICI", example="TELEFONICA"),
            _f("porte", "string", "Porte declarado da prestadora"),
            _f("uf_sede", "string", "UF da sede (cadastro SMP)"),
            _f("municipio_sede", "string", "Município da sede (cadastro SMP)"),
            _f("licenciado", "bool", "Tem outorga SMP na Anatel"),
            _f("ativo", "bool", "Declarou ao menos um acesso móvel no mês de referência"),
            _f("acessos", "int", "Acessos móveis padrão (voz/dados de linha pessoal) "
               "no mês de referência — exclui M2M e PONTO_DE_SERVICO"),
            _f("acessos_pf", "int", "Acessos de Pessoa Física (B2C)"),
            _f("acessos_pj", "int", "Acessos de Pessoa Jurídica (B2B)"),
            _f("acessos_m2m", "int", "Chips M2M (máquina a máquina), à parte do total"),
            _f("municipios", "int", "Municípios atendidos"),
            _f("geracao_predominante", "string", "Geração de rede predominante",
               enum=["2G", "3G", "4G", "5G"]),
            _f("asns", "array[int]", "ASNs do Registro.br com o mesmo CNPJ.",
               example=[27699]),
            _f("asn_vinculo", "string",
               "Vínculo mais forte do CNPJ com algum ASN (decisão D5): cnpj = ASN registrado no Registro.br com o mesmo CNPJ (fato); "
               "raiz = com outro CNPJ da mesma raiz de 8 dígitos, matriz ou filial (inferido); marca = com a raiz de outra empresa da "
               "mesma marca na tabela curada (inferido); estrangeiro = AS de fora do Brasil ligado pela marca (inferido, ex.: Starlink); "
               "nenhum.", enum=["cnpj", "raiz", "marca", "estrangeiro", "nenhum"]),
            _f("asns_vinculados", "array[int]",
               "Todos os ASNs ligados ao CNPJ por qualquer vínculo de asn_vinculo (inclui os de `asns`). Use contains/ncontains."),
            _f("com_asn", "bool", "Tem ASN brasileiro vinculado: asn_vinculo é cnpj, raiz ou marca (estrangeiro e nenhum = falso)"),
            _f("acessos_compartilhados", "bool",
               "CNPJ com mais de um ASN: o total é atribuído integralmente a CADA um. "
               "NUNCA some ASes do mesmo CNPJ."),
            _f("outorgas", "int", "Número de outorgas SMP do CNPJ"),
            _f("mes_referencia", "string", "Mês da declaração ao SICI", example="2026-07"),
        ],
        "geo": {"lat": "lat", "lon": "lon"},
    },
    "acessos_movel_municipio": {
        "key": "ibge",
        "description": (
            "Uma linha por (município, operadora móvel): quantos acessos móveis "
            "aquela operadora tem naquele município, com share e concentração. "
            "Espelha `acessos_municipio`, mas para SMP."
        ),
        "fields": [
            _f("ibge", "string", "Código IBGE do município (7 dígitos)"),
            _f("municipio", "string", "Nome do município"),
            _f("uf", "string", "UF (2 letras MAIÚSCULAS)"),
            _f("cnpj", "string", "CNPJ da operadora"),
            _f("empresa", "string", "Nome comercial da operadora"),
            _f("acessos", "int", "Acessos móveis DESTA operadora NESTE município"),
            _f("share", "number", "Participação da operadora no município (%)"),
            _f("asns", "array[int]", "ASNs da operadora. Use contains/ncontains."),
            _f("asn_vinculo", "string",
               "Vínculo mais forte do CNPJ com algum ASN (decisão D5): cnpj = ASN registrado no Registro.br com o mesmo CNPJ (fato); "
               "raiz = com outro CNPJ da mesma raiz de 8 dígitos, matriz ou filial (inferido); marca = com a raiz de outra empresa da "
               "mesma marca na tabela curada (inferido); estrangeiro = AS de fora do Brasil ligado pela marca (inferido, ex.: Starlink); "
               "nenhum.", enum=["cnpj", "raiz", "marca", "estrangeiro", "nenhum"]),
            _f("asns_vinculados", "array[int]",
               "Todos os ASNs ligados ao CNPJ por qualquer vínculo de asn_vinculo (inclui os de `asns`). Use contains/ncontains."),
            _f("com_asn", "bool", "A operadora tem ASN brasileiro vinculado: asn_vinculo é cnpj, raiz ou marca"),
            _f("municipio_acessos", "int", "Total de acessos móveis do município (todas)"),
            _f("municipio_operadores", "int", "Quantas operadoras atendem o município"),
            _f("municipio_hhi", "int", "Concentração do município (HHI)."),
        ],
    },
    "socios": {
        "key": "cnpj",
        "description": (
            "Cruzamento de quadro societário entre operadoras (SCM/SMP/STFC/SeAC) "
            "a partir do arquivo de Sócios dos dados abertos de CNPJ da Receita "
            "Federal. Uma linha por CNPJ que tem ALGUMA relação societária "
            "detectada com outra operadora da base — CNPJs sem sócio em comum ou "
            "propriedade cruzada não aparecem aqui. SÓ sócio com participação "
            "societária liga empresas: administrador, diretor e presidente sem "
            "participação (qualificações 05, 10, 16 e equivalentes) não ligam; cada "
            "relação traz `classes_qualificacao` (sem nomes). NÃO inclui percentual de "
            "participação societária (a Receita não divulga isso publicamente): "
            "toda relação é binária (é sócio ou não é), nunca proporcional. "
            "O CPF de sócio pessoa física vem parcialmente mascarado pela Receita "
            "(só alguns dígitos aparecem) — nomes comuns podem colidir nos dígitos "
            "visíveis e gerar falso positivo. O quadro societário é do mês de "
            "referência do dump da Receita (`receita_dump_reference`), que NÃO é "
            "a data do snapshot: cite as duas."
        ),
        "fields": [
            _f("cnpj", "string", "CNPJ da operadora (14 dígitos)"),
            _f("grupo_id", "string",
               "Identificador do grupo societário amplo, estável entre snapshots: "
               "`grp_` + o menor CNPJ básico do componente (componente conectado "
               "no grafo de sócios — soma relações TOTAIS e PARCIAIS, "
               "transitivamente). Mesmo grupo_id = conectados por alguma "
               "cadeia de relações, não necessariamente quadro idêntico entre "
               "todos os membros — para isso, ver `mesmo_grupo`."),
            _f("tamanho_grupo", "int", "Quantas empresas (raízes de CNPJ de 8 dígitos) fazem parte do grupo_id; matriz e filiais contam uma vez"),
            _f("grupo_inferivel", "bool",
               "`false` só nas sociedades anônimas (natureza jurídica 2046 e 2054 da Receita): o quadro da S.A. traz diretoria e conselho, não acionistas, e por isso não gera ligação "
               "(`motivo` = `sa_quadro_sem_acionistas`). A ligação que nasce do quadro de outra empresa em que a S.A. é sócia com participação continua. Ausente nas demais empresas."),
            _f("motivo", "string", "Por que o grupo não é inferível pelo quadro desta empresa (`sa_quadro_sem_acionistas`); presente só com `grupo_inferivel = false`"),
            _f("socios", "array[object]",
               "Sócios do CNPJ conforme a Receita: {tipo (fisica|juridica|"
               "estrangeiro), qualificacao; nome e documento (CNPJ básico) só para "
               "pessoa jurídica — sócio pessoa física ou estrangeiro sai sem nome}."),
            _f("mesmo_grupo", "array[object]",
               "Operadoras com relação DIRETA e TOTAL com este CNPJ (nunca por "
               "transitividade): quadro de sócios EXATAMENTE idêntico, ou uma "
               "controla a outra com exclusividade (nenhum outro sócio junto). "
               "{cnpj, tipo_relacao, classes_qualificacao}, onde tipo_relacao é um de: "
               "'quadro_identico' (mesmo conjunto de sócios); "
               "'controle_exclusivo_exercido' (este CNPJ é o ÚNICO sócio do "
               "outro); 'controle_exclusivo_recebido' (o outro CNPJ é o ÚNICO "
               "sócio deste)."),
            _f("relacionadas_parcial", "array[object]",
               "Operadoras com relação DIRETA mas PARCIAL: só alguns sócios em "
               "comum (não o quadro inteiro), ou propriedade não exclusiva "
               "(a controladora é uma entre vários sócios da controlada). "
               "{cnpj, tipo_relacao, classes_qualificacao, socios_em_comum (int) e nomes_em_comum "
               "(nomes dos sócios PJ em comum; pessoa física só conta) — só presentes para tipo_relacao "
               "'socios_em_comum'; total_socios_da_controlada (int) — só "
               "presente para os tipos de controle}. tipo_relacao é um de: "
               "'socios_em_comum'; "
               "'controle_parcial_exercido' (este CNPJ é UM dos sócios do "
               "outro, que tem mais sócios além dele); "
               "'controle_parcial_recebido' (o outro CNPJ é UM dos sócios "
               "deste). Não há como saber o percentual de cada sócio — a "
               "Receita não divulga isso."),
            _f("holdings_externas", "array[object]",
               "Sócios pessoa jurídica que NÃO são eles mesmos operadoras da "
               "base (ex.: holding controladora fora do universo SCM/SMP/"
               "STFC/SeAC), com cadastro completo resolvido via BrasilAPI pela "
               "matriz: {cnpj_basico (8 dígitos — a Receita não informa os 6 "
               "dígitos finais do CNPJ do sócio, só o básico), razao_social, "
               "nome_fantasia, situacao_cadastral, natureza_juridica, porte, "
               "capital_social, data_inicio_atividade, cnae_fiscal_descricao, "
               "municipio, uf} (sem endereço: logradouro, número, complemento, bairro e CEP não são servidos). "
               "Campos ficam vazios se a matriz não existir/não for encontrada."),
            _f("endereco_sede", "object",
               "Local da sede registrado na outorga Anatel (mesma fonte de "
               "`scms`/`smps`/`stfcs`/`seacs`): {municipio, uf, codigo_ibge}; "
               "logradouro, número, complemento, bairro e CEP não são servidos. "
               "Null se o CNPJ não tiver outorga com endereço cadastrado."),
            _f("receita_dump_reference", "string",
               "Mês de referência do dump de CNPJ da Receita usado neste "
               "cruzamento", example="2026-09"),
        ],
    },
}


# STFC e SeAC têm o mesmo formato de outorga de `smps` e `scms` (cadastro da Anatel cruzado com ASNs por CNPJ).
SCHEMA["eventos"] = {
    "key": "id",
    "description": (
        "O que mudou entre snapshots (camada de histórico): uma linha por evento, de TODAS as datas com histórico (não depende de `date`; `de` no corpo da consulta, AAAA-MM-DD, limita o início). Sem login ou chave de MCP `de` é obrigatório e não pode ser anterior ao snapshot atual mais antigo. Cada evento é uma "
        "diferença OBSERVADA entre dois snapshots, sem causa nem intenção; leve só a chave (ASN, PTT, CNPJ, prefixo), sem nome de empresa. `estado` é a janela de "
        "confirmação: confirmado, pendente ou revertido (para 'o que mudou' use estado=confirmado). `natureza=inferido` (provedor_novo, provedor_perdido) vem do "
        "ARC v1: trate como provável e variável entre snapshots."
    ),
    "fields": [
        _f("id", "string", "Identificador do evento"),
        _f("data", "string", "Data do snapshot em que a mudança apareceu (AAAA-MM-DD)", example="2026-10-30"),
        _f("tipo", "string", "Tipo do evento", enum=[
            "asn_novo", "asn_sumido", "ixp_entrada", "ixp_saida", "ixp_entrada_observada", "ixp_saida_observada", "provedor_novo", "provedor_perdido",
            "mudanca_origem", "roa_ganho", "roa_perdido", "aspa_ganho", "aspa_perdido", "rpki_invalido_novo", "rpki_invalido_resolvido",
            "outorga_nova", "outorga_baixa", "alerta_novo", "alerta_resolvido"]),
        _f("entidade", "string", "Chave da entidade: asn:N, cnpj:N ou prefixo:P", example="asn:28571"),
        _f("chave", "string", "Detalhe que distingue eventos da mesma entidade (PTT, provedor, serviço, alerta)"),
        _f("asn", "int", "ASN do evento (o novo originador em mudanca_origem)"),
        _f("uf", "string", "UF da sede do ASN (2 letras MAIÚSCULAS)", example="SP"),
        _f("estado", "string", "Janela de confirmação", enum=["confirmado", "pendente", "revertido"]),
        _f("confirmado", "bool", "estado = confirmado"),
        _f("janela", "int", "Snapshots necessários para confirmar (contando o de origem)"),
        _f("confirmado_em", "string", "Data em que foi confirmado"),
        _f("revertido_em", "string", "Data em que foi desmentido"),
        _f("natureza", "string", "observado (diferença medida) ou inferido (ARC v1)", enum=["observado", "inferido"]),
        _f("destaque", "bool", "mudanca_origem cujo novo estado é RPKI inválido"),
        _f("ixp", "string", "Código do PTT (eventos ixp_*)"),
        _f("servico", "string", "scm, smp, stfc ou seac (eventos outorga_*)"),
        _f("rpki", "string", "Estado RPKI do prefixo após a mudança de origem"),
        _f("provedor", "int", "ASN provedor (eventos provedor_*; inferido)"),
    ],
}
SCHEMA["series_asn"] = {
    "key": "asn",
    "description": (
        "Série por ASN brasileiro: uma linha por (ASN, snapshot com histórico), só das 8 datas mais recentes (`de` no corpo, AAAA-MM-DD, limita o início; sem login ou chave de MCP é obrigatório). Para a série longa de um ASN use "
        "historico_serie(escopo=\"asn:N\"). Coluna ausente = sem dado naquele snapshot (n_provedores antes do bloco de relações), nunca zero. "
        "`users` é estimativa da APNIC e oscila entre medições."
    ),
    "fields": [
        _f("asn", "int", "Número do AS"),
        _f("data", "string", "Data do snapshot (AAAA-MM-DD)", example="2026-10-31"),
        _f("uf", "string", "UF da sede da organização", example="SP"),
        _f("cnpj", "string", "CNPJ da organização"),
        _f("users", "int", "Usuários estimados (APNIC)"),
        _f("v6users", "int", "Usuários IPv6 estimados (APNIC)"),
        _f("p4", "int", "Prefixos IPv4 na tabela global"),
        _f("p6", "int", "Prefixos IPv6 na tabela global"),
        _f("n_ixd", "int", "PTTs onde é par direto"),
        _f("n_ixm", "int", "PTTs onde é membro cadastrado"),
        _f("n_provedores", "int", "Provedores confirmado+ (ARC v1, inferência)"),
        _f("n_roa", "int", "ROAs do AS"),
        _f("n_aspa", "int", "Objetos ASPA do AS"),
        _f("rpki_valid", "int", "Prefixos RPKI válidos"),
        _f("rpki_invalid", "int", "Prefixos RPKI inválidos"),
        _f("rpki_not_found", "int", "Prefixos sem ROA"),
        _f("n_alertas", "int", "Alertas do AS"),
    ],
}

SCHEMA["indicadores_operadora"] = {
    "key": "cnpj",
    "description": (
        "Indicadores do SICI fixo por operadora (CNPJ) no mês de referência: parcela dos acessos declarados no país, posição, variação contra o mês anterior e "
        "contra o mesmo mês do ano anterior, e meses seguidos de queda. Dado DECLARADO à Anatel (autodeclarado); não mede qualidade nem receita. "
        "`acessos` e `share_br` são do CNPJ; um CNPJ com vários ASNs não deve ter acessos somados por ASN."
    ),
    "fields": [
        _f("cnpj", "string", "CNPJ (14 dígitos)"),
        _f("empresa", "string", "Nome declarado no SICI"),
        _f("uf", "string", "UF do cadastro (2 letras MAIÚSCULAS)", example="SP"),
        _f("acessos", "int", "Acessos fixos declarados no mês de referência"),
        _f("share_br", "float", "Parcela (%) dos acessos declarados no país"),
        _f("posicao_br", "int", "Posição por acessos no país (1 = mais acessos)"),
        _f("var_mm_abs", "int", "Variação absoluta contra o mês anterior"),
        _f("var_mm_pct", "float", "Variação percentual contra o mês anterior"),
        _f("var_aa_abs", "int", "Variação absoluta contra o mesmo mês do ano anterior"),
        _f("var_aa_pct", "float", "Variação percentual contra o mesmo mês do ano anterior; nula sem base de comparação (base 0)"),
        _f("base_aa", "int", "Base da variação em 12 meses: acessos declarados no mesmo mês do ano anterior (0 = não declarou). Abaixo de 1.000 acessos a base é rotulada "
                             "\"base pequena\" (só rótulo, nenhuma linha sai): poucos acessos mudam muito o percentual, então leia junto com `var_aa_abs`"),
        _f("meses_declinio", "int", "Meses seguidos de queda até o mês de referência"),
        _f("em_declinio", "bool", "meses_declinio >= 6"),
        _f("mes_referencia", "string", "Mês de referência da declaração (AAAA-MM)", example="2026-08"),
    ],
}

SCHEMA["sem_declaracao_sici"] = {
    "key": "cnpj",
    "description": (
        "Outorgas SCM sem declaração ao SICI no mês de referência (`mes_referencia`): uma linha por CNPJ. É um FATO sobre a declaração (sem causa nem intenção). "
        "`usuarios_apnic` soma a estimativa da APNIC dos ASNs do CNPJ (medição estatística, não contagem). `classe`: com_usuarios_apnic (>= 100), "
        "sem_usuarios, nao_comparavel (CNPJ sem ASN). `grupo_declara`: outro CNPJ do mesmo grupo societário declarou no mês."
    ),
    "fields": [
        _f("cnpj", "string", "CNPJ (14 dígitos)"),
        _f("razao_social", "string", "Razão social (cadastro SCM)"),
        _f("uf", "string", "UF do cadastro (2 letras MAIÚSCULAS)", example="MG"),
        _f("n_outorgas", "int", "Outorgas SCM do CNPJ"),
        _f("desde", "string", "Mês da outorga mais antiga (AAAA-MM)"),
        _f("asns", "array[int]", "ASNs do CNPJ"),
        _f("usuarios_apnic", "int", "Usuários estimados (APNIC) somados nos ASNs do CNPJ"),
        _f("classe", "string", "Classe pelos usuários estimados", enum=["com_usuarios_apnic", "sem_usuarios", "nao_comparavel"]),
        _f("grupo_id", "string", "Grupo societário (identificador)"),
        _f("grupo_declara", "bool", "Outro CNPJ do grupo declarou no mês"),
        _f("mes_referencia", "string", "Mês de referência (AAAA-MM)", example="2026-08"),
    ],
}

SCHEMA["municipios"] = {
    "key": "ibge",
    "description": (
        "Uma linha por município do IBGE (5.570): população e domicílios do Censo 2022, acessos fixos declarados ao SICI, penetração (acessos ÷ domicílios projetados), mercado não visto "
        "e o PTT mais próximo em linha reta do centróide. `nao_visto` é ESTIMATIVA: max(0, domicílios projetados × taxa de internet da UF (PNAD) − acessos de pessoa física); "
        "inclui quem usa só o celular. Use `sem_ptt_proximo=true` para 'cidades a mais de 100 km de um PTT'. Cite o mês de referência do SICI e o ano do Censo."
    ),
    "fields": [
        _f("ibge", "string", "Código IBGE do município (7 dígitos)", example="3550308"),
        _f("nome", "string", "Nome do município"),
        _f("uf", "string", "UF (2 letras MAIÚSCULAS)", example="SP"),
        _f("populacao", "int", "População residente (Censo 2022); ausente em município criado depois do Censo"),
        _f("populacao_estimada", "int", "População estimada pelo IBGE (1º de julho do ano mais recente)"),
        _f("area_km2", "float", "Área (km²)"),
        _f("domicilios", "int", "Domicílios particulares permanentes ocupados (Censo 2022); ausente se o IBGE não informa"),
        _f("domicilios_projetados", "int", "Domicílios do Censo × crescimento de domicílios da UF na PNAD (estimativa; base da penetração)"),
        _f("fator_projecao_uf", "float", "Crescimento de domicílios da UF entre o Censo e o ano mais recente da PNAD"),
        _f("penetracao_censo", "float", "acessos ÷ domicílios do Censo (sem projeção; superestima a penetração atual)"),
        _f("mes_referencia", "string", "Mês da declaração ao SICI (AAAA-MM) de que vêm `acessos`, `acessos_pf` e a penetração", example="2026-09"),
        _f("acessos", "int", "Acessos fixos declarados ao SICI (0 se o município não tem declaração)"),
        _f("acessos_pf", "int", "Acessos fixos de pessoa física"),
        _f("sem_declaracao_sici", "bool", "Nenhuma operadora declarou acessos no município"),
        _f("penetracao", "float", "acessos ÷ domicílios projetados (pode passar de 1: acesso não é domicílio)"),
        _f("penetracao_pf", "float", "acessos_pf ÷ domicílios projetados"),
        _f("domicilios_com_internet_est", "int", "domicílios projetados × taxa de internet da UF (PNAD; estimativa)"),
        _f("nao_visto", "int", "Mercado não visto estimado, em domicílios"),
        _f("nao_visto_pct", "float", "nao_visto ÷ domicílios"),
        _f("ptt_proximo", "string", "Código do PTT mais próximo (linha reta do centróide)", example="sp"),
        _f("km_ptt", "float", "Distância ao PTT mais próximo (km)"),
        _f("sem_ptt_proximo", "bool", "km_ptt > 100"),
    ],
}

SCHEMA["seguranca_asn"] = {
    "key": "asn",
    "description": (
        "Sinais de segurança de roteamento por ASN do Brasil (parte A). `rov_validates_pct` e `dnssec_validates_pct` são MEDIÇÕES do APNIC por amostragem (alto = a rede valida RPKI/DNSSEC), "
        "não declarações da rede: use `rov_amostras`/`dnssec_amostras` (abaixo de 100 o percentual é instável). `asrank_*`, `cone_*` e `grau_*` são INFERÊNCIA do CAIDA AS Rank. "
        "`n_prefixos_bogon` conta prefixos originados dentro de espaço reservado (IANA) ou não alocado (Team Cymru, na data da lista). Cite as fontes e as datas (describe do `/seguranca/resumo`)."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN"),
        _f("uf", "string", "UF da sede do ASN (2 letras MAIÚSCULAS)", example="SP"),
        _f("faixa_porte", "string", "Porte do ASN por usuários estimados do APNIC (estimativa de usuários de Internet, não assinantes)", enum=["sem_usuarios", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "acima_de_1000000"]),
        _f("faixa_acessos_sici", "string", "Informação extra: faixa de acessos fixos declarados ao SICI do CNPJ do ASN", enum=["sem_acessos", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "acima_de_100000"]),
        _f("rov_validates_pct", "float", "% das medições do APNIC em que a rede não alcança rota RPKI-inválida (janela de 7 dias)"),
        _f("rov_amostras", "int", "Tamanho da amostra do ROV"),
        _f("dnssec_validates_pct", "float", "% de clientes que validam DNSSEC (janela de 1 dia)"),
        _f("dnssec_parcial_pct", "float", "% de clientes com validação parcial de DNSSEC"),
        _f("dnssec_amostras", "int", "Tamanho da amostra do DNSSEC"),
        _f("asrank_rank", "int", "Posição no CAIDA AS Rank (1 = maior cone) — inferência"),
        _f("cone_asns", "int", "ASNs no cone de clientes (CAIDA)"),
        _f("cone_prefixos", "int", "Prefixos no cone de clientes (CAIDA)"),
        _f("grau_cliente", "int", "Clientes segundo o CAIDA"),
        _f("grau_par", "int", "Pares segundo o CAIDA"),
        _f("grau_provedor", "int", "Provedores segundo o CAIDA"),
        _f("n_prefixos_bogon", "int", "Prefixos originados em espaço bogon (0 se nenhum)"),
        _f("asn_reservado", "string", "Motivo, se o ASN está em faixa reservada pela IANA"),
    ],
}

SCHEMA["rs_sessoes"] = {
    "key": "neighbor_ip",
    "description": (
        "Sessões BGP dos membros nos route servers do IX.br (Alice-LG), uma linha por sessão (route server × par). `estado` é up ou down no route server na data da coleta; "
        "`dias_no_estado` conta desde a última mudança; `last_error` é o que o route server reporta, sem causa atribuída. `uso_limite` = rotas recebidas ÷ `import_limit`. "
        "`rs_incerto` = o cache de vizinhos do Alice daquele route server tem mais de 24 h, não traz `cached_at` ou a consulta falhou: não conclua queda do membro por essas linhas (o READY/BUSY/ERROR do Alice é do cache de rotas e não entra). `cadastrado` = o ASN consta "
        "no cadastro de membros do IX.br; cadastrado sem sessão pode ser peering bilateral. Nunca resuma como ranking de empresas: descreva o que foi medido, com PTT e data da coleta."
    ),
    "fields": [
        _f("ixp", "string", "Código do PTT (minúsculo)", example="sp"),
        _f("asn", "int", "ASN do membro"),
        _f("nome", "string", "Nome do membro no cadastro do IX.br (vazio se a sessão não tem cadastro)"),
        _f("cadastrado", "bool", "ASN consta no cadastro de membros do PTT"),
        _f("rs", "string", "Route server (ex.: SP-rs1-v4)"),
        _f("afi", "string", "Família", enum=["v4", "v6"]),
        _f("neighbor_ip", "string", "IP do par na LAN do IX"),
        _f("estado", "string", "Estado da sessão no route server", enum=["up", "down"]),
        _f("dias_no_estado", "int", "Dias desde a última mudança de estado"),
        _f("last_error", "string", "Último erro reportado pelo route server"),
        _f("rotas_recebidas", "int", "Rotas recebidas do membro"),
        _f("rotas_aceitas", "int", "Rotas aceitas"),
        _f("rotas_filtradas", "int", "Rotas filtradas"),
        _f("import_limit", "int", "Limite de importação da sessão"),
        _f("uso_limite", "float", "Rotas recebidas ÷ import_limit"),
        _f("rs_incerto", "bool", "Cache de vizinhos do route server sem frescor confirmado: estado pode estar defasado"),
    ],
}

SCHEMA["rs_communities"] = {
    "key": "community",
    "description": (
        "Uso de communities nas rotas RECEBIDAS dos membros pelos route servers do IX.br (Alice-LG, nível 3), uma linha por PTT × ASN × community (exceto as informativas do IX.br: origem, validação e RTT, que só estão no explorador /communities), só dos vizinhos coletados "
        "(PTTs prioritários e rodízio dentro de um orçamento de requisições: ausência de linha não é ausência de uso). `rotas` é a contagem exata de rotas do ASN com a community (soma das sessões IPv6 e IPv4) e "
        "`fracao` = rotas ÷ `rotas_do_asn`. `classe` decodifica pelo dicionário do Alice: nao_exportar_para, exportar_somente_para (com `alvo_asn`), nao_exportar_rir, nao_exportar_ptt, blackhole, rpki, informativa, outra (community própria do membro). "
        "`forma` = equivalente_padrao quando a community padrão (65000:N) ou estendida (rt:65000:N) foi lida como a grande 65000:0:N (equivalência assumida pela forma). É declaração do membro, não tráfego nem relação comercial; "
        "perfis (aberto, seletivo, restritivo) são inferidos e vêm em /asns/{asn}/politica."
    ),
    "fields": [
        _f("ixp", "string", "Código do PTT (minúsculo)", example="sp"),
        _f("asn", "int", "ASN do membro que anuncia a rota"),
        _f("nome", "string", "Nome do membro como rotulado no route server"),
        _f("community", "string", "Community: a:b (padrão), a:b:c (grande) ou ro|rt:a:b (estendida)", example="65000:0:13335"),
        _f("classe", "string", "Classe da community pelo dicionário do Alice", enum=["rejeicao", "rpki", "blackhole", "nao_exportar_para", "exportar_somente_para", "nao_exportar_rir", "exportar_somente_rir", "nao_exportar_ptt", "nao_exportar_rtt", "nao_exportar_perda", "informativa", "outra"]),
        _f("rotulo", "string", "Rótulo do dicionário (vazio se não decodificada)"),
        _f("forma", "string", "Como foi decodificada", enum=["dicionario", "equivalente_padrao", "nao_decodificada"]),
        _f("alvo_asn", "int", "ASN citado por 'não exportar para' ou 'exportar somente para'"),
        _f("rotas", "int", "Rotas do ASN com a community (exato)"),
        _f("rotas_do_asn", "int", "Rotas recebidas do ASN nos vizinhos coletados"),
        _f("fracao", "float", "rotas ÷ rotas_do_asn"),
    ],
}

SCHEMA["rs_filtradas"] = {
    "key": "motivo",
    "description": (
        "Rotas REJEITADAS pelos route servers do IX.br (Alice-LG, nível 2), uma linha por PTT × ASN × motivo, só dos vizinhos coletados. O `motivo` é a community grande de rejeição decodificada pelo dicionário "
        "do snapshot (26162:300:0 RPKI inválido, 26162:100:0 inválido no Registro.br, 26162:190:0..5 comprimento, bogon, ASN bogon, trânsito livre, nunca via route server, prefixos do IX.br; 26162:616:666 blackhole confirmado). "
        "`rotas` é contagem exata; `prefixos_amostra` traz até 5 prefixos (dado público de roteamento) e é parcial. Um mesmo conjunto de rotas pode ter mais de um motivo. "
        "A rejeição é decisão do route server naquele instante, não veredito sobre o ASN."
    ),
    "fields": [
        _f("ixp", "string", "Código do PTT (minúsculo)", example="sp"),
        _f("asn", "int", "ASN do membro cujas rotas foram rejeitadas"),
        _f("nome", "string", "Nome do membro como rotulado no route server"),
        _f("motivo", "string", "Community grande do motivo", example="26162:300:0"),
        _f("rotulo", "string", "Motivo (dicionário do Alice)", example="Invalid on RPKI"),
        _f("classe", "string", "rejeicao ou blackhole", enum=["rejeicao", "blackhole"]),
        _f("rotas", "int", "Rotas rejeitadas com esse motivo (exato)"),
        _f("rotas_rejeitadas_do_asn", "int", "Total de rotas rejeitadas do ASN no PTT"),
        _f("prefixos_amostra", "array[string]", "Até 5 prefixos de exemplo (amostra)"),
    ],
}

SCHEMA["bloqueios_asn"] = {
    "key": "asn",
    "description": (
        "Medições do OONI (Open Observatory of Network Interference) por ASN × teste na janela de dias do snapshot: quantas medições e quantas a PRÓPRIA sonda declarou anômalas. NÃO é o veredito do backend do OONI "
        "nem prova de censura (pode ser filtro do cliente, VPN, falha do serviço ou falso positivo); sondas são de voluntários e poucas por ASN. Só células com 10 ou mais medições; sem ASN ausente não se conclui nada. "
        "`webconnectivity` é AMOSTRA de horas (`amostra`=true). Dados do OONI sob CC BY-NC-SA 4.0: cite OONI (ooni.org) e a licença (campo `licenca`). Cite a janela e o snapshot."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN"),
        _f("teste", "string", "Teste do OONI", enum=["whatsapp", "telegram", "signal", "facebookmessenger", "tor", "psiphon", "webconnectivity"]),
        _f("n", "int", "Medições válidas na janela"),
        _f("anomalias", "int", "Medições em que a sonda declarou bloqueio/falha"),
        _f("pct_anomalia", "float", "100 × anomalias / n (veredito da sonda)"),
        _f("amostra", "bool", "true para o webconnectivity (amostra de horas)"),
        _f("janela_inicio", "string", "Primeiro dia agregado (AAAA-MM-DD; dia da pasta do bucket, UTC)"),
        _f("janela_fim", "string", "Último dia agregado"),
        _f("veredito", "string", "Sempre 'da sonda'", example="da sonda"),
        _f("licenca", "string", "Licença dos dados do OONI", example="CC BY-NC-SA 4.0"),
    ],
}

SCHEMA["organizacoes_asn"] = {
    "key": "asn",
    "description": (
        "Organização de cada ASN do Brasil no CAIDA AS Rank (derivada do WHOIS pelo as2org do CAIDA) e, quando o produto de abuso foi publicado, a contagem de servidores C2 do Feodo Tracker (abuse.ch) em "
        "prefixos do ASN. `irmaos_br` são os outros ASNs do Brasil da mesma organização; é INFERÊNCIA do CAIDA, pode juntar filiais sob uma 'Parent' e não é grupo societário (para esse, use `socios`). "
        "`feodo_c2` zero quer dizer nenhum na lista, NÃO rede limpa (a lista cobre poucas famílias e está quase vazia em 2026). Cite a fonte e a data da coleta (describe de /asns/{asn}/organizacao)."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN"),
        _f("org_id", "string", "Identificador da organização no AS Rank (igual para ASNs da mesma organização)"),
        _f("org_nome", "string", "Nome da organização no registro (pode ser o de uma 'Parent')"),
        _f("org_pais", "string", "País da organização (ISO 3166-1 alfa-2)", example="BR"),
        _f("membros_total", "int", "ASNs da organização no mundo"),
        _f("n_irmaos_br", "int", "Quantos outros ASNs do Brasil a organização tem"),
        _f("irmaos_br", "array[int]", "Outros ASNs do Brasil da mesma organização. Teste com `contains`", example=[]),
        _f("feodo_c2", "int", "Servidores C2 do Feodo Tracker em prefixos do ASN (0 = nenhum na lista); só existe se o produto de abuso foi publicado"),
    ],
}

SCHEMA["transito_uf"] = {
    "key": "uf",
    "description": (
        "Concentração do trânsito por UF: os provedores INFERIDOS (ARC v2, nível provável ou superior) dos ASNs do Brasil com sede na UF. A UF é a da sede da organização; "
        "a concentração mede quem os ASNs da UF têm como provedor, NÃO volume de tráfego nem contratos. `hhi_clientes` vai de 0 a 10.000 (acima de 2.500 = concentrado, convenção da "
        "análise antitruste, aqui só uma régua). Cite a data do snapshot e que é inferência (describe de /transito/ufs)."
    ),
    "fields": [
        _f("uf", "string", "Sigla da UF", example="ES"),
        _f("asns_br", "int", "ASNs do Brasil com sede na UF"),
        _f("asns_com_provedor", "int", "Desses, quantos têm ao menos um provedor inferido (nível provável ou superior)"),
        _f("pct_com_provedor", "float", "asns_com_provedor ÷ asns_br, em %"),
        _f("elos_provedor", "int", "Pares (ASN da UF, provedor) inferidos"),
        _f("provedores_distintos", "int", "Provedores distintos dos ASNs da UF"),
        _f("hhi_clientes", "int", "HHI (0 a 10.000) da participação de cada provedor nos pares da UF"),
        _f("top1_share", "float", "Participação do maior provedor (0 a 1)"),
        _f("top3_share", "float", "Participação dos três maiores (0 a 1)"),
        _f("share_provedores_estrangeiros", "float", "Participação dos provedores sem ASN brasileiro (0 a 1)"),
        _f("provedor_principal", "int", "ASN do maior provedor inferido"),
        _f("provedor_principal_nome", "string", "Nome do maior provedor (nome do ASN)"),
    ],
}

SCHEMA["transito_asn"] = {
    "key": "asn",
    "description": (
        "Cone de clientes de cada ASN com cliente inferido: clientes diretos e indiretos pela relação provedor-cliente inferida (ARC v2, nível provável ou superior). Só existem "
        "elos com ao menos um ASN brasileiro; irmãos (mesmo CNPJ raiz ou organização do CAIDA) não contam. Usuários são estimativa APNIC e se repetem entre ASNs da mesma operadora. Inferência."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN (provedor)"),
        _f("clientes_diretos", "int", "Clientes diretos inferidos"),
        _f("cone_asns", "int", "ASNs no cone (diretos e indiretos)"),
        _f("cone_br", "int", "ASNs do Brasil no cone"),
        _f("cone_usuarios", "int", "Usuários estimados (APNIC) dos ASNs do Brasil no cone"),
        _f("n_ufs_cone", "int", "UFs distintas (sede) dos ASNs do Brasil no cone"),
        _f("irmaos_excluidos", "int", "ASNs irmãos do provedor que ficaram fora da contagem"),
        _f("br", "bool", "O ASN é brasileiro"),
        _f("posicao_cone_br", "int", "Posição pelo tamanho do cone no Brasil (1 = maior)"),
    ],
}

SCHEMA["facilities"] = {
    "key": "id",
    "description": (
        "Instalações (datacenters e pontos de interconexão) cadastradas no PeeringDB: as do Brasil (`escopo`=brasil) e as de outros países que abrigam PTTs externos cadastrados no Arandurapé (`escopo`=ptt_externo, sem contagem de redes). "
        "Cadastro AUTODECLARADO por organizações; `redes_declaradas` é o que o cadastro informa, `n_redes` o que foi coletado (só instalações do Brasil). `cadastro_classe` (recente: até 12 meses; parado: 1 a 3 anos; antigo: mais de 3 anos) "
        "é INFERÊNCIA pela data da última atualização do registro ou dos vínculos: mede a manutenção do cadastro, não a operação da instalação nem da empresa. Cite a fonte (PeeringDB) e a data da coleta (describe de /facilities)."
    ),
    "fields": [
        _f("id", "int", "Identificador da instalação no PeeringDB (fac)"),
        _f("nome", "string", "Nome da instalação"),
        _f("org_nome", "string", "Organização que cadastrou a instalação"),
        _f("cidade", "string", "Cidade (texto do cadastro)"),
        _f("uf", "string", "UF (só instalações do Brasil)", example="SP"),
        _f("pais", "string", "País (ISO 3166-1 alfa-2)", example="BR"),
        _f("lat", "float", "Latitude do cadastro"),
        _f("lon", "float", "Longitude do cadastro"),
        _f("escopo", "string", "brasil, ou ptt_externo (fora do Brasil, listada por abrigar um PTT externo cadastrado)", enum=["brasil", "ptt_externo"]),
        _f("n_redes", "int", "Redes vinculadas à instalação coletadas (só Brasil)"),
        _f("n_redes_br", "int", "Dessas, redes com ASN do Brasil"),
        _f("redes_declaradas", "int", "Número de redes que o próprio cadastro informa"),
        _f("ptts", "array[string]", "PTTs na instalação: código do Arandurapé (IX.br ou externo) ou `pdb-ix-<id>` se o PTT não é conhecido. Teste com `contains`", example=["sp"]),
        _f("n_carriers", "int", "Carriers cadastrados na instalação"),
        _f("campus_id", "int", "Campus do PeeringDB a que a instalação pertence"),
        _f("criado", "string", "Criação do registro (ISO 8601)"),
        _f("atualizado", "string", "Última atualização do registro (ISO 8601)"),
        _f("cadastro_classe", "string", "Cadastro vivo ou abandonado (INFERIDO pelas datas)", enum=["recente", "parado", "antigo"]),
        _f("cadastro_dias", "int", "Dias entre a última atualização do registro ou dos vínculos e a coleta"),
    ],
}

SCHEMA["facilidades_rede"] = {
    "key": "asn",
    "description": (
        "Uma linha por vínculo rede × instalação do Brasil no PeeringDB (`netfac`): a rede declara estar na instalação. É declaração no cadastro, não tráfego nem contrato; instalações no exterior não são coletadas. "
        "Para contar instalações por ASN use `group_by` em `asn`. Cite a fonte (PeeringDB) e a data da coleta."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN"),
        _f("asn_nome", "string", "Nome do ASN"),
        _f("facility_id", "int", "Identificador da instalação (use em /facilities/{id})"),
        _f("facility_nome", "string", "Nome da instalação"),
        _f("cidade", "string", "Cidade da instalação"),
        _f("uf", "string", "UF da instalação"),
        _f("org_nome", "string", "Organização da instalação"),
        _f("no_vinculo_desde", "string", "Criação do vínculo no cadastro (ISO 8601)"),
        _f("vinculo_atualizado", "string", "Última atualização do vínculo (ISO 8601)"),
    ],
}

SCHEMA["redes_peering"] = {
    "key": "asn",
    "description": (
        "Uma linha por rede do Brasil com registro no PeeringDB: atributos de peering AUTODECLARADOS (escopo, IPv6, multicast, se declara não usar route server, se informou looking glass e route server), contagens de instalações e de portas "
        "em PTTs externos e a leitura de cadastro (INFERIDA pelas datas: mede a manutenção do registro, não a operação da rede). Não traz as URLs (use /asns/{asn}/peering). Cite a fonte (PeeringDB) e a data da coleta."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN"),
        _f("escopo", "string", "Escopo geográfico declarado", example="Regional"),
        _f("ipv6", "bool", "Declara suporte a IPv6"),
        _f("multicast", "bool", "Declara suporte a multicast"),
        _f("unicast", "bool", "Declara suporte a unicast"),
        _f("nunca_via_route_server", "bool", "Declara não usar route servers"),
        _f("tem_looking_glass", "bool", "Informou URL de looking glass"),
        _f("tem_route_server", "bool", "Informou URL de route server"),
        _f("ixps_declarados", "int", "PTTs que o cadastro informa"),
        _f("instalacoes_declaradas", "int", "Instalações que o cadastro informa"),
        _f("instalacoes_br", "int", "Instalações do Brasil coletadas (vínculos netfac)"),
        _f("portas_externas", "int", "Portas em PTTs externos cadastrados"),
        _f("capacidade_externa_mbps", "int", "Soma das velocidades declaradas dessas portas (capacidade declarada, não tráfego)"),
        _f("criado", "string", "Criação do registro da rede (ISO 8601)"),
        _f("atualizado", "string", "Última atualização do registro (ISO 8601)"),
        _f("cadastro_classe", "string", "Cadastro vivo ou abandonado (INFERIDO pelas datas)", enum=["recente", "parado", "antigo"]),
        _f("cadastro_dias", "int", "Dias desde a última atualização do registro, das portas ou das instalações"),
    ],
}

SCHEMA["cetic_indicadores"] = {
    "key": "tabela",
    "description": (
        "Tabelas oficiais das pesquisas TIC Domicílios (uso de TIC nos domicílios) e TIC Provedores (setor de provimento de Internet) do Cetic.br|NIC.br, edição vigente, "
        "uma linha por tabela × recorte × item × resposta. `proporcao` é o percentual da resposta no recorte (`margem_proporcao` em pontos percentuais); `total` é o número "
        "estimado de domicílios ou de empresas provedoras (`margem_total`). São estimativas amostrais, não contagens: cite sempre a pesquisa, a edição e a margem de erro, e a fonte "
        "'Cetic.br|NIC.br' (CC BY 4.0). O recorte mais fino é a grande região (sem UF nem empresa); declarações de provedores são autodeclaração e não identificam empresa."
    ),
    "fields": [
        _f("pesquisa", "string", "Pesquisa", enum=["domicilios", "provedores"]),
        _f("edicao", "int", "Ano da edição", example=2025),
        _f("tabela", "string", "Código da aba (ex.: A1, C2, D7)", example="A1"),
        _f("titulo_tabela", "string", "Título da tabela"),
        _f("universo", "string", "A quem a pergunta se aplica (ex.: Total de domicílios)"),
        _f("dimensao", "string", "Tipo de recorte", example="Região"),
        _f("recorte", "string", "Categoria do recorte (ex.: Norte, Urbana, Até 1 SM)", example="Norte"),
        _f("item", "string", "Item da pergunta, quando ela tem vários (vazio se só há uma)"),
        _f("resposta", "string", "Resposta (Sim, Não, categoria...)", example="Sim"),
        _f("proporcao", "float", "Percentual (%) da resposta no recorte"),
        _f("margem_proporcao", "float", "Margem de erro da proporção, em pontos percentuais"),
        _f("total", "float", "Total estimado (domicílios ou empresas) com essa resposta"),
        _f("margem_total", "float", "Margem de erro do total"),
    ],
}

SCHEMA["cetic_estimativas_uf"] = {
    "key": "grupo",
    "description": (
        "Estimativas do ARANDURAPÉ (não são números publicados pelo Cetic.br) dos microdados públicos da TIC Domicílios: por Brasil, grande região e UF, a proporção (%) de domicílios com "
        "acesso à Internet, com computador e com banda larga fixa, com erro-padrão e margem de erro de 95% calculados dos 200 pesos de réplica da base. Diga sempre que é estimativa do "
        "Arandurapé sobre microdados do Cetic.br|NIC.br (CC BY 4.0), cite a edição e a margem; a margem oficial das tabelas é maior que a daqui. Por UF a amostra é de 700 a 1.500 "
        "domicílios: compare UFs só quando as margens não se sobrepõem. `suprimido` preenchido = grupo com menos de 30 entrevistados, sem número."
    ),
    "fields": [
        _f("grupo", "string", "BR, nome da região ou sigla da UF", example="SP"),
        _f("tipo", "string", "Tipo do grupo", enum=["brasil", "regiao", "uf"]),
        _f("uf", "string", "Sigla da UF (vazio para Brasil e região)", example="SP"),
        _f("indicador", "string", "Indicador", enum=["internet", "computador", "banda_larga_fixa"]),
        _f("rotulo", "string", "Descrição do indicador"),
        _f("edicao", "int", "Ano da edição da pesquisa", example=2025),
        _f("n", "int", "Domicílios entrevistados no grupo"),
        _f("proporcao", "float", "Percentual (%) de domicílios com a característica"),
        _f("erro_padrao", "float", "Erro-padrão da proporção (pontos percentuais)"),
        _f("margem", "float", "Margem de erro de 95% da proporção (1,96 × erro-padrão), em pontos percentuais"),
        _f("cv", "float", "Coeficiente de variação (erro-padrão ÷ proporção)"),
        _f("total", "int", "Domicílios com a característica, estimados pelos pesos"),
        _f("precisao", "string", "baixa se o CV passa de 30%", enum=["adequada", "baixa"]),
        _f("suprimido", "string", "Motivo da supressão (amostra pequena); vazio se há número"),
    ],
}

SCHEMA["demanda_oferta"] = {
    "key": "grupo",
    "description": (
        "Demanda × oferta de banda larga fixa, ESTIMATIVA do Arandurapé: a proporção de domicílios com banda larga fixa (TIC Domicílios, Cetic.br|NIC.br, CC BY 4.0) aplicada aos "
        "domicílios do IBGE projetados dá a demanda; a oferta são os acessos fixos de pessoa física declarados ao SICI. `razao` = oferta ÷ demanda, com intervalo de 95% que vem só da "
        "amostra da TIC (menor que o oficial). `classe`: oferta_abaixo_da_demanda (intervalo todo abaixo de 1), compativel, oferta_acima_da_demanda, indeterminado (precisão baixa). "
        "Razão baixa NÃO prova provedor sem declaração: é sinal para investigar (acesso não é domicílio; os períodos das fontes diferem). Cite a edição da TIC e o mês do SICI. "
        "`nao_visto` aqui é de banda larga fixa; o de `municipios` usa uso de internet da PNAD, que inclui só celular."
    ),
    "fields": [
        _f("grupo", "string", "Sigla da UF, nome da região ou BR", example="AL"),
        _f("tipo", "string", "Tipo do grupo", enum=["brasil", "regiao", "uf"]),
        _f("uf", "string", "Sigla da UF (vazio para região e Brasil)", example="AL"),
        _f("classe", "string", "Resultado do intervalo contra 1", enum=["oferta_abaixo_da_demanda", "compativel", "oferta_acima_da_demanda", "indeterminado"]),
        _f("domicilios_projetados", "int", "Domicílios do Censo 2022 projetados (IBGE)"),
        _f("proporcao_bl_fixa", "float", "% de domicílios com banda larga fixa (TIC, estimativa do Arandurapé)"),
        _f("proporcao_margem", "float", "Margem de 95% da proporção, em pontos percentuais"),
        _f("demanda_domicilios", "int", "Domicílios com banda larga fixa estimados"),
        _f("demanda_margem", "int", "Margem de 95% da demanda, em domicílios"),
        _f("oferta_acessos_pf", "int", "Acessos fixos de pessoa física declarados ao SICI"),
        _f("razao", "float", "Oferta ÷ demanda"),
        _f("razao_min", "float", "Limite inferior (95%) da razão"),
        _f("razao_max", "float", "Limite superior (95%) da razão"),
        _f("nao_visto", "int", "max(0, demanda − acessos de pessoa física)"),
        _f("nao_visto_min", "int", "Limite inferior (95%) do não visto"),
        _f("nao_visto_max", "int", "Limite superior (95%) do não visto"),
        _f("tic_edicao", "int", "Ano da edição da TIC Domicílios", example=2025),
        _f("mes_referencia_sici", "string", "Mês de referência do SICI", example="2026-08"),
    ],
}

SCHEMA["erbs_municipio"] = {
    "key": "ibge",
    "description": (
        "Estações do SMP (telefonia móvel) LICENCIADAS na Anatel por município: cadastro de licenciamento, NÃO cobertura nem sinal. Licenciada não quer dizer em operação; uma estação é "
        "um número do cadastro, não uma torre física; município sem estação (ausente aqui) pode ser atendido por vizinhos. Uma estação conta em todas as gerações que tem (2G GSM, 3G WCDMA, "
        "4G LTE, 5G NR), então as colunas por geração não somam `estacoes`. Fonte: Anatel, dados abertos; cite a data do arquivo."
    ),
    "fields": [
        _f("ibge", "string", "Código IBGE do município (7 dígitos)", example="3550308"),
        _f("nome", "string", "Nome do município"),
        _f("uf", "string", "Sigla da UF", example="SP"),
        _f("estacoes", "int", "Estações licenciadas no município"),
        _f("estacoes_2g", "int", "Estações com GSM"),
        _f("estacoes_3g", "int", "Estações com WCDMA"),
        _f("estacoes_4g", "int", "Estações com LTE"),
        _f("estacoes_5g", "int", "Estações com NR (5G)"),
        _f("por_10mil_hab", "float", "Estações por 10 mil habitantes (população estimada do IBGE)"),
        _f("operadoras", "int", "Operadoras com estação no município"),
        _f("operadora_principal", "string", "Operadora com mais estações no município"),
    ],
}

SCHEMA["fust_municipio"] = {
    "key": "ibge",
    "description": (
        "Compromissos de aplicação do FUST (Fundo de Universalização) registrados pela Anatel, por município: conectividade de escolas públicas e de unidades de saúde, fibra, SMP 4G e favelas. "
        "O arquivo NÃO identifica a empresa executora, então não há operadora. `investimento` é o valor previsto, não o desembolsado; 'em apuração' é a situação registrada pela Anatel, não "
        "inadimplência. Município sem compromisso (ausente aqui) não está no programa. Fonte: Anatel, dados abertos; cite a data do arquivo."
    ),
    "fields": [
        _f("ibge", "string", "Código IBGE do município (7 dígitos)", example="3550308"),
        _f("nome", "string", "Nome do município"),
        _f("uf", "string", "Sigla da UF", example="SP"),
        _f("compromissos", "int", "Compromissos (escola, UBS, favela, localidade ou município a atender)"),
        _f("atendidos", "int", "Com situação Atendido"),
        _f("a_vencer", "int", "Com situação A vencer"),
        _f("em_apuracao", "int", "Com situação Em apuração"),
        _f("investimento", "float", "Investimento total previsto (R$)"),
        _f("por_10mil_hab", "float", "Compromissos por 10 mil habitantes"),
        _f("programas", "array[string]", "Códigos dos programas com compromisso no município (ex.: 1.1, 2.6)"),
    ],
}

SCHEMA["prontidao_agregado"] = {
    "key": "recorte",
    "description": (
        "Prontidão em segurança de roteamento dos ASNs do Brasil, AGREGADA por recorte (país, UF ou faixa de porte): ASNs por classe (pronto, em progresso, atrasado, sem dados), média ponderada pelos usuários "
        "estimados do APNIC, mediana e quantos ASNs têm dado em cada pilar (filtragem, anti-spoofing, coordenação, validação global). O índice é a soma ponderada de medições de terceiros (APNIC, CAIDA, RPKI, IRR, "
        "PeeringDB) com regras públicas e versionadas (ver /prontidao/resumo); NÃO é veredito sobre empresas e não há linha por ASN nem por operadora. O índice de um ASN está em get_asn/asn_detalhe com include=prontidao. "
        "O anti-spoofing só existe para os ASNs com testes do CAIDA Spoofer (~2% dos ASNs brasileiros). Cite a data do snapshot e a versão das regras."
    ),
    "fields": [
        _f("tipo", "string", "Tipo de recorte", enum=["brasil", "uf", "porte"]),
        _f("recorte", "string", "BR, a sigla da UF ou a faixa de porte", example="SP"),
        _f("asns", "int", "ASNs do Brasil no recorte"),
        _f("asns_com_indice", "int", "ASNs com índice (ao menos 2 pilares com dado)"),
        _f("media_ponderada_usuarios", "float", "Média do índice ponderada pelos usuários estimados do APNIC"),
        _f("mediana", "float", "Mediana do índice"),
        _f("usuarios", "int", "Usuários estimados (APNIC) dos ASNs do recorte"),
        _f("classe_pronto", "int", "ASNs na classe pronto"),
        _f("classe_em_progresso", "int", "ASNs na classe em progresso"),
        _f("classe_atrasado", "int", "ASNs na classe atrasado"),
        _f("classe_sem_dados", "int", "ASNs sem dados suficientes"),
        _f("cobertura_filtragem", "int", "ASNs com dado no pilar filtragem"),
        _f("cobertura_anti_spoofing", "int", "ASNs com dado no pilar anti-spoofing"),
        _f("cobertura_coordenacao", "int", "ASNs com dado no pilar coordenação"),
        _f("cobertura_validacao_global", "int", "ASNs com dado no pilar validação global"),
        _f("asns_rov", "int", "ASNs do recorte com dado no componente rov"),
        _f("media_rov", "float", "Média simples do componente rov entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_rov", "float", "Média do componente rov ponderada pelos usuários estimados do APNIC"),
        _f("asns_sem_bogon", "int", "ASNs do recorte com dado no componente sem_bogon"),
        _f("media_sem_bogon", "float", "Média simples do componente sem_bogon entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_sem_bogon", "float", "Média do componente sem_bogon ponderada pelos usuários estimados do APNIC"),
        _f("asns_spoofer", "int", "ASNs do recorte com dado no componente spoofer"),
        _f("media_spoofer", "float", "Média simples do componente spoofer entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_spoofer", "float", "Média do componente spoofer ponderada pelos usuários estimados do APNIC"),
        _f("asns_peeringdb", "int", "ASNs do recorte com dado no componente peeringdb"),
        _f("media_peeringdb", "float", "Média simples do componente peeringdb entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_peeringdb", "float", "Média do componente peeringdb ponderada pelos usuários estimados do APNIC"),
        _f("asns_irr_aut_num", "int", "ASNs do recorte com dado no componente irr_aut_num"),
        _f("media_irr_aut_num", "float", "Média simples do componente irr_aut_num entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_irr_aut_num", "float", "Média do componente irr_aut_num ponderada pelos usuários estimados do APNIC"),
        _f("asns_irr_as_set", "int", "ASNs do recorte com dado no componente irr_as_set"),
        _f("media_irr_as_set", "float", "Média simples do componente irr_as_set entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_irr_as_set", "float", "Média do componente irr_as_set ponderada pelos usuários estimados do APNIC"),
        _f("asns_roa", "int", "ASNs do recorte com dado no componente roa"),
        _f("media_roa", "float", "Média simples do componente roa entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_roa", "float", "Média do componente roa ponderada pelos usuários estimados do APNIC"),
        _f("asns_irr", "int", "ASNs do recorte com dado no componente irr"),
        _f("media_irr", "float", "Média simples do componente irr entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_irr", "float", "Média do componente irr ponderada pelos usuários estimados do APNIC"),
        _f("asns_aspa", "int", "ASNs do recorte com dado no componente aspa"),
        _f("media_aspa", "float", "Média simples do componente aspa entre os ASNs com dado (0 a 100; nos componentes sim/não é o % de ASNs com sim)"),
        _f("media_ponderada_usuarios_aspa", "float", "Média do componente aspa ponderada pelos usuários estimados do APNIC"),
    ],
}

SCHEMA["prontidao_asn"] = {
    "key": "asn",
    "description": (
        "Índice de prontidão em segurança de roteamento POR ASN do Brasil (uma linha por ASN, em ordem de ASN). Lista nominal pública, ligada por padrão (`PRONTIDAO_LISTA_NOMINAL=0` a desliga e a coleção responde com erro). É soma ponderada de medições de terceiros "
        "(APNIC, CAIDA Spoofer, RPKI, IRR, PeeringDB) com regras públicas e versionadas (ver /prontidao/resumo); NÃO é veredito sobre a empresa nem ranking de culpa. Cobertura desigual: o anti-spoofing só existe para ~2% dos ASNs, "
        "o ROV vem de amostra do APNIC e objeto no IRR não prova autoria. Pilar sem dado é \"não medido\" (nota nula): fica fora do índice e da classe, e `pilares_medidos` diz em quantos dos quatro o índice se apoia. "
        "`indice` nulo = sem dados suficientes. Ordene por `asn` ou `usuarios` e leia o índice com `pilares_medidos` ao lado. Cite a data do snapshot e a versão das regras."
    ),
    "fields": [
        _f("asn", "int", "Número do ASN"),
        _f("nome", "string", "Nome do ASN"),
        _f("uf", "string", "UF da sede do ASN", example="SP"),
        _f("indice", "float", "Índice de prontidão, 0 a 100 (nulo se sem dados suficientes)"),
        _f("classe", "string", "Classe do índice (calculada só com os pilares medidos)", enum=["pronto", "em_progresso", "atrasado", "sem_dados"]),
        _f("pilares_medidos", "int", "Quantos dos pilares têm dado e entraram no índice e na classe"),
        _f("pilares_total", "int", "Total de pilares do índice (4)"),
        _f("usuarios", "int", "Usuários estimados (APNIC)"),
        _f("faixa_porte", "string", "Porte por usuários estimados", enum=["sem_usuarios", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "acima_de_1000000"]),
        _f("faixa_acessos_sici", "string", "Informação extra: faixa de acessos fixos declarados ao SICI", enum=["sem_acessos", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "acima_de_100000"]),
        _f("pilar_filtragem", "float", "Nota do pilar filtragem (nulo se sem dado)"),
        _f("pilar_anti_spoofing", "float", "Nota do pilar anti-spoofing (nulo se sem dado)"),
        _f("pilar_coordenacao", "float", "Nota do pilar coordenação (nulo se sem dado)"),
        _f("pilar_validacao_global", "float", "Nota do pilar validação global (nulo se sem dado)"),
        _f("pilares_sem_dado", "array[string]", "Pilares sem dado para o ASN"),
    ],
}

SCHEMA["multas_empresa"] = {
    "key": "raiz",
    "description": (
        "Multas constituídas pela Anatel contra PESSOAS JURÍDICAS prestadoras de SCM, SMP, STFC e SeAC, agregadas por raiz do CNPJ (8 dígitos: matriz e filiais) e grupo de serviço. Multa constituída NÃO é "
        "condenação definitiva: pode estar quitada, parcelada, suspensa judicialmente ou em recurso. Pessoa física, radiodifusão e serviços privados não estão aqui. `saldo` é o saldo devedor atualizado "
        "informado pela Anatel; os anos são os da aplicação da sanção. Fonte: Anatel, dados abertos; cite a data do arquivo."
    ),
    "fields": [
        _f("raiz", "string", "Raiz do CNPJ (8 dígitos)", example="76535764"),
        _f("cnpj_matriz", "string", "CNPJ da matriz (final 0001), quando consta"),
        _f("entidade", "string", "Nome mais frequente da empresa no arquivo"),
        _f("grupo", "string", "Grupo de serviço", enum=["SCM", "SMP", "STFC", "SeAC"]),
        _f("uf", "string", "UF mais frequente", example="SP"),
        _f("multas", "int", "Número de multas constituídas"),
        _f("original", "float", "Valor original das multas (R$)"),
        _f("pago", "float", "Valor pago (R$)"),
        _f("saldo", "float", "Saldo devedor atualizado (R$)"),
        _f("situacoes", "object", "Multas por situação (Quitado, Devedor, Parcial)"),
        _f("primeiro_ano", "string", "Primeiro ano de aplicação"),
        _f("ultimo_ano", "string", "Último ano de aplicação"),
    ],
}

SCHEMA["qualidade_uf"] = {
    "key": "indicador",
    "description": (
        "Indicadores de qualidade do RQUAL da Anatel por UF, serviço, prestadora, indicador e ano: média dos municípios medidos e média ponderada pelo número de medidas. Cobre só as grandes prestadoras de cada "
        "serviço; a ausência de uma empresa não diz nada sobre ela. A unidade e o sentido de cada indicador são os da Anatel (veja `descricao`); NÃO há ranking nem veredito. Resultados sem valor (NA, NO, NI) não entram. "
        "Fonte: Anatel, dados abertos (RQUAL); cite o ano e a data do arquivo."
    ),
    "fields": [
        _f("uf", "string", "Sigla da UF", example="SP"),
        _f("servico", "string", "Serviço medido", enum=["Banda Larga Fixa", "Telefonia Fixa", "Telefonia Móvel"]),
        _f("prestadora", "string", "Prestadora, como na Anatel", example="CLARO"),
        _f("indicador", "string", "Código do indicador (IND... = IQS; INF... = informativo)", example="IND4"),
        _f("descricao", "string", "Descrição do indicador"),
        _f("unidade", "string", "Unidade de medida", example="%"),
        _f("ano", "int", "Ano", example=2025),
        _f("municipios", "int", "Municípios com resultado"),
        _f("resultados", "int", "Resultados numéricos somados"),
        _f("medidas", "int", "Medidas somadas (quando informadas)"),
        _f("media", "float", "Média simples dos resultados dos municípios"),
        _f("media_ponderada", "float", "Média ponderada pelo número de medidas (nula se a Anatel não informou)"),
    ],
}

SCHEMA["reclamacoes_marca"] = {
    "key": "marca",
    "description": (
        "Reclamações de consumidores registradas na Anatel por marca, serviço e ano (2015 em diante). A marca é o nome escolhido pelo consumidor; 'NÃO LOCALIZEI A MINHA EMPRESA' e 'OUTROS' não identificam ninguém. "
        "`raizes` são as raízes de CNPJ ligadas à marca pela tabela curada do Arandurapé (casamento=curada) ou por nome fantasia único (automatico); vazio = sem CNPJ, nunca um palpite. Só agregados; reclamação não é "
        "prova de falha da empresa e depende do tamanho da base de clientes. NÃO há ranking de empresas. Fonte: Anatel, dados abertos; cite a data do arquivo."
    ),
    "fields": [
        _f("marca", "string", "Marca como na Anatel (maiúsculas)", example="VIVO"),
        _f("servico", "string", "Serviço da reclamação", enum=["SCM", "SMP_Pós", "SMP_Pré", "STFC", "SeAC", "Outros"]),
        _f("ano", "int", "Ano", example=2025),
        _f("reclamacoes", "int", "Reclamações (tipo Reclamação) no ano"),
        _f("municipios", "int", "Municípios com ao menos uma reclamação"),
        _f("raizes", "array[string]", "Raízes de CNPJ (8 dígitos) ligadas à marca"),
        _f("casamento", "string", "Como a marca foi ligada ao CNPJ", enum=["curada", "automatico"]),
    ],
}

SCHEMA["consumidor_marca"] = {
    "key": "marca",
    "description": (
        "Reclamações FINALIZADAS no Consumidor.gov.br (Senacon) contra operadoras de telecomunicações, por empresa (nome fantasia) e mês, em agregados: sexo e faixa etária de quem reclamou não são guardados. "
        "`indice_solucao` = resolvidas ÷ avaliadas pelo consumidor (%); `tempo_medio_dias` só das respondidas; `nota_media` de 1 a 5; as quatro razões são nulas com menos de 30 casos (nulo = base insuficiente, não zero). "
        "`raizes` são as raízes de CNPJ ligadas à empresa pela tabela curada do Arandurapé (curada) ou por nome fantasia único (automatico); vazio = sem CNPJ, nunca um palpite. Não é o total de reclamações contra a empresa "
        "e só empresas que aderiram à plataforma aparecem; reclamação não é prova de falha e depende do tamanho da base de clientes. NÃO há ranking. Fonte: Consumidor.gov.br; cite o mês."
    ),
    "fields": [
        _f("marca", "string", "Nome fantasia da empresa no Consumidor.gov.br", example="Vivo - Telefônica"),
        _f("mes", "string", "Mês de finalização (AAAA-MM)", example="2026-09"),
        _f("n", "int", "Reclamações finalizadas no mês"),
        _f("respondidas", "int", "Respondidas pela empresa"),
        _f("avaliadas", "int", "Avaliadas pelo consumidor (resolvida ou não resolvida)"),
        _f("resolvidas", "int", "Avaliadas como resolvidas"),
        _f("pct_respondidas", "float", "% respondidas (nulo com menos de 30 casos)"),
        _f("indice_solucao", "float", "% resolvidas entre as avaliadas (nulo com menos de 30 avaliadas)"),
        _f("tempo_medio_dias", "float", "Tempo médio de resposta, em dias (nulo com menos de 30 respostas)"),
        _f("nota_media", "float", "Nota média do consumidor, de 1 a 5 (nulo com menos de 30 notas)"),
        _f("raizes", "array[string]", "Raízes de CNPJ (8 dígitos) ligadas à empresa"),
        _f("casamento", "string", "Como a empresa foi ligada ao CNPJ", enum=["curada", "automatico"]),
    ],
}

SCHEMA["faixas_espectro"] = {
    "key": "ini_mhz",
    "description": (
        "Quadro de atribuição e destinação de faixas de frequência da Anatel (PDFF): para que serviços cada faixa pode ser usada no Brasil. É NORMA, não licença: não diz quem explora a faixa nem "
        "se está em uso. Uma linha por faixa em MHz, com os serviços de destinação primária e secundária e os atribuídos (primários)."
    ),
    "fields": [
        _f("ini_mhz", "float", "Início da faixa (MHz)", example=3300.0),
        _f("fim_mhz", "float", "Fim da faixa (MHz)", example=3400.0),
        _f("largura_mhz", "float", "Largura da faixa (MHz)"),
        _f("destinacao", "array[string]", "Serviços destinados com caráter primário"),
        _f("destinacao_secundaria", "array[string]", "Serviços destinados com caráter secundário"),
        _f("atribuicao", "array[string]", "Serviços atribuídos (primários)"),
    ],
}

SCHEMA["satelites_direitos"] = {
    "key": "codigo",
    "description": (
        "Direitos de exploração de satélite no Brasil segundo a Anatel: operadora, satélite, posição orbital, banda, tipo (Brasileiro ou Estrangeiro), status e validade. Muitas operadoras são "
        "estrangeiras e não se ligam aos grupos do SICI. Direito concedido não é capacidade em uso nem assinantes. `vencido` = validade anterior à data do snapshot."
    ),
    "fields": [
        _f("operadora", "string", "Operadora do satélite"),
        _f("satelite", "string", "Satélite ou sistema"),
        _f("codigo", "string", "Código do direito"),
        _f("posicao", "string", "Posição orbital (NGEO = não geoestacionário)"),
        _f("banda", "string", "Banda exercendo o direito"),
        _f("tipo", "string", "Brasileiro ou Estrangeiro", enum=["Brasileiro", "Estrangeiro"]),
        _f("status", "string", "Status do direito"),
        _f("lancamento", "string", "Data de lançamento (AAAA-MM-DD)"),
        _f("validade", "string", "Validade do direito (AAAA-MM-DD)"),
        _f("prorrogado", "bool", "Direito prorrogado"),
        _f("vencido", "bool", "Validade anterior à data do snapshot"),
    ],
}

SCHEMA["transferencias_ipv4"] = {
    "key": "id",
    "description": (
        "Operações de transferência de IPv4 em que o Brasil é origem ou destino (listas do Registro.br e log do LACNIC). Uma operação é o mesmo dia e as mesmas partes: um lote de blocos é UMA "
        "operação (`n_blocos`, `enderecos`). É o que as listas DECLARAM, na data que declaram, sem causa nem intenção (não diga 'venda' nem 'aluguel'). Nome de pessoa física provável vem omitido "
        "('Pessoa física'). `primeira_vez_visto` é a primeira data de snapshot em que a lista mostrou a operação; `anterior_a_coleta` = já estava na primeira lista coletada (a coleta começou em 2026-11-01), então "
        "a defasagem não existe. `asn_destino` é o ASN atual do bloco, quando o destino é brasileiro e o bloco é alocado a um ASN."
    ),
    "fields": [
        _f("id", "string", "Identificador da operação"),
        _f("data", "string", "Data da operação (AAAA-MM-DD)", example="2025-03-10"),
        _f("direcao", "string", "br_br, br_exterior ou exterior_br", enum=["br_br", "br_exterior", "exterior_br"]),
        _f("tamanho", "string", "Classe de tamanho pelo total de endereços", enum=["ate_24", "22_a_23", "20_a_21", "19_ou_maior"]),
        _f("origem_nome", "string", "Parte de origem (pessoa física omitida)"), _f("origem_pais", "string", "País da origem"), _f("origem_rir", "string", "RIR da origem"),
        _f("destino_nome", "string", "Parte de destino (pessoa física omitida)"), _f("destino_pais", "string", "País do destino"), _f("destino_rir", "string", "RIR do destino"),
        _f("n_blocos", "int", "Blocos CIDR da operação"), _f("enderecos", "int", "Endereços IPv4 da operação"), _f("blocos", "array[string]", "Blocos CIDR"),
        _f("fontes", "array[string]", "registrobr e/ou lacnic"), _f("primeira_vez_visto", "string", "Primeira data de snapshot em que apareceu"),
        _f("anterior_a_coleta", "bool", "Já estava na primeira lista coletada"), _f("defasagem_dias", "int", "primeira_vez_visto − data (só para o que apareceu depois do início da coleta)"),
        _f("asn_destino", "int", "ASN atual do bloco de destino"), _f("org_destino", "string", "Organização do ASN (pessoa física omitida)"),
    ],
}

SCHEMA["recuperacao_ipv4"] = {
    "key": "recurso",
    "description": (
        "Recursos (bloco IPv4, bloco IPv6 ou ASN) em recuperação pelo Registro.br, com a janela; para bloco IPv4, o status atual no delegated do LACNIC (`reserved` = voltou ao pool). "
        "Recuperação é o processo de retomar recursos sem uso regular; a lista não diz o motivo de cada um."
    ),
    "fields": [
        _f("tipo", "string", "Tipo do recurso", enum=["bloco", "bloco6", "asn"]), _f("recurso", "string", "Bloco CIDR ou número do ASN"),
        _f("inicio", "string", "Início da janela"), _f("fim", "string", "Fim da janela"), _f("primeira_vez_visto", "string", "Primeira data de snapshot em que apareceu"),
        _f("status_delegated", "string", "Status atual do bloco IPv4 no delegated (vazio para IPv6 e ASN)"),
    ],
}

SCHEMA["eventos_bloco"] = {
    "key": "id",
    "description": (
        "Eventos observados no delegated-lacnic-extended diário que envolvem o Brasil: `titularidade` (o opaque-id do bloco mudou), `recuperacao` (allocated/assigned → reserved), `liberacao` "
        "(reserved → allocated/assigned), `novo`, `removido`, `pais`. Diferença observada entre duas fotos, na data da foto em que apareceu (`visto_entre` quando faltou uma foto), sem causa nem "
        "intenção. O opaque-id é a organização sem nome. Desde 2020."
    ),
    "fields": [
        _f("id", "string", "Identificador do evento"), _f("data", "string", "Data da foto em que a mudança apareceu"),
        _f("tipo", "string", "Tipo do evento", enum=["titularidade", "recuperacao", "liberacao", "novo", "removido", "pais"]),
        _f("inicio", "string", "Primeiro endereço do bloco"), _f("quantidade", "int", "Endereços"), _f("blocos", "array[string]", "Blocos CIDR"),
        _f("de_status", "string", "Status antes"), _f("de_cc", "string", "País antes"), _f("de_opaque", "string", "opaque-id antes"),
        _f("para_status", "string", "Status depois"), _f("para_cc", "string", "País depois"), _f("para_opaque", "string", "opaque-id depois"), _f("visto_entre", "array[string]", "Fotos extremas quando faltou uma"),
    ],
}

SCHEMA["espaco_ipv4"] = {
    "key": "inicio",
    "description": (
        "Blocos IPv4 do Brasil (delegated) que NÃO estão plenamente anunciados na tabela de origens do snapshot: `nao_anunciado`, `roa_sem_anuncio` (há ROA mas nenhum anúncio), `parcial` (anunciado só em "
        "parte) e `em_recuperacao`. INFERIDO. NÃO ANUNCIADO NÃO É SEM USO (rede interna, enlace, reserva técnica e CGNAT não aparecem na tabela global): nunca diga que o espaço está 'ocioso' ou 'sem uso'. "
        "`tabelas_sem_anuncio` conta as tabelas de origem distintas seguidas sem anúncio que temos (a tabela é semanal); `sem_anuncio_desde` é a data mais antiga em que a tabela apareceu."
    ),
    "fields": [
        _f("inicio", "string", "Primeiro endereço do bloco", example="198.18.0.0"), _f("quantidade", "int", "Endereços do bloco"),
        _f("classe", "string", "Classe pela tabela de origens", enum=["nao_anunciado", "roa_sem_anuncio", "parcial", "em_recuperacao"]), _f("anunciado_pct", "float", "% de endereços anunciados"),
        _f("asn", "int", "ASN titular (blocos alocados pelo Registro.br ao ASN)"), _f("org", "string", "Organização do ASN (pessoa física omitida)"), _f("cnpj", "string", "CNPJ da organização do ASN"),
        _f("uf", "string", "UF da organização do ASN"), _f("tabelas_sem_anuncio", "int", "Tabelas de origem distintas seguidas sem anúncio (vazio se parcial)"),
        _f("sem_anuncio_desde", "string", "Data mais antiga em que a tabela sem anúncio apareceu"), _f("ano_registro", "string", "Ano do registro no delegated"), _f("roa_asns", "array[int]", "ASNs com ROA para o bloco"),
    ],
}

SCHEMA["uso_por_terceiros_ipv4"] = {
    "key": "inicio",
    "description": (
        "HIPÓTESE de uso por terceiros: blocos IPv4 do Brasil com ao menos um sinal (S1 origem ≠ titular, S2 ROA de outro ASN, S3 bloco sem ASN titular anunciado por terceiro, S4 origem mudou sem "
        "transferência registrada). NUNCA diga 'aluguel' nem afirme intenção: o caso comum é o provedor que anuncia o bloco do cliente. `confianca` (baixa, media, alta) sobe um nível com dois ou mais "
        "sinais; `evidencias` traz a regra aplicada. S5 a S7 (geofeed, contato, PTT novo) não foram avaliados."
    ),
    "fields": [
        _f("inicio", "string", "Primeiro endereço do bloco"), _f("quantidade", "int", "Endereços"), _f("classe", "string", "Classe pela tabela de origens"), _f("anunciado_pct", "float", "% anunciado"),
        _f("asn_titular", "int", "ASN titular"), _f("org_titular", "string", "Organização do titular (pessoa física omitida)"), _f("origens", "array[int]", "ASNs que anunciam o bloco"),
        _f("roa_asns", "array[int]", "ASNs com ROA"), _f("sinais", "array[string]", "Sinais presentes (S1 a S4)"), _f("confianca", "string", "Confiança do bloco", enum=["baixa", "media", "alta"]),
        _f("evidencias", "array", "Evidência de cada sinal"),
    ],
}

SCHEMA["subasignacoes_ipv4"] = {
    "key": "id",
    "description": (
        "Sub-asignações de IPv4 (aluguel regulado, política LAC-2025-5). ATENÇÃO: enquanto a bitácora pública oficial não existir (até 2026-11-02 não existe) esta coleção fica VAZIA e o esquema é "
        "HIPOTÉTICO; `/ipv4/subasignacoes` explica o estado. Cada linha traz as validações da política: `valida_*` é verdadeiro, falso ou nulo (sem dado); `em_conformidade` só é verdadeiro com todas verdadeiras."
    ),
    "fields": [
        _f("id", "string", "Identificador do registro"), _f("bloco", "string", "Bloco CIDR sub-asignado"), _f("receptor_asn", "int", "ASN do receptor"), _f("cedente_asn", "int", "ASN do cedente"),
        _f("inicio", "string", "Início"), _f("fim", "string", "Fim (vazio se em aberto)"), _f("em_conformidade", "bool", "Todas as validações verdadeiras"), _f("pendentes", "array[string]", "Validações sem dado"),
        _f("valida_receptor_origina", "bool", "O receptor origina o bloco"), _f("valida_tem_roa", "bool", "Há ROA do bloco para o receptor"), _f("valida_tamanho", "bool", "Entre /24 e /22"),
        _f("valida_receptor_ipv6", "bool", "O receptor tem IPv6"), _f("valida_prazo_3_anos", "bool", "3 anos desde a última transferência ou recuperação"), _f("valida_nao_infra_critica", "bool", "Não é infraestrutura crítica"),
    ],
}

SCHEMA["stfcs"] = {**SCHEMA["smps"], "description": (
    "Outorgas do Serviço Telefônico Fixo Comutado (STFC) da Anatel, geolocalizadas e cruzadas com ASNs do Registro.br por CNPJ. "
    "~1.700 CNPJs, incluindo pequenos provedores de VoIP e telefonia fixa. Mesmo formato de `scms`.")}
SCHEMA["seacs"] = {**SCHEMA["smps"], "description": (
    "Outorgas do Serviço de Acesso Condicionado (SeAC, TV por assinatura) da Anatel, geolocalizadas e cruzadas com ASNs do Registro.br "
    "por CNPJ. ~1.400 CNPJs. Mesmo formato de `scms`.")}


# ---------------------------------------------------------------------------
# Guia de operadores e receitas — ensinam a LLM a *encadear* as ferramentas.
# Devolvidos junto do schema para que cheguem mesmo sem o resource arandurape://recipes.
# ---------------------------------------------------------------------------

OPS_GUIDE: dict[str, str] = {
    "eq/ne": "igualdade. value escalar.",
    "gt/gte/lt/lte": "comparação numérica/ordinal. None nunca satisfaz.",
    "in/nin": "value é LISTA; pertinência do campo na lista.",
    "contains/ncontains": "substring em string (case-insensitive) OU pertinência em array. "
                          "É o operador para campos array como ixps_direct/ixps_origin/asns.",
    "exists": "value true/false — campo presente e não-nulo.",
    "aggregate/group_by": "agregação (group_by e/ou aggregate): `count` sem field conta linhas do grupo; `count` com field conta só os valores não nulos "
                          "daquele campo; sum/avg/min/max ignoram nulos. `sort` vale para os grupos e nomeia o alias do agregado (`count`, `sum_acessos` ou o `as`) "
                          "ou um campo de group_by; `limit` e `page` cortam os grupos (sem eles vêm todos, até 5.000) e a resposta traz `total_grupos`.",
    "within_radius": "geo; prefira a conveniência `near` no corpo da query (não monte à mão).",
}

# Receitas: pergunta em PT → sequência exata de ferramentas. As baseadas em `query`
# trazem o corpo pronto (collection + args), copiável quase direto para a tool `query`.
RECIPES: list[dict] = [
    {
        "pergunta": "O que mudou: ASNs brasileiros novos confirmados, do mais recente ao mais antigo",
        "ferramenta": "query",
        "args": {
            "collection": "eventos",
            "filter": {"and": [
                {"field": "tipo", "op": "eq", "value": "asn_novo"},
                {"field": "estado", "op": "eq", "value": "confirmado"},
            ]},
            "select": ["data", "asn", "uf"],
            "sort": [{"field": "data", "dir": "desc"}],
            "limit": 50,
        },
    },
    {
        "pergunta": "Prefixos que mudaram de origem e passaram a RPKI inválido (diferença observada, não acusação)",
        "ferramenta": "query",
        "args": {
            "collection": "eventos",
            "filter": {"and": [
                {"field": "tipo", "op": "eq", "value": "mudanca_origem"},
                {"field": "destaque", "op": "eq", "value": True},
            ]},
            "select": ["data", "entidade", "asn", "estado"],
            "limit": 50,
        },
    },
    {
        "pergunta": "Evolução de usuários e prefixos de um ASN nos snapshots com histórico",
        "ferramenta": "historico_serie",
        "args": {"escopo": "asn:28571", "metrics": "users,prefixes_v4,roa"},
    },
    {
        "pergunta": "Operadoras com mais de 5.000 assinantes sem ASN brasileiro vinculado (nem pelo CNPJ, nem pela raiz, nem pela marca)",
        "ferramenta": "query",
        "args": {
            "collection": "operadoras",
            "filter": {"and": [
                {"field": "acessos", "op": "gte", "value": 5000},
                {"field": "com_asn", "op": "eq", "value": False},
            ]},
            "select": ["empresa", "cnpj", "acessos", "asn_vinculo", "municipios", "uf_sede"],
            "sort": [{"field": "acessos", "dir": "desc"}],
            "limit": 50,
        },
    },
    {
        "pergunta": "Quem oferece banda larga em São Paulo (IBGE 3550308) e com que fatia",
        "ferramenta": "query",
        "args": {
            "collection": "acessos_municipio",
            "filter": {"field": "ibge", "op": "eq", "value": "3550308"},
            "select": ["empresa", "acessos", "share", "asns"],
            "sort": [{"field": "acessos", "dir": "desc"}],
            "limit": 20,
        },
    },
    {
        "pergunta": "Provedores de fibra do RS com mais de 10 mil acessos, do maior para o menor",
        "ferramenta": "query",
        "args": {
            "collection": "operadoras",
            "filter": {"and": [
                {"field": "uf_sede", "op": "eq", "value": "RS"},
                {"field": "meio", "op": "eq", "value": "Fibra"},
                {"field": "acessos", "op": "gte", "value": 10000},
            ]},
            "select": ["empresa", "acessos", "acessos_pf", "acessos_pj", "municipios", "asns"],
            "sort": [{"field": "acessos", "dir": "desc"}],
            "limit": 50,
        },
    },
    {
        "pergunta": "Operadoras com perfil corporativo (mais B2B que B2C)",
        "ferramenta": "query",
        "args": {
            "collection": "operadoras",
            "filter": {"and": [
                {"field": "ativo", "op": "eq", "value": True},
                {"field": "acessos", "op": "gte", "value": 500},
            ]},
            "select": ["empresa", "acessos", "acessos_pf", "acessos_pj", "asns"],
            "sort": [{"field": "acessos_pj", "dir": "desc"}],
            "limit": 50,
            "_nota": "compare acessos_pj com acessos_pf no resultado — a razão é o "
                     "perfil B2B, e um operador majoritariamente PJ tem necessidade "
                     "de peering diferente de um ISP residencial",
        },
    },
    {
        "pergunta": "Municípios onde um único operador tem mais de 80% do mercado",
        "ferramenta": "query",
        "args": {
            "collection": "acessos_municipio",
            "filter": {"and": [
                {"field": "share", "op": "gte", "value": 80},
                {"field": "municipio_acessos", "op": "gte", "value": 1000},
            ]},
            "select": ["municipio", "uf", "empresa", "share", "municipio_acessos",
                       "municipio_operadores"],
            "sort": [{"field": "municipio_acessos", "dir": "desc"}],
            "limit": 50,
        },
    },
    {
        "pergunta": "ASes BR com IPv6 mas sem RPKI presentes em ≥3 IXPs, do maior para o menor em usuários",
        "ferramenta": "query",
        "args": {
            "collection": "asns",
            "filter": {"and": [
                {"field": "is_br", "op": "eq", "value": True},
                {"field": "has_ipv6", "op": "eq", "value": True},
                {"field": "has_rpki", "op": "eq", "value": False},
                {"field": "ixps_direct_count", "op": "gte", "value": 3},
            ]},
            "select": ["asn", "name", "apnic_users", "uf"],
            "sort": [{"field": "apnic_users", "dir": "desc"}],
            "limit": 50,
        },
    },
    {
        "pergunta": "Quantos ASes brasileiros por macro-região e a média de usuários finais",
        "ferramenta": "query",
        "nota": "Só ASNs brasileiros (`is_br`, delegação LACNIC com país BR); os sem UF conhecida ficam no grupo de região vazia ('sem região'). "
                "Sem o filtro, os estrangeiros entram todos sem região.",
        "args": {
            "collection": "asns",
            "filter": {"field": "is_br", "op": "eq", "value": True},
            "group_by": ["region"],
            "aggregate": [{"fn": "count"}, {"fn": "avg", "field": "apnic_users", "as": "media_usuarios"}],
        },
    },
    {
        "pergunta": "Tabela de ASes por tipo de empresa (CNAE) com média de usuários",
        "ferramenta": "query",
        "args": {
            "collection": "asns",
            "filter": {"field": "cnae", "op": "exists", "value": True},
            "group_by": ["cnae"],
            "aggregate": [{"fn": "count"}, {"fn": "avg", "field": "apnic_users", "as": "media_usuarios"}],
        },
    },
    {
        "pergunta": "ASes diretos no PTT de SP mas NÃO no do RJ",
        "ferramenta": "query",
        "nota": "Álgebra de conjuntos na mesma collection sai do filtro composto sobre o array de membership.",
        "args": {
            "collection": "asns",
            "filter": {"and": [
                {"field": "ixps_direct", "op": "contains", "value": "sp"},
                {"field": "ixps_direct", "op": "ncontains", "value": "rj"},
            ]},
        },
    },
    {
        "pergunta": "ASes com sede a ≤20 km de Vitória",
        "ferramenta": "query",
        "nota": "`near` resolve o lugar e aplica o raio; não chame within_radius à mão. Nas coleções com posição de sede (asns, scms, smps, stfcs, seacs, operadoras, operadoras_movel) o raio mínimo é de 2 km (privacidade do endereço). Contatos não saem pelo `query`: só por `asn_contatos`, com chave e cota.",
        "args": {
            "collection": "asns",
            "near": {"place": "Vitória", "radius_km": 20},
            "select": ["asn", "name", "city", "uf", "apnic_users"],
        },
    },
    {
        "pergunta": "ASes a ≤80 km do PTT de Manaus que ainda não participam nem originam prefixos",
        "ferramenta": "ixp_proximos",
        "args": {"code": "mao", "radius_km": 80},
        "nota": "No resultado, filtre os itens com status == 'absent' (os 'direct'/'origin' já estão presentes).",
    },
    {
        "pergunta": "Em quantos PTTs a Globo está e quantos usuários finais alcança por esse caminho",
        "ferramentas": ["operadora_resolver(name='Globo') → pegue os asns",
                        "operator_reach(asns=<lista>)"],
        "nota": "Marcas multi-ASN (Claro, Vivo) exigem operadora_resolver antes de operadora_alcance.",
    },
    {
        "pergunta": "Detalhe completo de um AS específico (drill-down)",
        "ferramentas": ["asn_lista(q='nome') para achar o número, depois asn_detalhe(asn=<n>)",
                        "para vários de uma vez: asn_lote(asns=[...])"],
        "nota": "Para UMA entidade use asn_detalhe/ixp_detalhe; só use query para filtrar/cruzar/agregar conjuntos.",
    },
    {
        "pergunta": "Prefixos geolocalizados na Índia vistos no PTT SP",
        "ferramenta": "query",
        "nota": "Usa global_prefixes (todos os prefixos IX.br, com a posição usada só por dentro). "
                "ixps_seen é array — use contains. country é ISO 3166-1 alfa-2.",
        "args": {
            "collection": "global_prefixes",
            "filter": {"and": [
                {"field": "country", "op": "eq", "value": "IN"},
                {"field": "ixps_seen", "op": "contains", "value": "sp"},
            ]},
            "select": ["prefix", "ip_version", "origin_asn", "ixps_seen", "country"],
        },
    },
    {
        "pergunta": "Quantos prefixos por país são vistos no PTT SP (top 20)",
        "ferramenta": "query",
        "args": {
            "collection": "global_prefixes",
            "filter": {"field": "ixps_seen", "op": "contains", "value": "sp"},
            "group_by": ["country"],
            "aggregate": [{"fn": "count"}],
            "sort": [{"field": "count", "dir": "desc"}],
            "limit": 20,
        },
    },
    {
        "pergunta": "Outorgados SCM sem acessos declarados ao SICI, mas com usuários observáveis (APNIC), em MG",
        "ferramenta": "query",
        "nota": "Fato sobre a declaração, sem causa: diga 'sem declaração no mês X; usuários estimados (APNIC): Y'. `grupo_declara=true` = outro CNPJ do "
                "mesmo grupo declarou no mês. Cite mes_referencia e a data do snapshot.",
        "args": {
            "collection": "sem_declaracao_sici",
            "filter": {"and": [
                {"field": "classe", "op": "eq", "value": "com_usuarios_apnic"},
                {"field": "uf", "op": "eq", "value": "MG"},
            ]},
            "select": ["cnpj", "razao_social", "usuarios_apnic", "asns", "grupo_declara", "mes_referencia"],
            "sort": [{"field": "usuarios_apnic", "dir": "desc"}],
            "limit": 25,
        },
    },
    {
        "pergunta": "Operadoras em declínio contínuo de acessos declarados (6 meses ou mais), maiores primeiro",
        "ferramenta": "query",
        "nota": "Dado declarado à Anatel (autodeclarado). Parcela e variação são sobre acessos declarados do CNPJ, não sobre receita.",
        "args": {
            "collection": "indicadores_operadora",
            "filter": {"field": "em_declinio", "op": "eq", "value": True},
            "select": ["cnpj", "empresa", "acessos", "share_br", "meses_declinio", "var_aa_pct", "mes_referencia"],
            "sort": [{"field": "acessos", "dir": "desc"}],
            "limit": 25,
        },
    },
    {
        "pergunta": "Municípios a mais de 100 km de um PTT com baixa penetração de banda larga fixa (população acima de 20 mil)",
        "ferramenta": "query",
        "nota": "Penetração = acessos fixos declarados ÷ domicílios do Censo 2022; é indicador, não juízo. nao_visto é estimativa (inclui só-móvel). Cite mes_referencia do SICI e o Censo.",
        "args": {
            "collection": "municipios",
            "filter": {"and": [
                {"field": "sem_ptt_proximo", "op": "eq", "value": True},
                {"field": "populacao", "op": "gte", "value": 20000},
                {"field": "penetracao", "op": "lt", "value": 0.5},
            ]},
            "select": ["ibge", "nome", "uf", "populacao", "domicilios", "acessos", "penetracao", "km_ptt", "ptt_proximo", "mes_referencia"],
            "sort": [{"field": "populacao", "dir": "desc"}],
            "limit": 25,
        },
    },
    {
        "pergunta": "Organizações com mais de um ASN no Brasil (ASNs irmãos), maiores primeiro",
        "ferramenta": "query",
        "nota": "Organização inferida pelo CAIDA a partir do WHOIS: não é grupo societário (para esse, use a coleção socios). Cite a fonte e a data da coleta (describe de /asns/{asn}/organizacao).",
        "args": {
            "collection": "organizacoes_asn",
            "filter": {"field": "n_irmaos_br", "op": "gte", "value": 1},
            "select": ["asn", "org_nome", "n_irmaos_br", "irmaos_br"],
            "sort": [{"field": "n_irmaos_br", "dir": "desc"}],
            "limit": 25,
        },
    },
    {
        "pergunta": "Instalações (datacenters) do PeeringDB num PTT ou com muitas redes, e quais estão com o cadastro parado",
        "ferramenta": "query",
        "nota": "Cadastro autodeclarado no PeeringDB; `cadastro_classe` é inferido pelas datas e não diz nada da operação. Cite a fonte e a data da coleta (describe de /facilities).",
        "args": {
            "collection": "facilities",
            "filter": {"and": [{"field": "escopo", "op": "eq", "value": "brasil"}, {"field": "ptts", "op": "contains", "value": "sp"}]},
            "select": ["id", "nome", "org_nome", "cidade", "n_redes", "ptts", "cadastro_classe"],
            "sort": [{"field": "n_redes", "dir": "desc"}],
            "limit": 25,
        },
    },
    {
        "pergunta": "Sessões down há mais de uma semana nos route servers de um PTT do IX.br",
        "ferramenta": "query",
        "nota": "Medição no route server na data da coleta; ignore as linhas com rs_incerto. Não diz de quem é a causa da queda. Cite o PTT e a data da coleta (describe de /ixps/{code}/route-servers).",
        "args": {
            "collection": "rs_sessoes",
            "filter": {"and": [
                {"field": "ixp", "op": "eq", "value": "sp"},
                {"field": "estado", "op": "eq", "value": "down"},
                {"field": "dias_no_estado", "op": "gte", "value": 7},
                {"field": "rs_incerto", "op": "eq", "value": False},
            ]},
            "select": ["asn", "nome", "rs", "afi", "dias_no_estado", "last_error"],
            "sort": [{"field": "dias_no_estado", "dir": "desc"}],
            "limit": 25,
        },
    },
    {
        "pergunta": "Proporção de domicílios com acesso à Internet por grande região (TIC Domicílios)",
        "ferramenta": "query",
        "nota": "Estimativa amostral do Cetic.br|NIC.br com margem de erro; cite pesquisa, edição e margem e leia cada proporção como intervalo "
                "(proporção ± margem): regiões com intervalos sobrepostos não se distinguem, por isso a lista sai por região e não em ranking. "
                "Uma só tabela (A4, domicílios com acesso à Internet): o título 'acesso à Internet' também casa outras tabelas, que não se misturam.",
        "args": {
            "collection": "cetic_indicadores",
            "filter": {"and": [
                {"field": "pesquisa", "op": "eq", "value": "domicilios"},
                {"field": "tabela", "op": "eq", "value": "A4"},
                {"field": "dimensao", "op": "eq", "value": "Região"},
                {"field": "resposta", "op": "eq", "value": "Sim"},
            ]},
            "select": ["tabela", "titulo_tabela", "recorte", "proporcao", "margem_proporcao", "total", "edicao"],
            "sort": [{"field": "recorte", "dir": "asc"}],
            "limit": 10,
        },
    },
    {
        "pergunta": "ASNs de uma UF com validação RPKI medida alta (acima de 90%) e amostra suficiente",
        "ferramenta": "query",
        "nota": "Medição do APNIC por amostragem, não declaração da rede. Cite as fontes e as datas e use rov_amostras (>= 100). Não é ranking de empresas: descreva o que foi medido.",
        "args": {
            "collection": "seguranca_asn",
            "filter": {"and": [
                {"field": "uf", "op": "eq", "value": "SP"},
                {"field": "rov_validates_pct", "op": "gt", "value": 90},
                {"field": "rov_amostras", "op": "gte", "value": 100},
            ]},
            "select": ["asn", "uf", "rov_validates_pct", "rov_amostras", "dnssec_validates_pct"],
            "sort": [{"field": "rov_amostras", "dir": "desc"}],
            "limit": 25,
        },
    },
]


# Nome e esquema de URI do `.env` nos textos do catálogo: os textos acima usam o nome do software ("Arandurapé") como marcador.
from core.site import com_identidade as _identidade  # noqa: E402

for _k in list(SCHEMA):
    SCHEMA[_k] = _identidade(SCHEMA[_k])
OPS_GUIDE.update(_identidade(OPS_GUIDE))
RECIPES[:] = _identidade(RECIPES)
