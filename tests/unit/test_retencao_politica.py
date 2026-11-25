# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — a tabela de retenção da política (`frontend/src/lib/retencao.gen.json`) bate com as constantes do código.

Compara a TABELA gerada com o código, não o texto de `Privacidade.tsx` (redação do mantenedor, aprovada em PT-13b).
"""
import importlib.util
import json
import re
from pathlib import Path

from api import limites, usage_log, uso_conta
from api.auth import contas, storage
from mcp_server import chave

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gen_retencao", ROOT / "scripts" / "gen_retencao.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _tabela() -> dict:
    return {l["id"]: l for l in json.loads(gen.SAIDA.read_text(encoding="utf-8"))["linhas"]}


def test_json_em_dia():
    assert gen.SAIDA.read_text(encoding="utf-8") == gen.texto(), "retencao.gen.json desatualizado: rode `python3 scripts/gen_retencao.py`"


def test_prazos_batem_com_as_constantes():
    t = _tabela()
    assert t["registro_conta_detalhe"]["valor"] == {"dias": uso_conta.RETENCAO_DETALHE_DIAS}
    assert t["registro_conta_agregado"]["valor"] == {"dias": uso_conta.RETENCAO_AGREGADO_DIAS}
    assert t["registro_anonimo"]["valor"] == {"dias": usage_log.retention_days()}
    assert t["log_acesso_conta"]["valor"] == {"meses": storage.RETENCAO_LOG_MESES}
    assert t["exclusao_conta"]["valor"] == {"dias": contas.PRAZO_EXCLUSAO_DIAS}
    for i in ("registro_conta_detalhe", "registro_conta_agregado", "registro_anonimo", "log_acesso_conta", "exclusao_conta"):
        n = list(t[i]["valor"].values())[0]
        assert str(n) in t[i]["prazo"], i


def test_tetos_do_mcp_batem_com_limites_e_cota():
    v = _tabela()["tetos_mcp"]["valor"]
    assert v["anonimo"] == {"minuto": 60, "hora": 1000, "dia": 5000} and limites.PADROES["mcp"]["anon"] == "60/minute;1000/hour;5000/day"
    assert v["conta"] == {"minuto": 60, "hora": 400} and limites.PADROES["mcp"]["conta"] == "60/minute;400/hour"
    assert v["conta_cota_diaria"] == chave.COTA_DIARIA_PADRAO


def test_servidor_web_tem_prazo_indeterminado_sem_numeros_de_rotacao():
    l = _tabela()["log_servidor_web"]
    assert l["prazo"] == "tempo indeterminado" and l["contem_ip"] is True
    assert not re.search(r"\d", l["prazo"]) and "rotação" not in l["prazo"]
    assert "$remote_addr" in (ROOT / "docker" / "nginx-frontend.conf").read_text(encoding="utf-8")


def test_toda_chave_de_localstorage_do_front_esta_na_tabela():
    """Uma chave nova de localStorage no front tem de entrar na tabela (e na política)."""
    usam = sorted(
        str(p.relative_to(ROOT))
        for p in (ROOT / "frontend" / "src").rglob("*.ts*")
        if ".test." not in p.name and p.name != "Privacidade.tsx" and "localStorage" in p.read_text(encoding="utf-8")
    )
    assert usam == sorted(gen._CHAVES_LOCALSTORAGE), "arquivo novo usa localStorage: acrescente em scripts/gen_retencao.py e regere o JSON"
    for arq, rx in gen._CHAVES_LOCALSTORAGE.items():
        assert re.search(rx, (ROOT / arq).read_text(encoding="utf-8")).group(1) in _tabela()["local_storage"]["valor"]["chaves"]

