# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
"""T0 — o leitor GeoLite2 do Store abre o mmdb mais recente.

O log "mmdb loaded" não pode passar `path=` a um logger da stdlib (levanta TypeError): o `except`
o trataria como falha de carga e o leitor ficaria None, zerando as camadas de prefixos de PTT do mapa. Aqui `open_database` é falso e o logging é o real.
"""
import logging

from api import store as store_mod


class _FakeMaxmind:
    def __init__(self):
        self.opened: list[str] = []

    def open_database(self, path):
        self.opened.append(path)
        return object()


def test_mmdb_reader_abre_o_arquivo_mais_recente(tmp_path, monkeypatch, caplog):
    geo = tmp_path / "raw" / "geolite2"
    geo.mkdir(parents=True)
    for m in ("2026-08", "2026-10", "2026-09"):
        (geo / f"GeoLite2-City-{m}.mmdb").write_bytes(b"")
    fake = _FakeMaxmind()
    monkeypatch.setattr(store_mod, "_maxminddb", fake)

    with caplog.at_level(logging.INFO, logger="arandurape"):
        reader = store_mod.Store(tmp_path)._mmdb_reader()

    assert reader is not None
    assert fake.opened == [str(geo / "GeoLite2-City-2026-10.mmdb")]
    assert not [r for r in caplog.records if "load failed" in r.getMessage()]
