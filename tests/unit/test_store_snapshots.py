# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`Store.list_snapshots` guardada em memória: um `stat` de `published/` por chamada, sem perder data nova, removida ou em publicação."""
import shutil
from pathlib import Path

from api.store import Store


def _publicar(base: Path, data: str, manifesto: bool = True) -> Path:
    d = base / "published" / data
    d.mkdir(parents=True, exist_ok=True)
    if manifesto:
        (d / "manifest.json").write_text("{}")
    return d


def test_lista_ordenada_e_so_com_manifesto(tmp_path):
    _publicar(tmp_path, "2026-11-15")
    _publicar(tmp_path, "2026-11-08")
    _publicar(tmp_path, "2026-11-22", manifesto=False)
    assert Store(tmp_path).list_snapshots() == ["2026-11-08", "2026-11-15"]


def test_sem_published(tmp_path):
    assert Store(tmp_path).list_snapshots() == []


def test_segunda_chamada_nao_lista_o_diretorio(tmp_path, monkeypatch):
    _publicar(tmp_path, "2026-11-08")
    _publicar(tmp_path, "2026-11-15")
    s = Store(tmp_path)
    assert s.list_snapshots() == ["2026-11-08", "2026-11-15"]
    chamadas = []
    original = Path.iterdir
    monkeypatch.setattr(Path, "iterdir", lambda self: chamadas.append(self) or original(self))
    for _ in range(50):
        assert s.list_snapshots() == ["2026-11-08", "2026-11-15"]
    assert chamadas == []


def test_data_nova_e_removida_aparecem(tmp_path):
    _publicar(tmp_path, "2026-11-08")
    s = Store(tmp_path)
    assert s.list_snapshots() == ["2026-11-08"]
    _publicar(tmp_path, "2026-11-15")
    assert s.list_snapshots() == ["2026-11-08", "2026-11-15"]
    shutil.rmtree(tmp_path / "published" / "2026-11-08")
    assert s.list_snapshots() == ["2026-11-15"]


def test_publicacao_em_andamento_aparece_quando_ganha_o_manifesto(tmp_path):
    """O diretório nasce antes do manifesto (que é gravado dentro dele e não muda `published/`): a data entra assim que ele existe."""
    _publicar(tmp_path, "2026-11-08")
    d = _publicar(tmp_path, "2026-11-15", manifesto=False)
    s = Store(tmp_path)
    assert s.list_snapshots() == ["2026-11-08"]
    (d / "manifest.json").write_text("{}")
    assert s.list_snapshots() == ["2026-11-08", "2026-11-15"]


def test_devolve_copia(tmp_path):
    _publicar(tmp_path, "2026-11-15")
    s = Store(tmp_path)
    s.list_snapshots().append("x")
    assert s.list_snapshots() == ["2026-11-15"]
