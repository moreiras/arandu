#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera `frontend/src/lib/retencao.gen.json`: a tabela de retenção da política de privacidade, derivada das constantes do código
(`api/uso_conta.py`, `api/usage_log.py`, `api/auth/storage.py`, `api/auth/contas.py`, `api/auth/anon_session.py`, `api/auth/jwt_utils.py`,
`api/limites.py`, `mcp_server/chave.py`).

Cada linha traz o valor numérico, o prazo em texto e a `fonte` (arquivo e constante). O texto de `prazo` é o aprovado pelo mantenedor (PT-13b) e é exibido na página
`/privacidade` (`EXIBIR_TABELA_RETENCAO` em `Privacidade.tsx`).
`tests/unit/test_retencao_politica.py` confere que o arquivo está em dia e que a tabela bate com as constantes.

    python3 scripts/gen_retencao.py          # regrava
    python3 scripts/gen_retencao.py --check  # só confere (código 1 se diferente)
    python3 scripts/gen_retencao.py --stdout # imprime o JSON sem gravar
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from limits import parse_many

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import limites, usage_log, uso_conta  # noqa: E402
from api.auth import anon_session, contas, jwt_utils, storage  # noqa: E402
from mcp_server import chave  # noqa: E402

SAIDA = ROOT / "frontend" / "src" / "lib" / "retencao.gen.json"
_JANELA = {"minute": "minuto", "hour": "hora", "day": "dia"}
_CHAVES_LOCALSTORAGE = {
    "frontend/src/lib/buscaRecentes.ts": r"CHAVE_RECENTES\s*=\s*'([^']+)'",
    "frontend/src/components/layout/LeituraConfortavel.tsx": r"const CHAVE\s*=\s*'([^']+)'",
    "frontend/src/lib/orientacaoMapa.ts": r"const CHAVE\s*=\s*'([^']+)'",
}


def _tetos(spec: str) -> dict[str, int]:
    """`"60/minute;400/hour"` → `{"minuto": 60, "hora": 400}` (mesma biblioteca que aplica o limite)."""
    return {_JANELA[i.GRANULARITY.name]: i.amount for i in parse_many(spec)}


def chaves_localstorage() -> list[str]:
    return sorted(re.search(rx, (ROOT / arq).read_text(encoding="utf-8")).group(1) for arq, rx in _CHAVES_LOCALSTORAGE.items())


