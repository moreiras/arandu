# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produto `bloqueios` (OONI): janela, mínimo por célula, ASN fora do snapshot, licença e aviso."""
from api.services import bloqueios as s
from core import ooni
from products.bloqueios import build

DOC = {
    "janela_dias": 28, "horas_amostra_web": [2, 10, 18],
    "dias": {
        "2026-11-05": {"testes": {"whatsapp": {"64496": {"n": 6, "anom": 1, "partes": {"web": 1}}, "64497": {"n": 3, "anom": 3}, "64999": {"n": 50, "anom": 0}},
                                  "tor": {"64496": {"n": 12, "anom": 0, "alvos": {"obfs4": [168, 40]}}}},
                       "web": {"64496": {"n": 20, "anom": 4, "partes": {"dns": 4}, "sem_veredito": 1, "inacessivel": 3}},
                       "web_amostra": {"arquivos": 3, "bytes": 100, "completa": True}},
        "2026-11-06": {"testes": {"whatsapp": {"64496": {"n": 6, "anom": 0}, "64497": {"n": 3, "anom": 0}}}, "web": None, "web_amostra": None},
    },
}


def test_janela_soma_dias_e_aplica_o_minimo_por_celula():
    r = build.calcular(DOC, {64496, 64497})
    assert r["janela"] == {"inicio": "2026-11-05", "fim": "2026-11-06", "dias_com_dado": 2, "dias_da_janela": 28}
    por = {t["teste"]: t for t in r["asns"]["64496"]["testes"]}
    assert por["whatsapp"] == {"teste": "whatsapp", "rotulo": "WhatsApp", "n": 12, "anomalias": 1, "pct_anomalia": 8.33, "partes": {"web": 1}}
    assert "64497" not in r["asns"]                                              # 6 medições < 10: não publica, mesmo com 3 anomalias
    res = {t["teste"]: t for t in r["testes"]}
    assert res["whatsapp"]["asns_abaixo_do_minimo"] == 1 and res["whatsapp"]["asns_fora_do_snapshot"] == 1
    assert "64999" not in r["asns"]
    assert por["tor"]["alvos_acessiveis_pct"] == {"obfs4": 23.81}


def test_web_vem_como_amostra_com_o_aviso_do_veredito():
    r = build.calcular(DOC, {64496}, minimo=10)
    w = {t["teste"]: t for t in r["asns"]["64496"]["testes"]}["webconnectivity"]
    assert w["amostra"] is True and w["n"] == 20 and w["anomalias"] == 4 and w["inacessivel"] == 3
    assert r["web_amostra"]["dias_com_amostra"] == 1 and "sonda" in ooni.CRITERIOS["webconnectivity"]


def test_servico_bloco_licenca_aviso_e_linhas():
    pub = {"snapshot_date": "2026-11-07", "coletado_em": "x", "fonte": {"licenca": "CC BY-NC-SA 4.0"}, "licenca": "CC BY-NC-SA 4.0", "aviso": ooni.AVISO, "limites": "l",
           **build.calcular(DOC, {64496, 64497}, minimo=1)}
    b = s.bloco_asn(pub, 64496)
    assert b["licenca"] == "CC BY-NC-SA 4.0" and "sonda" in b["aviso"] and {t["teste"]: t for t in b["testes"]}["whatsapp"]["n"] == 12
    assert all(t["criterio"] for t in b["testes"])
    assert s.bloco_asn(pub, 1) is None and s.bloco_asn(None, 64496) is None
    ln = s.linhas(pub)
    assert {(x["asn"], x["teste"]) for x in ln} >= {(64496, "whatsapp"), (64497, "whatsapp")}
    assert all(x["licenca"] == "CC BY-NC-SA 4.0" and x["veredito"] == "da sonda" for x in ln)
    from api.privacidade import sem_contatos
    assert sem_contatos(s.bloco_asn(pub, 64496)) == s.bloco_asn(pub, 64496)           # nada que o filtro de contatos da API removeria
