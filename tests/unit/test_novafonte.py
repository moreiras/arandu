# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — `arandu source new`: uma fonte de CSV nova em 6 arquivos, sem editar nenhum arquivo existente."""
import shutil
from pathlib import Path

import pytest

from arandu import cli, executor, novafonte
from core.catalog.loader import load_catalog, validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def raiz(tmp_path):
    shutil.copytree(ROOT / "catalog", tmp_path / "catalog")
    return tmp_path


def test_gera_seis_arquivos_e_o_catalogo_continua_valido(raiz):
    criados = novafonte.criar("ptts_parceiros", "PTTs parceiros", "https://exemplo.invalid/ptts.csv", raiz)
    assert sorted(criados) == sorted([
        "catalog/sources/ptts_parceiros.yaml", "sources/ptts_parceiros/__init__.py", "sources/ptts_parceiros/collect.py",
        "tests/fixtures/raw/ptts_parceiros/amostra.csv", "tests/fixtures/raw/ptts_parceiros/README.md", "tests/sources/test_t1_ptts_parceiros.py"])
    cat = load_catalog(raiz / "catalog")
    assert validate(cat) == [], validate(cat)
    st = cat.steps["ptts_parceiros"]                                   # etapa descoberta da fonte, sem arquivo em catalog/steps/
    assert st.modulo == "sources.ptts_parceiros.collect" and st.fontes == ["ptts_parceiros"] and st.ordem < 0
    assert cat.sources["ptts_parceiros"].publicar.para == "ptts_parceiros.json.gz"
    # todo arquivo Python gerado compila e tem o cabeçalho SPDX
    for c in criados:
        if c.endswith(".py"):
            texto = (raiz / c).read_text(encoding="utf-8")
            compile(texto, c, "exec")
            assert texto.startswith("# SPDX-License-Identifier: AGPL-3.0-or-later")


def test_nao_sobrescreve_e_valida_o_id(raiz):
    novafonte.criar("fonte_a", "A", "https://x.invalid/a.csv", raiz)
    with pytest.raises(FileExistsError):
        novafonte.criar("fonte_a", "A", "https://x.invalid/a.csv", raiz)
    with pytest.raises(ValueError):
        novafonte.criar("Fonte-Ruim", "x", "https://x.invalid", raiz)
    assert novafonte.criar("fonte_b", "B", "https://x.invalid/b.csv", raiz, dry_run=True) and not (raiz / "sources" / "fonte_b").exists()


def test_cli_source_new(raiz, capsys):
    assert cli.main(["source", "new", "ptts_parceiros", "--raiz", str(raiz), "--url", "https://x.invalid/p.csv"]) == 0
    assert "Próximos passos" in capsys.readouterr().out
    assert cli.main(["source", "new", "ptts_parceiros", "--raiz", str(raiz)]) == 1                       # já existe


def test_publicar_copia_o_normalizado_para_o_publicado(raiz, tmp_path):
    novafonte.criar("ptts_parceiros", "PTTs", "https://x.invalid/p.csv", raiz)
    cat = load_catalog(raiz / "catalog")
    dados = tmp_path / "dados"
    d = "2026-10-24"
    assert executor.publicar_fontes(cat, cat.steps["ptts_parceiros"], dados, d) == (None, "ptts_parceiros: summary/ptts_parceiros.json.gz não foi gerado; nada a publicar")
    (dados / "normalized" / d / "summary").mkdir(parents=True)
    (dados / "normalized" / d / "summary" / "ptts_parceiros.json.gz").write_bytes(b"conteudo")
    arquivos, erro = executor.publicar_fontes(cat, cat.steps["ptts_parceiros"], dados, d, log=lambda *_: None)
    assert erro is None and arquivos == ["ptts_parceiros.json.gz"]
    assert (dados / "published" / d / "ptts_parceiros.json.gz").read_bytes() == b"conteudo"
