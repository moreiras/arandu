# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""O aquecimento dos perfis (api/cache.py) pede exatamente o que a interface pede: mesma rota, mesmos blocos, `opcional` igual.
Se a página mudar a lista de `include` e o aquecimento não, o primeiro visitante volta a pagar o cálculo a frio."""
import re
from pathlib import Path

from api.cache import PERFIS_DA_INTERFACE, url_do_perfil

FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "services" / "api.ts"


def _chamadas_do_front() -> dict:
    texto = FRONT.read_text(encoding="utf-8")
    achadas = {}
    # o bloco de histórico entra como `${blocoHistorico(...)}`: o aquecimento grava a versão de todos (`historico`, as datas atuais)
    for m in re.finditer(r"get\(`(/api/v1/(?:ixps|asns|operadoras|municipios|ufs))/\$\{\w+\}`,\s*\{(.*)\}\)$", texto, re.M):
        rota, params = m.group(1), m.group(2)
        inc = re.search(r"include:\s*[`']([^`']+)[`']", params)
        if inc:
            blocos = re.sub(r"\$\{blocoHistorico\([^)]*\)\}", "historico", inc.group(1))
            achadas.setdefault(rota, []).append((blocos, "opcional: true" in params))
    return achadas


def test_listas_de_blocos_iguais_as_da_interface():
    front = _chamadas_do_front()
    for tipo, (rota, blocos, opcional) in PERFIS_DA_INTERFACE.items():
        base = rota.replace("/{id}", "")
        assert (blocos, opcional) in front.get(base, []), f"{tipo}: a interface não pede {base} com include={blocos} (opcional={opcional})"


def test_url_igual_a_do_navegador():
    assert url_do_perfil("operadora", "123", "2026-11-13") == (
        "/api/v1/operadoras/123?date=2026-11-13&include=historico%2Cindicadores%2Cerbs%2Cmultas%2Cprontidao%2Cqualidade%2C"
        "reclamacoes%2Cconsumidor%2Cmercado_grupos&opcional=true")