def linhas() -> list[dict]:
    mcp = limites.PADROES["mcp"]
    return [
        {"id": "log_servidor_web", "registro": "Registro de acesso do servidor web", "contem_ip": True,
         "valor": {"prazo": "indeterminado"}, "prazo": "tempo indeterminado",
         "fonte": "docker/nginx-frontend.conf (log_format temporizado); docker-compose.prod.yml (serviço frontend, logging)"},
        {"id": "log_acesso_conta", "registro": "Registro de páginas visitadas por quem tem conta (identificador interno e IP)", "contem_ip": True,
         "valor": {"meses": storage.RETENCAO_LOG_MESES}, "prazo": f"{storage.RETENCAO_LOG_MESES} meses (o mês corrente conta como o primeiro)",
         "fonte": "api/auth/storage.py (RETENCAO_LOG_MESES, log_access)"},
        {"id": "registro_anonimo", "registro": "Registro anônimo de uso (identificador por hash que muda a cada dia)", "contem_ip": False,
         "valor": {"dias": usage_log.RETENCAO_PADRAO_DIAS}, "prazo": f"{usage_log.RETENCAO_PADRAO_DIAS} dias",
         "fonte": "api/usage_log.py (RETENCAO_PADRAO_DIAS; USAGE_LOG_RETENTION_DAYS altera)"},
        {"id": "registro_conta_detalhe", "registro": "Registro de uso associado à conta, detalhado", "contem_ip": False,
         "valor": {"dias": uso_conta.RETENCAO_DETALHE_DIAS}, "prazo": f"{uso_conta.RETENCAO_DETALHE_DIAS} dias",
         "fonte": "api/uso_conta.py (RETENCAO_DETALHE_DIAS)"},
        {"id": "registro_conta_agregado", "registro": "Contagens de uso por dia, conta, origem e classe de rota", "contem_ip": False,
         "valor": {"dias": uso_conta.RETENCAO_AGREGADO_DIAS},
         "prazo": f"{uso_conta.RETENCAO_AGREGADO_DIAS} dias (12 meses); o identificador da conta só é retirado das contagens na exclusão da conta",
         "fonte": "api/uso_conta.py (RETENCAO_AGREGADO_DIAS)"},
        {"id": "exclusao_conta", "registro": "Exclusão da conta", "contem_ip": False,
         "valor": {"dias": contas.PRAZO_EXCLUSAO_DIAS}, "prazo": f"{contas.PRAZO_EXCLUSAO_DIAS} dias após o pedido",
         "fonte": "api/auth/contas.py (PRAZO_EXCLUSAO_DIAS)"},
        {"id": "cookie_anon_sid", "registro": "Cookie de sessão sem login (anon_sid)", "contem_ip": False,
         "valor": {"horas": anon_session.TTL_PADRAO_HORAS}, "prazo": f"{anon_session.TTL_PADRAO_HORAS} horas",
         "fonte": "api/auth/anon_session.py (TTL_PADRAO_HORAS; ANON_SESSION_TTL_HOURS altera)"},
        {"id": "cookie_auth_token", "registro": "Cookie de sessão com login (auth_token)", "contem_ip": False,
         "valor": {"dias": jwt_utils._TTL_DAYS}, "prazo": f"{jwt_utils._TTL_DAYS} dias",
         "fonte": "api/auth/jwt_utils.py (_TTL_DAYS)"},
        {"id": "tetos_mcp", "registro": "Tetos de uso do MCP (contadores em memória, sem registro de IP)", "contem_ip": False,
         "valor": {"anonimo": _tetos(mcp["anon"]), "conta": _tetos(mcp["conta"]), "conta_cota_diaria": chave.COTA_DIARIA_PADRAO},
         "prazo": "por minuto, hora e dia (anônimo: %s; conta: %s e cota diária de %d chamadas)" % (
             ", ".join(f"{v}/{k}" for k, v in _tetos(mcp["anon"]).items()), ", ".join(f"{v}/{k}" for k, v in _tetos(mcp["conta"]).items()), chave.COTA_DIARIA_PADRAO),
         "fonte": "api/limites.py (PADROES['mcp']); mcp_server/chave.py (COTA_DIARIA_PADRAO, MCP_COTA_DIARIA altera)"},
        {"id": "local_storage", "registro": "Preferências guardadas no navegador (localStorage): leitura confortável, buscas recentes, orientação do mapa",
         "contem_ip": False, "valor": {"chaves": chaves_localstorage()},
         "prazo": "ficam no seu navegador até você limpá-las; nunca são enviadas ao servidor",
         "fonte": "frontend/src/lib/buscaRecentes.ts, frontend/src/components/layout/LeituraConfortavel.tsx, frontend/src/lib/orientacaoMapa.ts"},
    ]


def texto() -> str:
    return json.dumps({"gerado_por": "scripts/gen_retencao.py", "linhas": linhas()}, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str]) -> int:
    novo = texto()
    if "--stdout" in argv:
        sys.stdout.write(novo)
        return 0
    if "--check" in argv:
        if not SAIDA.exists() or SAIDA.read_text(encoding="utf-8") != novo:
            print(f"{SAIDA.relative_to(ROOT)} desatualizado: rode `python3 scripts/gen_retencao.py`", file=sys.stderr)
            return 1
        return 0
    SAIDA.write_text(novo, encoding="utf-8")
    print(f"gravado {SAIDA.relative_to(ROOT)} ({len(linhas())} linhas)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
