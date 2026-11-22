# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — trilha contínua (`arandu continuo`): as coletas em rodízio diário saem do pipeline, que só as restaura do armazém."""
import json
from pathlib import Path

import pytest

from arandu import executor
from arandu.lockfile import lock
from arandu.runner import FakeRunner
from core.catalog.loader import load_catalog, ordem_de_execucao

ROOT = Path(__file__).resolve().parents[2]
CONTINUAS = ["ixbr_alice", "ixbr_alice_rotas", "rdap_contatos"]


@pytest.fixture(autouse=True)
def _sem_bloqueio_por_disco(monkeypatch):
    monkeypatch.setenv("ARANDU_BLOQUEIO_DISCO_PCT", "101")


@pytest.fixture(scope="module")
def cat():
    return load_catalog(ROOT / "catalog")


def _roda(cat, base, runner=None, **kw):
    runner = runner or FakeRunner()
    rel = executor.executar(cat, "2026-11-22", base, runner, log=lambda *_: None, versao="t", sleep=lambda s: None, **kw)
    return rel, runner


def test_catalogo_marca_as_coletas_continuas(cat):
    assert sorted(s.id for s in cat.steps.values() if s.continua) == sorted(CONTINUAS)


def test_pipeline_nao_coleta_as_continuas_e_restaura_do_armazem(cat, tmp_path, monkeypatch):
    restauradas = []

    def falso_reutilizar(cat_, step, data_dir, date):
        restauradas.append(step.id)
        return [{"fonte": step.id, "versao": "v1", "as_of": "2026-11-21T22:00:00Z"}] if step.id != "rdap_contatos" else []

    monkeypatch.setattr(executor, "reutilizar_versao", falso_reutilizar)
    rel, runner = _roda(cat, tmp_path, due=False)
    st = {e.id: e for e in rel.etapas}
    assert not set(CONTINUAS) & set(runner.chamadas)
    assert set(CONTINUAS) <= set(restauradas)
    assert st["ixbr_alice"].status == executor.PULADA and "versão do armazém de 2026-11-21" in st["ixbr_alice"].motivo
    assert st["ixbr_alice"].reutilizadas[0]["versao"] == "v1"
    assert "nenhuma versão no armazém" in st["rdap_contatos"].motivo
    # quem depende delas segue rodando no pipeline, sobre a versão restaurada
    assert "rs_policy" in runner.chamadas


def test_pipeline_com_only_ainda_roda_a_continua(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, only=["ixbr_alice"], usar_lock=False)
    assert runner.chamadas == ["ixbr_alice"]


def test_trilha_continua_roda_so_as_continuas_na_ordem_com_relatorio_proprio(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, continuo=True)
    ordem = [x for x in ordem_de_execucao(cat) if x in CONTINUAS]
    assert runner.chamadas == ordem
    assert [e.id for e in rel.etapas] == ordem and all(e.status == executor.OK for e in rel.etapas)
    assert executor.caminho_relatorio(tmp_path, "2026-11-22", continuo=True).is_file()
    assert not executor.caminho_relatorio(tmp_path, "2026-11-22").exists()       # não se mistura à retomada do pipeline
    hist = list((tmp_path / "ops" / "runs" / "continuo" / "history").glob("2026-11-22T*.json"))
    assert len(hist) == 1


def test_trilha_continua_e_pipeline_tem_locks_separados(cat, tmp_path):
    with lock(executor.caminho_lock(tmp_path)):                  # pipeline em andamento
        rel, runner = _roda(cat, tmp_path, continuo=True)
    assert runner.chamadas
    with lock(executor.caminho_lock(tmp_path, continuo=True)):   # outra instância da trilha contínua
        with pytest.raises(executor.LockOcupado):
            _roda(cat, tmp_path, continuo=True)


def test_trilha_continua_com_only_e_falha_opcional_segue(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, continuo=True, only=["ixbr_alice", "rdap_contatos"])
    assert runner.chamadas == ["ixbr_alice", "rdap_contatos"]
    rel, runner = _roda(cat, tmp_path, FakeRunner({"ixbr_alice": 1}), continuo=True)
    st = {e.id: e.status for e in rel.etapas}
    assert st["ixbr_alice"] == executor.FALHA and st["rdap_contatos"] == executor.OK
    gravado = json.loads(executor.caminho_relatorio(tmp_path, "2026-11-22", continuo=True).read_text())
    assert gravado["avisos"] == ["ixbr_alice"]


def test_cli_continuo(cat, tmp_path, monkeypatch, capsys):
    from arandu import cli

    chamadas = []
    monkeypatch.setattr(cli, "SubprocessRunner", lambda *a, **k: FakeRunner(antes=lambda s, d: chamadas.append(s.id)))
    rc = cli.main(["continuo", "--date", "2026-11-22", "--data-dir", str(tmp_path)])
    assert rc == 0 and sorted(chamadas) == sorted(CONTINUAS)
    assert "arandu continuo 2026-11-22: ok" in capsys.readouterr().out
