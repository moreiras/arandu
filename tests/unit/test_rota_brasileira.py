# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rota brasileira = prefixo contido em bloco alocado pelo Registro.br; a origem não define (D4, BGP-E3).

Cenário da V1: AS174 está na lista de ASNs do Registro.br com um único bloco (`2804:5330::/32`) e origina milhares de rotas de outros
RIRs (`2408:8000::/…`, `2605:…`), que entravam no total de rotas brasileiras como "apenas origem BR" e nos filtráveis IPv6."""
import gzip
import json

from products.routing_analysis import build
from products.routing_analysis import resumo

D = "2026-11-22"


class _Log:
    def info(self, *a, **k): pass
    debug = warning = error = info


def _gz(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def _montar(tmp):
    norm = tmp / "normalized" / D / "summary"
    _gz(norm / "registro_br.json.gz", {"asns": [
        {"asn": 174, "name": "COGENT BRASIL", "cnpj": "1", "prefixes_v4": [], "prefixes_v6": ["2804:5330::/32"]},
        {"asn": 64500, "name": "PROVEDOR BR", "cnpj": "2", "prefixes_v4": ["198.18.0.0/15"], "prefixes_v6": ["2001:db8::/32"]},
    ]})
    _gz(norm / "origin-prefixes-v6.json.gz", {
        "174": ["2804:5330::/32", "2408:8000::/32", "2408:8000:1::/48", "2605:bc40::/32", "2605:bc40:c715:97e9::c715:97e9/128"],
        "64500": ["2001:db8::/32", "2001:db8:1::/48"],
        "65001": ["2001:db8:100::/48"],                        # ASN estrangeiro em bloco do Registro.br: continua rota brasileira
    })
    _gz(norm / "origin-prefixes-v4.json.gz", {"174": ["203.0.113.0/24", "203.0.113.0/25"], "64500": ["198.18.0.0/16", "198.19.0.0/24"]})
    _gz(norm / "prefix-set-v6.json.gz", [])
    _gz(norm / "prefix-set-v4.json.gz", [])
    assert build.run(D, tmp, _Log())
    pub = tmp / "published" / D
    return json.loads((pub / "routing_analysis.json").read_text()), json.loads((pub / resumo.ARQUIVO).read_text())


def test_so_prefixo_em_bloco_do_registro_br_e_rota_brasileira(tmp_path):
    ra, res = _montar(tmp_path)
    assert ra["summary"]["v6"]["pbr_routes"] == 4             # 2804:5330::/32, 2001:db8::/32, 2001:db8:1::/48, 2001:db8:100::/48
    assert ra["summary"]["v4"]["pbr_routes"] == 2
    for afi in ("v6", "v4"):
        c = ra["pbr_composition"][afi]
        assert c["strict_br"]["routes"] + c["prefix_only_br"]["routes"] == ra["summary"][afi]["pbr_routes"] == c["total"]["routes"]
    assert ra["pbr_composition"]["v6"]["prefix_only_br"]["routes"] == 1 and ra["pbr_composition"]["v6"]["strict_br"]["routes"] == 3
    assert res["rotas_br"]["v6"]["pbr_routes"] == 4 and res["rpki"]["v6"]["rotas"] == 4


def test_rede_brasileira_em_espaco_de_outro_rir_e_contada_a_parte(tmp_path):
    ra, res = _montar(tmp_path)
    fora = ra["pbr_composition"]["v6"]["asn_br_fora_de_bloco"]
    assert fora == {"routes": 4, "asns": 1, "fora_do_total": True}
    assert ra["pbr_composition"]["v6"]["origin_only_br"] == fora                 # nome antigo mantido como alias, fora do total
    assert ra["pbr_composition"]["v4"]["asn_br_fora_de_bloco"]["routes"] == 2
    assert res["rotas_br"]["v6"]["asn_br_fora_de_bloco"] == 4
    assert "Registro.br" in res["definicao"] and "origem" in res["definicao"]


def test_as174_fora_dos_filtraveis_e_da_agregacao_com_prefixo_de_outro_rir(tmp_path):
    ra, _ = _montar(tmp_path)
    filtraveis = {r["prefix"] for r in ra["too_specific"]["v6"]}
    assert not any(p.startswith(("2408:", "2605:")) for p in filtraveis)
    agreg = [r for r in ra["aggregation_by_asn"] if r["asn"] == 174]
    assert agreg == []                                        # o único bloco brasileiro do AS174 é um /32 sem mais-específico


def test_asn_brasileiro_pela_delegacao_lacnic(tmp_path):
    """Com `lacnic_delegated` (is_br), AS174 deixa de ser ASN brasileiro: sua rota no bloco brasileiro continua rota brasileira,
    como "apenas prefixo BR", e as de outros RIRs saem até da contagem de apoio."""
    _gz(tmp_path / "normalized" / D / "summary" / "lacnic_delegated.json.gz", {"br_asns": [64500]})
    ra, _ = _montar(tmp_path)
    c = ra["pbr_composition"]["v6"]
    assert ra["summary"]["v6"]["pbr_routes"] == 4 and c["strict_br"]["routes"] == 2 and c["prefix_only_br"]["routes"] == 2
    assert c["asn_br_fora_de_bloco"]["routes"] == 0 and ra["br_asns_registered"] == 1
