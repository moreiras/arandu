# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Nome dos membros de IXP externo: snapshots podem trazer o nome do PTT em todo membro."""
import json

from api.store import Store


def test_nome_do_ptt_nunca_sai_como_nome_do_membro(tmp_path, monkeypatch):
    pub = tmp_path / "published" / "2026-11-13" / "external-ixps"
    pub.mkdir(parents=True)
    (pub / "decix-sp.json").write_text(json.dumps({"code": "decix-sp", "name": "DE-CIX Sao Paulo", "members": [
        {"asn": 6939, "name": "DE-CIX Sao Paulo", "speed": 100000, "is_br": False},
        {"asn": 64500, "name": "DE-CIX Sao Paulo", "speed": 10000, "is_br": True},
        {"asn": 64501, "name": "Rede Própria, BR", "speed": 10000, "is_br": True}]}))
    s = Store(tmp_path)
    monkeypatch.setattr(s, "asn_names", lambda d: {"6939": "HURRICANE - Hurricane Electric LLC, US"})
    nomes = {m["asn"]: m["name"] for m in s.external_ixp_detail("2026-11-13", "decix-sp")["members"]}
    assert nomes == {6939: "HURRICANE - Hurricane Electric LLC, US", 64500: "", 64501: "Rede Própria, BR"}
