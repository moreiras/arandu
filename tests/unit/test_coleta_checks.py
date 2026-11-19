# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — sanidade de coleta: limites e estados dos checks do manifesto."""
import copy
import json

from publish import coleta_checks as cc

BASE = {"ixps_configured": ["sp", "rj"], "ixps_collected": ["sp", "rj"], "total_asns_br": 1000,
        "m3_prefixes_v4": 10000, "m3_prefixes_v6": 5000}


def test_snapshot_normal_e_completo():
    r = cc.evaluate(BASE, BASE, vrps=2000, vrps_prev=2000, pdb_registered=500)
    assert r["coleta_ok"] and r["coleta"] == "completa"
    assert {c["status"] for c in r["checks"].values()} == {"ok"}


def test_limites_de_variacao_da_regra_do_plano():
    cur = {**BASE, "total_asns_br": 1011, "m3_prefixes_v4": 10300, "m3_prefixes_v6": 5151}
    r = cc.evaluate(cur, BASE, vrps=2100, vrps_prev=2000, pdb_registered=500)
    c = r["checks"]
    assert c["asns_br"]["status"] == "falha"          # +1,1% > 1%
    assert c["prefixos_v4"]["status"] == "ok"         # +3,0% (limite inclusive)
    assert c["prefixos_v6"]["status"] == "falha"      # +3,02% > 3%
    assert c["vrps"]["status"] == "ok"                # +5,0%
    assert not r["coleta_ok"] and r["coleta"] == "parcial"


def test_ptt_faltando_e_listado():
    cur = {**BASE, "ixps_collected": ["sp"]}
    r = cc.evaluate(cur, BASE, 2000, 2000, 500)
    assert r["checks"]["ptt_coletados"] == {"status": "falha", "configurados": 2, "coletados": 1, "faltam": ["rj"]}
    assert r["coleta"] == "parcial"


def test_pdb_exige_mais_de_20_por_cento():
    assert cc.evaluate(BASE, BASE, 2000, 2000, 200)["checks"]["pdb_registrados"]["status"] == "falha"   # 20,0% não passa
    assert cc.evaluate(BASE, BASE, 2000, 2000, 201)["checks"]["pdb_registrados"]["status"] == "ok"


def test_sem_snapshot_anterior_nao_reprova_e_sem_rpki_fica_pendente():
    r = cc.evaluate(BASE, None, vrps=None, vrps_prev=None, pdb_registered=500)
    assert r["checks"]["asns_br"]["status"] == "sem_base"
    assert r["checks"]["vrps"]["status"] == "pendente"
    assert r["coleta_ok"] and r["coleta"] == "pendente"


def test_refresh_manifest_completa_os_vrps_e_marca_parcial(tmp_path):
    def snap(date, manifest, vrps):
        d = tmp_path / "published" / date
        (d / "rpki").mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps(manifest))
        import gzip
        with gzip.open(d / "rpki" / "vrp_list.json.gz", "wt") as f:
            json.dump([{"asn": i} for i in range(vrps)], f)

    snap("2026-09-13", BASE, 100)
    snap("2026-09-20", copy.deepcopy(BASE), 70)          # 30% menos VRPs: coleta de RPKI incompleta
    m = cc.refresh_manifest(tmp_path, "2026-09-20")
    assert m["comparado_com"] == "2026-09-13"
    assert m["checks"]["vrps"]["status"] == "falha" and m["coleta"] == "parcial" and not m["coleta_ok"]
    again = json.loads((tmp_path / "published" / "2026-09-20" / "manifest.json").read_text())
    assert again["checks"]["vrps"]["variacao_pct"] == -30.0


def test_asn_names_detecta_o_formato_diferente_de_2026_10_11():
    normal = {"total": 122666, "pct_hifen": 68.2}
    ruim = {"total": 128261, "pct_hifen": 32.2}                    # medido no snapshot de 11/10
    assert cc._check_asn_names(normal, {"total": 122469, "pct_hifen": 68.2})["status"] == "ok"
    r = cc._check_asn_names(ruim, normal)
    assert r["status"] == "falha" and r["variacao_pontos_hifen"] == -36.0
    assert cc._check_asn_names(normal, ruim)["status"] == "falha"        # a volta ao normal também é mudança
    assert cc._check_asn_names(normal, None)["status"] == "sem_base"
    assert cc._check_asn_names(None, normal)["status"] == "pendente"


def test_asn_names_variacao_so_de_quantidade_tambem_falha():
    assert cc._check_asn_names({"total": 130000, "pct_hifen": 68.0}, {"total": 122000, "pct_hifen": 68.0})["status"] == "falha"


def test_asn_names_stats_conta_o_formato_handle_hifen_descricao():
    assert cc.asn_names_stats({"1": "A - b, BR", "2": "sem formato", "3": "C - d, US", "4": "x"}) == {"total": 4, "pct_hifen": 50.0}
    assert cc.asn_names_stats({}) is None and cc.asn_names_stats(None) is None


def test_evaluate_inclui_asn_names_so_quando_ha_dados_e_marca_parcial():
    m = {"ixps_configured": ["sp"], "ixps_collected": ["sp"], "total_asns_br": 100}
    out = cc.evaluate(m, None, None, None, 60, {"total": 100, "pct_hifen": 30.0}, {"total": 100, "pct_hifen": 68.0})
    assert out["checks"]["asn_names"]["status"] == "falha" and out["coleta"] == "parcial" and out["coleta_ok"] is False
    assert "asn_names" not in cc.evaluate(m, None, None, None, 60)["checks"]
