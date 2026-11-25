# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 (PT-20, TRANSV-E12 e TRANSV-E17): fonte, selo e licença por collection; textos do índice e mapa de detalhe."""
import re
from pathlib import Path

import pytest

from api.query_catalogo import RESUMO_INDICE, SCHEMA
from api.query_meta import META, SELOS, meta_da_collection, resumo_do_indice
from core.catalog.loader import load_catalog
from mcp_server import guia

ROOT = Path(__file__).resolve().parents[2]


def test_toda_collection_tem_meta_e_nenhuma_sobra():
    assert set(META) == set(SCHEMA)


def test_ids_existem_no_catalogo_e_selo_e_do_vocabulario():
    cat = load_catalog()
    for nome, m in META.items():
        assert m["fontes"], nome
        assert not [s for s in m["fontes"] if s not in cat.sources], (nome, m["fontes"])
        assert m["selo"] in SELOS, nome


def test_bloqueios_asn_e_restrita_e_cita_o_ooni():
    m = meta_da_collection("bloqueios_asn")
    assert [f["id"] for f in m["fontes"]] == ["ooni_bloqueios"]
    assert m["uso_comercial_efetivo"] == "restrito"


def test_operadoras_traz_anatel_aberta_com_licenca():
    m = meta_da_collection("operadoras")
    sici = next(f for f in m["fontes"] if f["id"] == "anatel_sici")
    assert sici["uso_comercial"] == "permitido" and "Anatel" in sici["licenca"]


def test_fonte_nao_verificada_aparece_como_nao_verificada():
    m = meta_da_collection("asns")
    apnic = next(f for f in m["fontes"] if f["id"] == "apnic_pop")
    assert apnic["uso_comercial"] == "nao_verificado"
    assert m["uso_comercial_efetivo"] in ("nao_verificado", "restrito")      # pior caso, nunca "permitido" com fonte não verificada


def test_pior_caso_e_o_maximo_das_fontes():
    ordem = {"permitido": 0, "nao_verificado": 1, "restrito": 2}
    for nome in META:
        m = meta_da_collection(nome)
        assert ordem[m["uso_comercial_efetivo"]] == max(ordem[f["uso_comercial_efetivo"]] for f in m["fontes"]), nome


def test_indice_compacto():
    assert resumo_do_indice("bloqueios_asn") == {"selo": "fato", "uso_comercial": "restrito", "fontes": ["ooni_bloqueios"]}


def test_descricao_do_ixps_sem_numero_fixo():
    """TRANSV-E17: a contagem de PTTs vem do dado (`count` de GET /ixps), não de texto."""
    d = SCHEMA["ixps"]["description"]
    assert not re.search(r"\b(39|40)\b", d), d


def test_resumo_do_indice_mantem_o_aviso_do_sici_e_cabe_no_corte():
    for nome in ("operadoras", "operadoras_movel", "municipios", "indicadores_operadora"):
        r = RESUMO_INDICE[nome]
        assert "SICI" in r and "mês de referência" in r.lower() and len(r) <= 150, nome
        assert nome in SCHEMA


def test_ferramenta_detalhe_de_faixas_e_satelites_nao_aponta_para_historico():
    assert guia.DETALHE_DA_COLLECTION["faixas_espectro"] is None
    assert guia.DETALHE_DA_COLLECTION["satelites_direitos"] is None
    assert set(guia.DETALHE_DA_COLLECTION) == set(SCHEMA)


@pytest.mark.parametrize("arquivo", ["mcp_server/tools_entidades.py", "mcp_server/recursos.py"])
def test_textos_do_mcp_sem_contagem_de_ptt_desatualizada(arquivo):
    txt = (ROOT / arquivo).read_text(encoding="utf-8")
    assert not re.search(r"\b39 (códigos|looking)", txt)
    assert "Ver list_ixps" not in txt


def test_selos_por_campo_citam_campos_que_existem_e_sao_do_vocabulario():
    for nome, m in META.items():
        campos = {f["name"] for f in SCHEMA[nome]["fields"]}
        for campo, selo in m.get("selos_campo", {}).items():
            assert campo in campos, (nome, campo)
            assert selo in SELOS and selo != m["selo"], (nome, campo)


def test_asns_nao_carimba_estimativa_do_apnic_como_fato():
    """Collection que mistura cadastro com estimativa não pode passar um selo único: o campo estimado traz o próprio selo."""
    m = meta_da_collection("asns")
    assert m["selo"] == "fato"
    assert {k: m["selos_campo"][k] for k in ("apnic_users", "apnic_v6_users", "pct_v6")} == dict.fromkeys(("apnic_users", "apnic_v6_users", "pct_v6"), "estimado")
    assert meta_da_collection("seguranca_asn")["selos_campo"]["cone_asns"] == "inferido"
    assert "selos_campo" not in meta_da_collection("ixps")
