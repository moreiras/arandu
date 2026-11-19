# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — o orçamento de requisições/bytes por página (baseline do smoke.js) está completo e sensato."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGINAS = {"ases", "asn", "bgp", "cdncap", "communities", "comparar_asn", "dados", "dashboard", "estados", "estatisticas", "explorar", "fontes", "grupo", "home", "mapa", "mercado_ipv4", "mudancas", "municipio", "municipios", "operadora", "operadoras_ranking", "panorama_mercado_concentracao", "panorama_mercado_maiores", "panorama_tecnico_ipv6", "prefixo", "ptt", "qualidade", "rankings", "regulatorio", "relatorio_asn", "seguranca_roteamento", "uf", "uso_da_internet"}


def test_baseline_cobre_as_paginas_da_fumaca_sem_erro_5xx():
    b = json.loads((ROOT / "tests" / "contracts" / "page_budget.json").read_text())["paginas"]
    assert set(b) == PAGINAS
    for nome, m in b.items():
        assert m["chamadas"] > 0 and m["api"] > 0 and m["bytes"] > 0, nome
        assert m["erros_5xx"] == 0 and m["erros_pagina"] == 0 and m["mostra_erro_na_tela"] is False, nome


def test_smoke_js_le_o_mesmo_arquivo_que_o_run_sh_monta():
    run = (ROOT / "tests" / "e2e" / "run.sh").read_text()
    smoke = (ROOT / "tests" / "e2e" / "smoke.js").read_text()
    assert "/contracts" in run and "/contracts/page_budget.json" in smoke
