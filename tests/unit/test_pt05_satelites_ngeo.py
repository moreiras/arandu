# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""NGEO: um sistema por linha (REGULATORIO-E1)."""
import io

from core.satelites import consolidar, sistemas_ngeo

# ── REGULATORIO-E1: NGEO um sistema por linha ──

CAB = "NU_CNPJ;NO_PRESTADORA;DT_LANCAMENTO;SG_ESTACAO;NO_COMERCIAL_OBJETO;STATUS_OPERACAO;ORBITA_NGEO;QT_PLANO_NGEO;QT_CONSTELACAO_NGEO"


def _csv(linhas, extra=""):
    return io.BytesIO(("\n".join([CAB + extra] + linhas) + "\n").encode("utf-8"))


def _vazio(cab):
    return io.BytesIO((cab + "\n").encode("utf-8"))


DIR = "Operadora (Operator);Satélite (Satellite);Código do Direito (Code);Posição Orbital (Orbital slot);Banda do satélite exercendo o direito (Satellite Band);Tipo de Direito (Type of landing right);Status;Data de lançamento (Launch date);Validade (Validity);Direito prorrogado (Landing right postponed)"
OPE = "Satélite em operação;Posição orbital;Bandas do satélite;Tipo de Direito;Operadora comercial"


def test_ngeo_um_sistema_por_linha_com_a_faixa_declarada():
    starlink = [(2022, 2661), (2023, 4408), (2024, 4408), (2025, 7184), (2026, 9857)]
    linhas = [f";STARLINK BRAZIL;01/01/2019;STL;Starlink;OPERAÇÃO COMERCIAL;BAIXA (LEO);72;{q};01/01/{a};{a};555" for a, q in starlink]
    om = ";OMNISPACE;01/01/2020;OMN;Omnispace F2;OPERAÇÃO COMERCIAL;BAIXA (LEO);1;2;01/01/2026;2026;777"
    linhas += [om] * 7                                                     # cópias exatas da origem
    t, n = consolidar(_vazio(DIR), _csv(linhas, ";DT_AGENDA_EE;AGENDA_EE_ANO;NU_ESTACAO"), _vazio(OPE))
    assert n["ngeo"] == 6                                                  # 5 da Starlink + 1 Omnispace
    sis = {x["objeto"]: x for x in sistemas_ngeo(t["ngeo"])}
    assert len(sis) == 2
    st = sis["Starlink"]
    assert (st["registros"], st["constelacao"], st["constelacao_min"], st["constelacao_max"]) == (5, 9857, 2661, 9857)
    assert st["anos_agenda"] == [2022, 2023, 2024, 2025, 2026]
    assert sis["Omnispace F2"]["registros"] == 1


def test_ngeo_leiaute_antigo_sem_ano_de_agenda():
    linhas = [";P;01/01/2019;STL;Starlink;OPERAÇÃO COMERCIAL;BAIXA (LEO);72;2661", ";P;01/01/2019;STL;Starlink;OPERAÇÃO COMERCIAL;BAIXA (LEO);72;9857",
              ";P;01/01/2019;STL;Starlink;OPERAÇÃO COMERCIAL;BAIXA (LEO);72;9857"]
    t, n = consolidar(_vazio(DIR), _csv(linhas), _vazio(OPE))
    assert n["ngeo"] == 2 and "agenda_ano" not in t["ngeo"][0]
    (st,) = sistemas_ngeo(t["ngeo"])
    assert st["registros"] == 2 and st["anos_agenda"] == [] and st["constelacao"] == 9857        # sem ano: o último na ordem da origem


def test_api_agrupa_ngeo_de_snapshot_antigo():
    from api.services.regulatorio import satelites_resumo
    reg = {"cnpj": None, "prestadora": "P", "lancamento": None, "estacao": "S", "objeto": "Sistema", "status": "x", "orbita": "LEO", "planos": 1}
    doc = {"snapshot_date": "d", "resumo": {"ngeo": 2}, "ngeo": [{**reg, "constelacao": 10}, {**reg, "constelacao": 20}], "operando": []}
    r = satelites_resumo(doc)
    assert r["resumo"]["ngeo_sistemas"] == 1 and r["ngeo_sistemas"][0]["constelacao_max"] == 20
