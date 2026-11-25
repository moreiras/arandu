# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Script de pessoa natural sobre snapshot compactado (`asns.zip`): regrava o ZIP, guarda o original e reconcilia o manifesto com o disco."""
import gzip
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from core.integridade import sha256_arquivo

DATA = "2026-07-05"


def _script():
    spec = importlib.util.spec_from_file_location("mascarar_pn", Path(__file__).resolve().parents[2] / "scripts" / "mascarar_pessoa_natural_publicados.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def snap(tmp_path):
    dados = tmp_path / "data"
    s = dados / "normalized" / DATA / "summary"
    s.mkdir(parents=True)
    with gzip.open(s / "geo_orgs.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"orgs": {"65001": {"cnpj": "12345678000195", "razao_social": "FULANO DE TAL", "codigo_natureza_juridica": 2135}}}, f)
    pub = dados / "published" / DATA
    pub.mkdir(parents=True)
    membros = {"65001.json": {"asn": 65001, "name": "FULANO DE TAL"}, "65002.json": {"asn": 65002, "name": "REDE LTDA"}, "index.json": [65001, 65002]}
    with zipfile.ZipFile(pub / "asns.zip", "w") as z:
        z.writestr("65002.json", json.dumps(membros["65002.json"]), compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("65001.json", json.dumps(membros["65001.json"]), compress_type=zipfile.ZIP_STORED)
        z.writestr("index.json", json.dumps(membros["index.json"]), compress_type=zipfile.ZIP_DEFLATED)
    (pub / "outro.json").write_text("{}")
    sums = {"outro.json": sha256_arquivo(pub / "outro.json"), **{f"asns/{n}": "sha256:" + "0" * 64 for n in membros}}
    (pub / "manifest.json").write_text(json.dumps({"date": DATA, "checksums": sums}))
    return dados, pub


def _manifesto(pub):
    return json.loads((pub / "manifest.json").read_text())


def _estado(pub):
    return {p.name: p.read_bytes() for p in pub.iterdir() if p.is_file()}


def test_simulacao_nao_altera_nada(snap, tmp_path):
    dados, pub = snap
    antes = _estado(pub)
    assert _script().main([str(dados), "--corrigir-manifesto", "--copias", str(tmp_path / "orig")]) == 0
    assert _estado(pub) == antes and not (tmp_path / "orig").exists()


def test_aplicar_mascara_o_zip_guarda_o_original_e_reconcilia_o_manifesto(snap, tmp_path):
    dados, pub = snap
    original = (pub / "asns.zip").read_bytes()
    with zipfile.ZipFile(pub / "asns.zip") as z:
        ordem, tipos = z.namelist(), {i.filename: i.compress_type for i in z.infolist()}
    assert _script().main([str(dados), "--aplicar", "--corrigir-manifesto", "--copias", str(tmp_path / "orig")]) == 0
    with zipfile.ZipFile(pub / "asns.zip") as z:
        assert z.namelist() == ordem and {i.filename: i.compress_type for i in z.infolist()} == tipos
        assert "FULANO" not in z.read("65001.json").decode() and json.loads(z.read("65002.json"))["name"] == "REDE LTDA"
        assert json.loads(z.read("index.json")) == [65001, 65002]
    assert (tmp_path / "orig" / DATA / "asns.zip").read_bytes() == original
    assert not list(pub.glob("*.tmp*"))
    man = _manifesto(pub)
    assert set(man["checksums"]) == {"outro.json", "asns.zip"}
    assert all(sha == sha256_arquivo(pub / rel) for rel, sha in man["checksums"].items())
    assert man["manifesto_reconciliado"]["removidos"] == 3 and man["privacidade"]["pessoa_natural"]
    assert len(man["correcoes"]) == 2


def test_idempotente(snap, tmp_path):
    dados, pub = snap
    args = [str(dados), "--aplicar", "--corrigir-manifesto", "--copias", str(tmp_path / "orig")]
    assert _script().main(args) == 0
    antes = _estado(pub)
    assert _script().main(args) == 0
    assert _estado(pub) == antes


def test_membro_ausente_do_zip_nao_e_removido_e_e_reportado(snap, tmp_path, capsys):
    dados, pub = snap
    man = _manifesto(pub)
    man["checksums"]["asns/99999.json"] = "sha256:" + "1" * 64
    (pub / "manifest.json").write_text(json.dumps(man))
    assert _script().main([str(dados), "--aplicar", "--corrigir-manifesto", "--copias", str(tmp_path / "orig")]) == 2
    assert "asns/99999.json" in _manifesto(pub)["checksums"]
    assert "fora do zip: asns/99999.json" in capsys.readouterr().out


def test_divergencia_de_checksum_e_reportada_sem_corrigir(snap, tmp_path, capsys):
    dados, pub = snap
    man = _manifesto(pub)
    man["checksums"]["outro.json"] = "sha256:" + "2" * 64
    (pub / "manifest.json").write_text(json.dumps(man))
    assert _script().main([str(dados), "--aplicar", "--corrigir-manifesto", "--copias", str(tmp_path / "orig")]) == 2
    assert _manifesto(pub)["checksums"]["outro.json"] == "sha256:" + "2" * 64
    assert "divergente: outro.json" in capsys.readouterr().out
