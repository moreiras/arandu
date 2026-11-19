# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — recomputação dos alertas de um snapshot antigo: área separada, reproduzível, sem tocar no publicado."""
import hashlib
import json
from pathlib import Path

import pytest

from arandu import cli
from products.alerts import recompute, registro
from tests.unit.test_alerts_regras import FakeStore, _doc

D = "2026-09-20"


class _Log:
    def info(self, *a, **k): pass


def _publicar(base, docs):
    pub = base / "published" / D / "asns"
    pub.mkdir(parents=True)
    for d in docs:
        (pub / f"{d['asn']}.json").write_text(json.dumps(d), encoding="utf-8")
    (base / "published" / D / "manifest.json").write_text(json.dumps({"snapshot_date": D}), encoding="utf-8")


def _hash_publicado(base):
    h = hashlib.sha256()
    for p in sorted((base / "published").rglob("*")):
        if p.is_file():
            h.update(str(p).encode() + p.read_bytes())
    return h.hexdigest()


DOCS = [
    {**_doc(rir_prefixes_v6=[], global_prefixes_v6=[]), "asn": 64500, "is_br": True, "alerts": [{"id": "velho"}]},   # alerta antigo é ignorado
    {**_doc(single_upstream_v4=1), "asn": 64501, "is_br": True},
    {**_doc(), "asn": 64999, "is_br": False},                                                                          # não-BR não tem alertas
]


def test_recompute_grava_em_area_separada_com_meta_e_nao_toca_no_publicado(tmp_path):
    _publicar(tmp_path, DOCS)
    antes = _hash_publicado(tmp_path)
    meta = recompute.recomputar(tmp_path, D, _Log(), lambda b: FakeStore())
    assert _hash_publicado(tmp_path) == antes                                           # published/ intacto
    destino = recompute.diretorio(tmp_path, D)
    assert destino == tmp_path / "alerts" / registro.rules_version() / D and (destino / "alertas.jsonl.gz").is_file()
    assert meta["asns"] == 2 and meta["alertas"] >= 2 and meta["rules"] == registro.regras_publicadas()
    assert meta["rules_version_do_snapshot"] is None                                    # manifesto sem rules_version
    assert meta["por_id"]["sem_ipv6"] == 1 and meta["por_id"]["single_homed"] == 1
    por_asn = dict(recompute.ler_alertas(tmp_path, D))
    assert set(por_asn) == {64500, 64501} and "velho" not in {a["id"] for a in por_asn[64500]}


def test_recompute_e_reproduzivel(tmp_path):
    import time
    _publicar(tmp_path, DOCS)
    a = recompute.recomputar(tmp_path, D, _Log(), lambda b: FakeStore())
    bytes_a = (recompute.diretorio(tmp_path, D) / "alertas.jsonl.gz").read_bytes()
    time.sleep(1.1)
    b = recompute.recomputar(tmp_path, D, _Log(), lambda b: FakeStore())
    assert a["conteudo_sha256"] == b["conteudo_sha256"]
    assert (recompute.diretorio(tmp_path, D) / "alertas.jsonl.gz").read_bytes() == bytes_a     # gzip determinístico


def test_regras_diferentes_vao_para_outra_pasta(tmp_path, monkeypatch):
    from dataclasses import replace
    _publicar(tmp_path, DOCS)
    recompute.recomputar(tmp_path, D, _Log(), lambda b: FakeStore())
    v1 = registro.rules_version()
    alvo = registro.MODULOS[0]
    monkeypatch.setattr(alvo, "REGRA", replace(alvo.REGRA, versao=alvo.REGRA.versao + 1))
    monkeypatch.setattr(registro, "REGRAS", tuple(m.REGRA for m in registro.MODULOS))
    recompute.recomputar(tmp_path, D, _Log(), lambda b: FakeStore())
    v2 = registro.rules_version()
    assert v1 != v2 and (tmp_path / "alerts" / v1 / D).is_dir() and (tmp_path / "alerts" / v2 / D).is_dir()      # versões coexistem
    assert not registro.comparavel(v1, v2)


def test_sem_documentos_de_asn_falha_alto(tmp_path):
    with pytest.raises(FileNotFoundError):
        recompute.recomputar(tmp_path, D, _Log(), lambda b: FakeStore())


def test_cli_exige_recompute_e_roteia_o_produto_alerts(tmp_path, monkeypatch, capsys):
    _publicar(tmp_path, DOCS)
    assert cli.main(["build", "alerts", "--data-dir", str(tmp_path), "--date", D]) == 2             # sem --recompute: recusa
    import api.store as store_mod
    monkeypatch.setattr(store_mod, "Store", lambda base: FakeStore())
    assert cli.main(["build", "alerts", "--recompute", "--data-dir", str(tmp_path), "--date", D]) == 0
    assert "recalculados com as regras" in capsys.readouterr().out
