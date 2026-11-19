# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — a configuração de CI é coerente com o repositório (sem rodar o Actions)."""
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def workflow():
    return yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())


def test_jobs_e_python_igual_ao_da_imagem_de_producao():
    wf = workflow()
    assert set(wf["jobs"]) == {"python", "frontend", "e2e", "ipv6", "sbom", "sbom-imagens"}
    img = re.search(r"^FROM python:(\d+\.\d+)", (ROOT / "Dockerfile.api").read_text(), re.M).group(1)
    py = [s for s in wf["jobs"]["python"]["steps"] if "setup-python" in str(s.get("uses"))][0]
    assert str(py["with"]["python-version"]) == img
    runs = " ".join(str(s.get("run", "")) for s in wf["jobs"]["python"]["steps"])
    assert "scripts/ci.sh" in runs and "--require-hashes -r requirements-dev.lock" in runs


def test_e2e_so_noturno_ou_manual_e_usa_o_publicado_sintetico():
    wf = workflow()
    assert "schedule" in wf[True] and "workflow_dispatch" in wf[True]      # `on:` vira True no YAML 1.1
    e2e = wf["jobs"]["e2e"]
    assert "schedule" in e2e["if"]
    runs = " ".join(str(s.get("run", "")) for s in e2e["steps"])
    assert "tests.synth.publish" in runs and "tests/e2e/run.sh" in runs
    n = int(re.search(r"--extra-asns (\d+)", runs).group(1))
    assert n > 1000, "a lista logada pagina de 1000 em 1000 (ASes.tsx): o E2E precisa de mais que isso"


def test_scripts_do_ci_existem_e_tem_sintaxe_valida():
    for f in ("scripts/ci.sh", "scripts/post-deploy-check.sh"):
        assert subprocess.run(["bash", "-n", f], cwd=ROOT).returncode == 0
    assert subprocess.run(["bash", "scripts/ci.sh", "--bobagem"], cwd=ROOT, capture_output=True).returncode == 2


def test_dataset_em_escala_nao_altera_o_mundo_base():
    from tests.synth.world import build_world

    base = build_world()
    w0 = build_world(extra_asns=0)
    assert base.ases == w0.ases and base.routes == w0.routes
    w = build_world(extra_asns=50)
    novos = [a for asn, a in w.ases.items() if asn >= 4200001000]
    assert len(novos) == 50 and all(a.is_br for a in novos)
    # o mundo-base segue igual: só se acrescenta
    assert all(w.ases[asn] == a for asn, a in base.ases.items())
    prefixos = [p for a in novos for p in a.v4]
    assert len(prefixos) == len(set(prefixos))


def test_ipv6_so_noturno_ou_manual_e_roda_o_t7():
    """T7 (tests/ipv6): laboratório Kathará, pesado demais para cada push."""
    job = workflow()["jobs"]["ipv6"]
    assert "schedule" in job["if"] and "workflow_dispatch" in job["if"]
    runs = " ".join(str(s.get("run", "")) for s in job["steps"])
    assert "tests/ipv6/run.sh" in runs and "tests/ipv6/requirements.txt" in runs


def test_sbom_em_todo_push_e_imagens_a_noite_ou_na_tag():
    """SBOM das dependências a cada push; o das imagens (pesado: constrói as duas) à noite, manual ou na tag de versão."""
    wf = workflow()
    assert "v*" in wf[True]["push"]["tags"]
    deps = wf["jobs"]["sbom"]
    assert "if" not in deps and "bash scripts/sbom.sh" in " ".join(str(s.get("run", "")) for s in deps["steps"])
    img = wf["jobs"]["sbom-imagens"]
    assert "schedule" in img["if"] and "refs/tags/v" in img["if"]
    runs = " ".join(str(s.get("run", "")) for s in img["steps"])
    assert "scripts/sbom.sh --imagens" in runs and "Dockerfile.api" in runs and "Dockerfile.frontend" in runs
    assert img["permissions"] == {"contents": "write"} and wf["permissions"] == {"contents": "read"}


def test_actions_fixadas_por_sha():
    usos = re.findall(r"uses:\s*(\S+)", (ROOT / ".github" / "workflows" / "ci.yml").read_text())
    assert usos and all(re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u) for u in usos), usos
