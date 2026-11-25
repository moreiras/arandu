# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rotas substituídas por contratos unificados: continuam respondendo e ganham `Deprecation` + `Link`.

`Deprecation: true` (RFC 9745) e `Link: <sucessor>; rel="successor-version"` avisam quem consome a API sem quebrar ninguém;
nada é removido (AGENTS §2, item 8). Esta tabela é a lista de aliases: o que está aqui conta como alias na medição de rotas.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import quote

_API = "/api/v1"

# (padrão do caminho depois de /api/v1, sucessor com {grupos} do padrão)
_ALIASES: list[tuple[re.Pattern, str]] = [(re.compile(rf"^{p}$"), s) for p, s in [
    # outorgas por serviço → /outorgas?servico=
    *[(rf"/{r}", f"/outorgas?servico={sv}") for r, sv in (("scms", "SCM"), ("smps", "SMP"), ("stfcs", "STFC"), ("seacs", "SeAC"))],
    *[(rf"/{r}/stats", f"/outorgas/stats?servico={sv}") for r, sv in (("scms", "SCM"), ("smps", "SMP"), ("stfcs", "STFC"), ("seacs", "SeAC"))],
    *[(rf"/map/{r}", f"/outorgas/map?servico={sv}") for r, sv in (("scms", "SCM"), ("smps", "SMP"), ("stfcs", "STFC"), ("seacs", "SeAC"))],
    *[(rf"/{r}/(?P<cnpj>\d+)", f"/outorgas/{{cnpj}}?servico={sv}") for r, sv in (("scms", "SCM"), ("smps", "SMP"), ("stfcs", "STFC"), ("seacs", "SeAC"))],
    # acessos móveis → /acessos?servico=movel
    (r"/acessos-movel/stats", "/acessos/stats?servico=movel"),
    (r"/acessos-movel/operadoras", "/acessos/operadoras?servico=movel"),
    (r"/acessos-movel/operadora/(?P<cnpj>[^/]+)", "/acessos/operadora/{cnpj}?servico=movel"),
    (r"/acessos-movel/operadora/(?P<cnpj>[^/]+)/contacts", "/acessos/operadora/{cnpj}/contacts?servico=movel"),
    (r"/acessos-movel/municipios", "/acessos/municipios?servico=movel"),
    (r"/acessos-movel/municipio/(?P<ibge>[^/]+)", "/acessos/municipio/{ibge}?servico=movel"),
    # PTT: o detalhamento por AS mora junto do PTT
    (r"/analytics/ixps/(?P<code>[^/]+)/nearby", "/ixps/{code}/nearby"),
    # D12: o vocabulário "omissão" saiu do produto; o nome antigo segue como alias
    (r"/omissao-sici", "/sem-declaracao-sici"),
    # mesmo CNPJ com vários ASNs não é grupo econômico (esse está em /grupos)
    (r"/asns/economic-groups", "/asns/by-organization"),
]]


def sucessor(path: str) -> Optional[str]:
    """Caminho (com /api/v1) que substitui `path`, ou None se a rota não está descontinuada."""
    if not path.startswith(_API + "/"):
        return None
    rel = path[len(_API):]
    for padrao, destino in _ALIASES:
        m = padrao.match(rel)
        if m:
            # cabeçalho HTTP só leva ASCII: o que veio do caminho é codificado (caminhos estranhos viram %XX, nunca 500)
            return _API + destino.format(**{k: quote(v, safe='') for k, v in m.groupdict().items()})
    return None


def cabecalhos(path: str) -> dict[str, str]:
    novo = sucessor(path)
    return {"Deprecation": "true", "Link": f'<{novo}>; rel="successor-version"'} if novo else {}
