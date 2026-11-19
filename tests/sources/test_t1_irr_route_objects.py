# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — IRR TC e RADB: dumps RPSL sintéticos, sem rede (urllib simulado)."""
import io
from pathlib import Path

import pytest

from core import irr
from core.common import read_json_gz, write_json_gz
from sources.irr_route_objects import collect as fonte

BR = {64500, 64501, 64502}


class _Log:
    def info(self, *a, **k): pass
    warning = info


def test_parser_ignora_comentario_continuacao_e_outras_classes(fx):
    rotas, aut, contagem = irr.ler_dump(fx("irr_route_objects", "tc.db.gz"), BR)
    assert rotas == {64500: {"198.51.100.0/24", "2001:db8:100::/40"}, 64501: {"203.0.113.0/24"}}      # o duplicado (continuação) não repete; AS15169 fora
    assert aut == {64500} and contagem["route"] == 4 and contagem["route6"] == 1 and contagem["aut-num"] == 2 and contagem["invalidos_br"] == 0


def test_radb_prefixo_invalido_e_origem_mal_formada(fx):
    rotas, aut, contagem = irr.ler_dump(fx("irr_route_objects", "radb.db.gz"), BR)
    assert rotas == {64500: {"198.51.100.0/24", "198.51.101.0/24"}, 64501: {"203.0.113.0/24"}, 64502: {"2001:db8:200::/40"}}
    assert aut == {64501} and contagem["invalidos_br"] == 1 and contagem["route"] == 6 and contagem["route6"] == 1


def test_objetos_nao_exige_linha_em_branco_no_fim():
    objs = list(irr.objetos(io.StringIO("route: 10.0.0.0/8\norigin: AS1")))
    assert objs == [{"route": ["10.0.0.0/8"], "origin": ["AS1"]}]


@pytest.fixture
def dumps(fx, monkeypatch, tmp_path):
    """Troca a rede por arquivos locais: `baixar` copia o dump da fixture e `ler_serial` devolve o serial da fixture."""
    pedidos = []
    mapa = {"tc.db.gz": ("tc.db.gz", "TC.CURRENTSERIAL"), "radb.db.gz": ("radb.db.gz", "RADB.CURRENTSERIAL")}

    def baixar(url, destino: Path):
        pedidos.append(url)
        destino.write_bytes(fx("irr_route_objects", mapa[url.rsplit("/", 1)[1]][0]).read_bytes())
        return {"bytes": destino.stat().st_size, "sha256": "0" * 64}

    def serial(url):
        return fx("irr_route_objects", url.rsplit("/", 1)[1]).read_text().strip()
    monkeypatch.setattr(fonte, "baixar", baixar)
    monkeypatch.setattr(fonte, "ler_serial", serial)
    for nome, cfg in fonte.IRRS.items():
        monkeypatch.setitem(fonte.IRRS, nome, {**cfg, "minimo_objetos": 3, "minimo_asns_br": 1})
    # lista de ASNs brasileiros
    write_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "registro_br.json.gz", {"asns": [{"asn": a} for a in sorted(BR)]})
    return pedidos


def test_run_grava_normalizado_e_bruto(dumps, tmp_path):
    r = fonte.run("2026-11-02", tmp_path, _Log())
    assert r["TC"]["asns_br_com_route"] == 2 and r["RADB"]["asns_br_com_route"] == 3 and r["TC"]["serial"] == "376802"
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "irr_route_objects.json.gz")
    assert doc["rotas"]["RADB"]["64502"] == ["2001:db8:200::/40"] and doc["aut_num"] == {"TC": [64500], "RADB": [64501]} and doc["fontes"]["RADB"]["prefixos_br"] == 4
    assert (tmp_path / "raw" / "2026-11-02" / "summary" / "irr-tc-2026-11-02.db.gz").exists() and "mntner" not in str(doc) and "MAINT" not in str(doc)       # nem mantenedor nem texto


def test_serial_igual_reaproveita_sem_baixar(dumps, tmp_path):
    fonte.run("2026-11-02", tmp_path, _Log())
    dumps.clear()
    write_json_gz(tmp_path / "normalized" / "2026-12-02" / "summary" / "registro_br.json.gz", {"asns": [{"asn": a} for a in sorted(BR)]})
    r = fonte.run("2026-12-02", tmp_path, _Log())
    assert dumps == [] and r["TC"]["reaproveitado_de"] == "2026-11-02" and r["RADB"]["asns_br_com_route"] == 3
    doc = read_json_gz(tmp_path / "normalized" / "2026-12-02" / "summary" / "irr_route_objects.json.gz")
    assert doc["rotas"]["TC"]["64500"] and doc["fontes"]["TC"]["reaproveitado_de"] == "2026-11-02"
    fonte.run("2026-12-02", tmp_path, _Log(), forcar=True)
    assert len(dumps) == 2                                            # --force baixa de novo


def test_dump_pequeno_demais_falha_alto(dumps, tmp_path, monkeypatch):
    for nome, cfg in fonte.IRRS.items():
        monkeypatch.setitem(fonte.IRRS, nome, {**cfg, "minimo_objetos": 1000})
    with pytest.raises(RuntimeError, match="truncado"):
        fonte.run("2026-11-02", tmp_path, _Log())


def test_sem_lista_de_asns_br_falha(tmp_path):
    with pytest.raises(RuntimeError, match="registro_br"):
        fonte.run("2026-11-02", tmp_path, _Log())
