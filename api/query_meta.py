# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Fonte, selo e licença de cada collection de `query` (TRANSV-E12).

`META` declara, por collection, os ids de fonte do catálogo (`catalog/sources/`) de que as linhas dependem e o selo da natureza
predominante do conteúdo. O selo usa o vocabulário do frontend (`frontend/src/components/entidade/proveniencia.ts`, tipo `Selo`):
`fato` (declarado ou medido na fonte), `inferido` (derivado por regra) e `estimado` (amostragem ou modelo). Campo de natureza diferente
da predominante fica dito em `nota`. A licença vem do catálogo, não daqui: `uso_comercial_efetivo` é o pior caso entre as fontes e as
entradas delas (mesma regra de `docs/licencas.md`). `tests/unit/test_query_meta.py` falha se uma collection do `SCHEMA` não tiver
entrada ou se um id não existir no catálogo.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

SELOS = {
    "fato": "Dado declarado ou medido na fonte.",
    "inferido": "Derivado de outros dados por uma regra; pode estar errado.",
    "estimado": "Valor aproximado (amostragem ou modelo).",
}

_GEO = "posição geocodificada (estimada), não a posição exata"
_SICI = "acessos autodeclarados à Anatel no mês de referência do SICI, que não é a data do snapshot"

META: dict[str, dict[str, Any]] = {
    "asns": {"fontes": ["registro_br", "lg_ixbr", "fulltable_routeviews", "rpki_collector", "apnic_pop", "asn_names", "rdap", "cnpj_geo", "receita_cnpj"], "selo": "fato",
             "nota": "apnic_users, apnic_v6_users e pct_v6 são estimativas do APNIC; uf, city e cnpj vêm do cadastro do Registro.br e da Receita"},
    "ixps": {"fontes": ["curada_ixps", "curada_pix", "lg_ixbr", "ixbr_api", "fulltable_routeviews", "registro_br"], "selo": "fato"},
    "external_ixps": {"fontes": ["peeringdb_ixps", "curada_peeringdb_ixps", "decix_alice"], "selo": "fato", "nota": "cadastro autodeclarado no PeeringDB"},
    "cdns": {"fontes": ["curada_cdns", "lg_ixbr", "peeringdb_ixps"], "selo": "inferido", "nota": "presença deduzida dos ASNs da lista curada de CDNs entre os membros dos PTTs"},
    "prefixes": {"fontes": ["registro_br", "prefix_geo"], "selo": "fato", "nota": "UF e país do prefixo vêm de geolocalização estimada (DB-IP)"},
    "global_prefixes": {"fontes": ["lg_ixbr", "global_prefix_geo"], "selo": "fato", "nota": "país do prefixo vem de geolocalização estimada (DB-IP)"},
    "scms": {"fontes": ["anatel_scm", "anatel_outorgas", "scm_geo", "registro_br"], "selo": "fato", "nota": _GEO},
    "smps": {"fontes": ["anatel_smp", "anatel_outorgas", "smp_geo", "registro_br"], "selo": "fato", "nota": _GEO},
    "stfcs": {"fontes": ["anatel_stfc", "anatel_outorgas", "stfc_geo", "registro_br"], "selo": "fato", "nota": _GEO},
    "seacs": {"fontes": ["anatel_seac", "anatel_outorgas", "seac_geo", "registro_br"], "selo": "fato", "nota": _GEO},
    "operadoras": {"fontes": ["anatel_scm", "anatel_sici", "registro_br", "receita_cnpj"], "selo": "fato", "nota": _SICI},
    "operadoras_movel": {"fontes": ["anatel_smp", "anatel_sici_movel", "registro_br", "receita_cnpj"], "selo": "fato", "nota": _SICI},
    "acessos_municipio": {"fontes": ["anatel_sici"], "selo": "fato", "nota": _SICI + "; share e HHI são calculados"},
    "acessos_movel_municipio": {"fontes": ["anatel_sici_movel"], "selo": "fato", "nota": _SICI + "; share e HHI são calculados"},
    "socios": {"fontes": ["socios_grupos", "receita_socios", "receita_cnpj"], "selo": "inferido", "nota": "grupo econômico deduzido do cruzamento do quadro societário"},
    "eventos": {"fontes": ["registro_br", "lg_ixbr", "fulltable_routeviews", "rpki_collector", "caida_asrel", "anatel_scm", "anatel_smp", "anatel_stfc", "anatel_seac"], "selo": "fato",
                "nota": "diferença observada entre snapshots; provedor_novo e provedor_perdido são inferidos (natureza=inferido)"},
    "series_asn": {"fontes": ["lg_ixbr", "registro_br", "rpki_collector", "apnic_pop", "caida_asrel"], "selo": "fato", "nota": "users é estimativa do APNIC"},
    "indicadores_operadora": {"fontes": ["anatel_sici"], "selo": "fato", "nota": _SICI + "; share, posição e variações são calculados"},
    "sem_declaracao_sici": {"fontes": ["anatel_scm", "anatel_sici"], "selo": "fato", "nota": "fato sobre a declaração no mês de referência, sem causa nem intenção"},
    "municipios": {"fontes": ["ibge_censo_pnad", "anatel_sici", "curada_ixps", "ibge_malha_municipal"], "selo": "fato", "nota": "nao_visto é estimativa; " + _SICI},
    "seguranca_asn": {"fontes": ["apnic_irov", "apnic_dnssec", "caida_asrank", "bogons"], "selo": "fato",
                      "nota": "rov e dnssec são medições do APNIC por amostragem; asrank, cone e grau são inferência do CAIDA"},
    "rs_sessoes": {"fontes": ["ixbr_alice", "ixbr_api"], "selo": "fato"},
    "rs_communities": {"fontes": ["ixbr_alice_rotas", "ixbr_alice"], "selo": "fato"},
    "rs_filtradas": {"fontes": ["ixbr_alice_rotas", "ixbr_alice"], "selo": "fato", "nota": "motivo decodificado da community de rejeição"},
    "bloqueios_asn": {"fontes": ["ooni_bloqueios"], "selo": "fato", "nota": "medições de voluntários; anomalia declarada pela sonda não prova censura"},
    "organizacoes_asn": {"fontes": ["caida_as2org", "abusech"], "selo": "inferido", "nota": "organização e irmãos são inferência do CAIDA; feodo_c2 é contagem da lista do abuse.ch"},
    "transito_uf": {"fontes": ["caida_asrel", "registro_br", "caida_as2org", "apnic_pop"], "selo": "inferido", "nota": "relação provedor-cliente inferida (ARC)"},
    "transito_asn": {"fontes": ["caida_asrel", "registro_br", "caida_as2org", "apnic_pop"], "selo": "inferido", "nota": "relação provedor-cliente inferida (ARC)"},
    "facilities": {"fontes": ["peeringdb_fac", "peeringdb_ixps"], "selo": "fato", "nota": "cadastro autodeclarado; cadastro_classe é inferida pelas datas"},
    "facilidades_rede": {"fontes": ["peeringdb_fac"], "selo": "fato", "nota": "declaração no cadastro do PeeringDB"},
    "redes_peering": {"fontes": ["peeringdb_networks", "peeringdb_fac", "peeringdb_ixps"], "selo": "fato", "nota": "atributos autodeclarados; leitura de cadastro inferida pelas datas"},
    "cetic_indicadores": {"fontes": ["cetic_tic_domicilios_tabelas", "cetic_tic_provedores_tabelas"], "selo": "estimado", "nota": "estimativas amostrais publicadas pelo Cetic.br, com margem de erro"},
    "cetic_estimativas_uf": {"fontes": ["cetic_tic_domicilios_microdados"], "selo": "estimado", "nota": "estimativa do Arandurapé sobre microdados, não número publicado pelo Cetic.br"},
    "demanda_oferta": {"fontes": ["cetic_tic_domicilios_microdados", "ibge_censo_pnad", "anatel_sici"], "selo": "estimado", "nota": "estimativa do Arandurapé: domicílios projetados × proporção da TIC, contra acessos do SICI"},
    "erbs_municipio": {"fontes": ["anatel_erbs"], "selo": "fato", "nota": "estações licenciadas, não cobertura nem estações em operação"},
    "fust_municipio": {"fontes": ["anatel_fust"], "selo": "fato", "nota": "investimento é o valor previsto, não o desembolsado"},
    "prontidao_agregado": {"fontes": ["caida_spoofer", "irr_route_objects", "apnic_irov", "bogons", "rpki_collector", "peeringdb_networks", "apnic_pop"], "selo": "inferido",
                           "nota": "índice calculado por regra pública e versionada sobre medições de terceiros; não é veredito"},
    "prontidao_asn": {"fontes": ["caida_spoofer", "irr_route_objects", "apnic_irov", "bogons", "rpki_collector", "peeringdb_networks", "apnic_pop"], "selo": "inferido",
                      "nota": "índice calculado por regra pública e versionada sobre medições de terceiros; não é veredito"},
    "multas_empresa": {"fontes": ["anatel_multas"], "selo": "fato", "nota": "multa constituída não é condenação definitiva"},
    "qualidade_uf": {"fontes": ["anatel_rqual"], "selo": "fato"},
    "reclamacoes_marca": {"fontes": ["anatel_reclamacoes"], "selo": "fato"},
    "consumidor_marca": {"fontes": ["consumidor_gov"], "selo": "fato"},
    "faixas_espectro": {"fontes": ["anatel_pdff"], "selo": "fato", "nota": "norma de destinação, não licença nem uso"},
    "satelites_direitos": {"fontes": ["anatel_satelites"], "selo": "fato", "nota": "direito concedido, não capacidade em uso"},
    "transferencias_ipv4": {"fontes": ["ipv4_listas"], "selo": "fato", "nota": "o que as listas declaram, na data que declaram"},
    "recuperacao_ipv4": {"fontes": ["ipv4_listas", "ipv4_delegated"], "selo": "fato"},
    "eventos_bloco": {"fontes": ["ipv4_delegated"], "selo": "fato", "nota": "diferença observada entre duas fotos do delegated do LACNIC, sem causa"},
    "espaco_ipv4": {"fontes": ["ipv4_delegated", "ipv4_listas", "lg_ixbr", "rpki_collector"], "selo": "inferido", "nota": "não anunciado na tabela observada não quer dizer sem uso"},
    "uso_por_terceiros_ipv4": {"fontes": ["ipv4_delegated", "ipv4_listas", "lg_ixbr", "rpki_collector"], "selo": "inferido", "nota": "hipótese a partir de sinais, não afirma aluguel nem intenção"},
    "subasignacoes_ipv4": {"fontes": ["ipv4_subasignacao", "ipv4_listas"], "selo": "fato", "nota": "esquema hipotético: sem bitácora pública oficial a collection fica vazia"},
}

