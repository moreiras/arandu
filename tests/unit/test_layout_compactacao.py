# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`layout_version` 2: leitura nos dois formatos, compactação verificada, reversão e falha que devolve tudo ao lugar."""
import json

import pytest

from arandu import compactacao
from core import layout
from core.integridade import calcular_checksums


def _snapshot(base, data="2026-06-07", n=30):
    pub = base / "published" / data
    (pub / "asns").mkdir(parents=True)
    (pub / "maps").mkdir()
    for i in range(1, n + 1):
        (pub / "asns" / f"{i}.json").write_text(json.dumps({"asn": i, "nome": f"AS{i}"}), encoding="utf-8")
    (pub / "asns" / "index.json").write_text(json.dumps([{"asn": i} for i in range(1, n + 1)]), encoding="utf-8")
    (pub / "asns" / "names.json").write_text(json.dumps({"1": "A"}), encoding="utf-8")
    (pub / "maps" / "submarine_cables.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    (pub / "maps" / "asns.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [1]}), encoding="utf-8")
    (pub / "summary.json").write_text("{}", encoding="utf-8")
    man = {"snapshot_date": data, "layout_version": 1, "checksums": calcular_checksums(pub)}
    (pub / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    return pub


def _arvore(pub):
    return {str(p.relative_to(pub)): p.read_bytes() for p in sorted(pub.rglob("*")) if p.is_file() and p.name != "manifest.json"}


def test_compactar_deixa_um_zip_le_nos_dois_formatos_e_descompactar_devolve_o_mesmo(tmp_path):
    pub = _snapshot(tmp_path)
    antes = _arvore(pub)
    r = compactacao.compactar(tmp_path, "2026-06-07")
    assert r["estado"] == "compactado" and r["membros"] == 32
    assert not (pub / "asns").exists() and (pub / "asns.zip").is_file() and not (pub / ".compactacao").exists()
    assert not (pub / "maps" / "submarine_cables.geojson").exists() and (pub / "maps" / "asns.geojson").exists()
    man = json.loads((pub / "manifest.json").read_text())
    assert man["layout_version"] == 2 and "maps/submarine_cables.geojson" in man["compactado"]["compartilhados"]
    # leitura: o mesmo conteúdo por qualquer caminho
    assert json.loads(layout.ler_bytes(pub, "asns/7.json")) == {"asn": 7, "nome": "AS7"}
    assert layout.ler_bytes(pub, "asns/999.json") is None and layout.existe(pub, "asns/7.json") and not layout.existe(pub, "asns/999.json")
    assert layout.caminho(pub, "maps/submarine_cables.geojson").parent.parent.name == "_shared"
    from api.store import Store
    assert Store(tmp_path).asn_detail("2026-06-07", 7) == {"asn": 7, "nome": "AS7"}
    # reversão
    d = compactacao.descompactar(tmp_path, "2026-06-07")
    assert d["estado"] == "descompactado"
    assert _arvore(pub) == antes
    assert json.loads((pub / "manifest.json").read_text())["layout_version"] == 1
    assert [o.name for o in compactacao.orfaos_shared(tmp_path)] != []      # _shared sobrou sem uso: o gc pode limpar


def test_zip_diferente_do_diretorio_aborta_e_o_snapshot_fica_como_estava(tmp_path, monkeypatch):
    pub = _snapshot(tmp_path)
    antes = _arvore(pub)
    manifesto = (pub / "manifest.json").read_bytes()
    original = compactacao._montar_zip

    def corrompe(asns, destino):
        n = original(asns, destino)
        (asns / "3.json").write_text("{}", encoding="utf-8")      # o diretório muda depois do ZIP montado
        return n

    monkeypatch.setattr(compactacao, "_montar_zip", corrompe)
    with pytest.raises(compactacao.CompactacaoErro):
        compactacao.compactar(tmp_path, "2026-06-07")
    (pub / "asns" / "3.json").write_text(antes["asns/3.json"].decode(), encoding="utf-8")
    assert _arvore(pub) == antes and (pub / "manifest.json").read_bytes() == manifesto
    assert not (pub / "asns.zip").exists() and not (pub / ".compactacao").exists()


def test_divergencia_previa_do_manifesto_nao_impede_e_fica_registrada(tmp_path):
    """Snapshots antigos têm documentos corrigidos depois do manifesto; a compactação preserva o conteúdo e conta quantos eram."""
    pub = _snapshot(tmp_path)
    man = json.loads((pub / "manifest.json").read_text())
    man["checksums"]["asns/3.json"] = "sha256:" + "0" * 64
    (pub / "manifest.json").write_text(json.dumps(man))
    antes = _arvore(pub)
    r = compactacao.compactar(tmp_path, "2026-06-07")
    assert r["estado"] == "compactado" and r["divergentes_previos"] == 1
    assert json.loads((pub / "manifest.json").read_text())["compactado"]["asns"]["divergentes_previos"] == 1
    assert compactacao.descompactar(tmp_path, "2026-06-07")["estado"] == "descompactado"
    assert _arvore(pub) == antes


def test_leitura_pelo_store_que_falha_devolve_tudo_ao_lugar(tmp_path, monkeypatch):
    pub = _snapshot(tmp_path)
    antes = _arvore(pub)
    monkeypatch.setattr(compactacao, "_verificar_leitura_pela_api", lambda *a, **k: (_ for _ in ()).throw(compactacao.CompactacaoErro("simulado")))
    with pytest.raises(compactacao.CompactacaoErro):
        compactacao.compactar(tmp_path, "2026-06-07")
    assert _arvore(pub) == antes and json.loads((pub / "manifest.json").read_text())["layout_version"] == 1
    assert not (tmp_path / "published" / "_shared").exists() or not any((tmp_path / "published" / "_shared").rglob("*.geojson"))


def test_ja_compactado_nao_repete_e_snapshot_formato_1_continua_legivel(tmp_path):
    pub = _snapshot(tmp_path)
    assert layout.ler_bytes(pub, "asns/2.json") is not None            # formato 1: arquivo comum
    compactacao.compactar(tmp_path, "2026-06-07")
    assert compactacao.compactar(tmp_path, "2026-06-07")["estado"] == "ja-compactado"
