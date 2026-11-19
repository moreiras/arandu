# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — contagens do Registro.br com os nomes `registro_br_` e `m3_`: o snapshot já publicado só tem o segundo, e toda leitura da
API devolve os dois com o mesmo valor."""
import json

from api import snapshot_detail
from api.repos.documentos import DocumentosRepo
from core.chaves_registro import PARES, com_os_dois_nomes
from publish import coleta_checks

ANTIGO = {"snapshot_date": "2026-10-11", "m3_asns": 36, "m3_prefixes_v4": 76, "m3_prefixes_v6": 43,
          "m3_declared_space_v4": 39680, "m3_declared_space_v6": 7}


def test_completa_nos_dois_sentidos_sem_alterar_o_original():
    antes = dict(ANTIGO)
    d = com_os_dois_nomes(ANTIGO)
    assert ANTIGO == antes and d["registro_br_asns"] == 36 and d["registro_br_prefixes_v6"] == 43
    assert com_os_dois_nomes({"registro_br_prefixes_v4": 5})["m3_prefixes_v4"] == 5
    assert "registro_br_declared_space_v4_24" not in d                  # par ausente fica ausente
    assert com_os_dois_nomes(None) is None and com_os_dois_nomes([1]) == [1]
    assert all(novo.startswith("registro_br_") and antigo.startswith("m3_") for antigo, novo in PARES.items())


def test_resumo_e_manifesto_de_snapshot_antigo_saem_com_os_dois_nomes(tmp_path):
    pub = tmp_path / "2026-10-11"
    pub.mkdir()
    (pub / "summary.json").write_text(json.dumps(ANTIGO))
    (pub / "manifest.json").write_text(json.dumps({"m3_prefixes_v4": 76, "m3_prefixes_v6": 43}))
    repo = DocumentosRepo(lambda d: tmp_path / d)
    s, m = repo.summary("2026-10-11"), repo.manifest("2026-10-11")
    assert s["registro_br_asns"] == s["m3_asns"] == 36
    assert m["registro_br_prefixes_v4"] == m["m3_prefixes_v4"] == 76
    assert repo.manifest_em_memoria("2026-10-11")["registro_br_prefixes_v6"] == 43
    assert "registro_br_asns" not in json.loads((pub / "summary.json").read_text())   # o publicado não muda


def test_detalhe_gravado_so_com_nomes_antigos_sai_com_os_dois(tmp_path):
    pub = tmp_path / "published" / "2026-10-11"
    pub.mkdir(parents=True)
    (pub / snapshot_detail.SIDECAR).write_text(json.dumps({"versao": snapshot_detail.SIDECAR_VERSION, "date": "2026-10-11",
                                                          "summary": {"m3_declared_space_v4_24": 155}, "manifest": None}))
    d = snapshot_detail.read_sidecar(tmp_path, "2026-10-11")
    assert d["summary"]["registro_br_declared_space_v4_24"] == d["summary"]["m3_declared_space_v4_24"] == 155


def test_sanidade_de_coleta_compara_com_manifesto_anterior_que_so_tem_o_nome_antigo():
    atual = {"ixps_configured": [], "ixps_collected": [], "total_asns_br": 100, "registro_br_prefixes_v4": 1000,
             "registro_br_prefixes_v6": 500, "m3_prefixes_v4": 1000, "m3_prefixes_v6": 500}
    anterior = {"total_asns_br": 100, "m3_prefixes_v4": 1000, "m3_prefixes_v6": 500}
    r = coleta_checks.evaluate(atual, anterior, vrps=None, vrps_prev=None, pdb_registered=None)
    assert r["checks"]["prefixos_v4"]["status"] == "ok" and r["checks"]["prefixos_v6"]["status"] == "ok"