_GRAU = {"permitido": 0, "nao_verificado": 1, "restrito": 2}


@lru_cache(maxsize=1)
def _catalogo():
    from core.catalog.loader import load_catalog
    return load_catalog()


def meta_da_collection(collection: str) -> dict[str, Any]:
    """`{fontes, selo, uso_comercial_efetivo, nota_fonte?}` da collection; `{}` se não declarada (o teste impede o caso)."""
    m = META.get(collection)
    if m is None:
        return {}
    from core.catalog.loader import uso_comercial_efetivo
    cat = _catalogo()
    fontes, graus = [], []
    for sid in m["fontes"]:
        s = cat.sources.get(sid)
        if s is None:
            continue
        efetivo = uso_comercial_efetivo(cat, sid)
        graus.append(efetivo)
        o = s.origem
        fontes.append({"id": sid, "nome": s.nome, "licenca": o.licenca if o else "herdada das entradas",
                       "uso_comercial": o.uso_comercial if o else efetivo, "uso_comercial_efetivo": efetivo})
    pior = max(graus, key=lambda g: _GRAU[g]) if graus else "nao_verificado"
    return {"fontes": fontes, "selo": m["selo"], "uso_comercial_efetivo": pior, **({"nota_fonte": m["nota"]} if m.get("nota") else {})}


def resumo_do_indice(collection: str) -> dict[str, Any]:
    """Forma compacta para o índice do MCP: selo, uso comercial efetivo e ids das fontes."""
    m = meta_da_collection(collection)
    return {"selo": m["selo"], "uso_comercial": m["uso_comercial_efetivo"], "fontes": [f["id"] for f in m["fontes"]]} if m else {}
