# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — abuse.ch (Feodo Tracker): lista → contagens por ASN, sem IPs, sem rede."""
import gzip
import json

import pytest
import respx

from core.common import read_json_gz
from sources.abusech import collect as fonte


def _lista(fx):
    return json.loads(fx("abusech", "ipblocklist.json").read_text(encoding="utf-8"))


def test_agregar_conta_por_asn_e_descarta_entrada_sem_asn(fx):
    r = fonte.agregar(_lista(fx))
    assert r["total"] == 4 and r["online"] == 2
    assert r["asns"]["64497"] == {"c2_total": 2, "c2_online": 1, "malware": {"Emotet": 1, "QakBot": 1}}
    assert set(r["asns"]) == {"64497", "64510"}


@respx.mock
def test_run_grava_so_contagens_sem_ip(base, log, fx, date_str):
    respx.get(fonte.URL_FEODO).respond(200, json=_lista(fx))
    r = fonte.run(date_str, base, log)
    assert r == {"total": 4, "asns": 2}
    p = base / "normalized" / date_str / "summary" / "abusech.json.gz"
    texto = gzip.decompress(p.read_bytes()).decode()
    assert "203.0.113" not in texto and "198.51.100" not in texto and "ip_address" not in texto and "hostname" not in texto      # privacidade: só agregado
    d = read_json_gz(p)
    assert d["urlhaus"]["estado"] == "indisponivel" and d["licenca"].startswith("CC0")


@respx.mock
def test_lista_vazia_e_resultado_valido_e_formato_inesperado_falha(base, log, date_str):
    respx.get(fonte.URL_FEODO).respond(200, json=[])
    assert fonte.run(date_str, base, log)["total"] == 0
    respx.get(fonte.URL_FEODO).respond(200, json={"erro": "x"})
    with pytest.raises(RuntimeError):
        fonte.run(date_str, base, log)
