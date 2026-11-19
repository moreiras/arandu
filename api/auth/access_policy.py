# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Política de acesso: classifica cada rota da API em open | metered | login.

Fonte ÚNICA da classificação, consumida pelo gate do nginx (`GET /auth/gate`), pelo
middleware da API e pelos testes (`tests/test_access_policy.py` exige que TODA rota
de `/api/v1` esteja aqui — rota nova sem classe explícita falha o teste).

Classes (quem vale: anônimo fora da allowlist e sem login):
  open     — sempre liberada (páginas de entrada: vitrine do projeto);
  metered  — liberada enquanto houver orçamento de uso ativo em páginas avançadas;
  login    — exige login (expandir listas, histórico, contatos).

Rota não listada cai em `metered` (padrão conservador, nunca `open`).
O middleware da API e o gate do nginx (`api/gate_app.py`) leem esta mesma tabela; o espelho do
frontend fica em `frontend/src/auth/accessPolicy.ts`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

OPEN = "open"
METERED = "metered"
LOGIN = "login"

# Prévia de lista para anônimo: 1ª página, até este nº de linhas.
PREVIEW_LIMIT = 100

_API = "/api/v1"


@dataclass(frozen=True)
class Classification:
    cls: str
    reason: str


# ── Rotas abertas (GET): o que as páginas de ENTRADA precisam para abrir ─────
# Levantado a partir dos fetch* de Dashboard, IXPs, ASes, SCMs/SMPs/STFCs/SEACs,
# Grupos e Sobre (+ layout: busca, seletor de snapshot). O teste
# `test_entry_pages_use_only_open_endpoints` trava essa lista.
_OPEN_PATTERNS: Sequence[str] = (
    r"/busca",                        # busca universal da barra (toda página); índice só com PJ e recursos de rede
    r"/brasil/indicadores",           # agregados do país na home (página de entrada)
    r"/snapshots",
    r"/snapshots/[^/]+",
    r"/feed/mudancas\.atom",          # só confirmados e só as datas atuais, então não abre a série antiga
    r"/ixps",
    r"/ixps/estimated-users",
    r"/ixps/[^/]+/hilbert/v4/detail",
    r"/external-ixps",
    r"/asns/ix-presence",
    r"/hilbert/v4",
    r"/hilbert/v4/detail",
    r"/hilbert/v6",
    r"/bgp-stability/summary",
    r"/outorgas/stats",   # contrato unificado das outorgas (mesma classe das rotas por serviço)
    r"/outorgas/map",
    r"/scms/stats",
    r"/smps/stats",
    r"/stfcs/stats",
    r"/seacs/stats",
    r"/acessos/stats",
    r"/acessos-movel/stats",
    r"/map/asns-overview",
    r"/map/layers",   # hashes das camadas estáticas; pedido por toda página no boot
    r"/map/scms",
    r"/map/smps",
    r"/map/stfcs",
    r"/map/seacs",
    r"/acessos/municipios",
    r"/acessos/municipio/[^/]+",
    r"/ufs",   # resumo das 27 UFs: a página /estados é de entrada; o perfil /ufs/{uf} é avançado (metered)
    r"/municipios/[^/]+",   # perfil do município: mesma classe das rotas de acessos que ele consolida
    r"/acessos-movel/municipios",
    r"/acessos-movel/municipio/[^/]+",
    r"/acessos-movel/operadoras",
    r"/grupos",
    r"/grupos/[^/]+/prefixos-geo",
    r"/schema",
)

# ── Listas paginadas: 1ª página (≤ PREVIEW_LIMIT) aberta; além disso, login ──
_PAGED_PATTERNS: Sequence[str] = (r"/asns", r"/scms", r"/smps", r"/stfcs", r"/seacs", r"/outorgas")

# Listas de alto valor em páginas avançadas: a prévia continua `metered` (a página
# é medida); só ampliar (limit/page acima da prévia) exige login.
_PAGED_METERED_PATTERNS: Sequence[str] = (r"/acessos/divergencias", r"/acessos/divergencias/scm", r"/ranking/operadoras", r"/ranking/municipios", r"/omissao-sici", r"/territorio/ranking", r"/seguranca/resumo", r"/ranking/route-servers", r"/communities", r"/ixps/[^/]+/rejeicoes", r"/ipv4/transferencias", r"/ipv4/espaco", r"/ipv4/uso-por-terceiros", r"/multas/empresas", r"/espectro/faixas", r"/satelites/direitos", r"/prontidao/asns", r"/reclamacoes/marcas", r"/consumidor/marcas", r"/facilities")

# ── Login: contatos e o que é de alto valor ──────────────────────────────────
_LOGIN_PATTERNS: Sequence[str] = (r"/.*/contacts",)

# Rotas que não carregam snapshot (não se aplica a regra de histórico).
_NO_HISTORY_PATTERNS: Sequence[str] = (r"/snapshots", r"/schema")


def _compile(patterns: Sequence[str]) -> list[re.Pattern]:
    return [re.compile(rf"^{p}$") for p in patterns]


_OPEN = _compile(_OPEN_PATTERNS)
_PAGED = _compile(_PAGED_PATTERNS)
_PAGED_METERED = _compile(_PAGED_METERED_PATTERNS)
_LOGIN = _compile(_LOGIN_PATTERNS)
_NO_HISTORY = _compile(_NO_HISTORY_PATTERNS)
_HISTORICO = _compile((r"/history/.+", r"/changes", r"/changes/summary", r"/snapshots/diff"))


def _matches(patterns: Sequence[re.Pattern], path: str) -> bool:
    return any(p.match(path) for p in patterns)


_INTEIRO = re.compile(r"^[0-9]{1,9}$")


def _int(value: Optional[str], default: int) -> Optional[int]:
    """Inteiro decimal puro; `None` para qualquer outra forma (`1000.0`, `1e3`, ` 1`, `-1`, vazio), que a classificação trata como `login`.

    O FastAPI aceita `limit=1000.0` como 1000; um `int()` direto recusaria e cairia no padrão (prévia aberta).
    Falhar fechado: o que a política não entende não pode valer menos do que o servidor entrega."""
    if value is None:
        return default
    return int(value) if _INTEIRO.match(value) else None


def classify(
    method: str,
    path: str,
    query: Mapping[str, str],
    recent_dates: Optional[Sequence[str]] = None,
) -> Classification:
    """Classe da requisição `method path?query` para um anônimo.

    `recent_dates`: snapshots tratados como "atuais" (o mais recente e o anterior,
    para o cliente que ainda tem o `latest` antigo em cache). Datas fora disso são
    histórico → `login`. `None` = desconhecido: a regra de histórico não se aplica.
    """
    if not path.startswith(_API + "/"):
        return Classification(OPEN, "fora-da-api")
    rel = path[len(_API):]
    # `/acessos/*?servico=movel` é a mesma coisa que `/acessos-movel/*`: mesma classe de acesso
    if rel.startswith("/acessos/") and query.get("servico") == "movel":
        rel = "/acessos-movel/" + rel[len("/acessos/"):]

    if _matches(_LOGIN, rel):
        return Classification(LOGIN, "contatos")

    # Histórico (séries e eventos): a consulta precisa começar num snapshot atual; sem `from` ou com `from` mais antigo é a
    # série inteira, que exige login. `/snapshots/diff` compara duas datas, ambas atuais. Antes da regra de `/snapshots/{data}`, que o capturaria.
    if _matches(_HISTORICO, rel):
        if recent_dates:
            pedidas = [query.get("a"), query.get("b")] if rel == "/snapshots/diff" else [query.get("from")]
            if rel == "/snapshots/diff":
                fora = any(d not in recent_dates for d in pedidas)
            else:
                fora = not pedidas[0] or pedidas[0] < min(recent_dates)
            if fora:
                return Classification(LOGIN, "historico")
        return Classification(METERED, "historico-recente")

    # Histórico: snapshot que não é um dos atuais.
    if recent_dates:
        date: Optional[str] = None
        if rel.startswith("/snapshots/"):
            date = rel.rsplit("/", 1)[-1]
        elif not _matches(_NO_HISTORY, rel):
            date = query.get("date")
        if date and date not in recent_dates:
            return Classification(LOGIN, "historico")

    # Lote de ASNs: `GET /asns?asns=…` devolve documentos completos, que em `/asns/{asn}` são avançados.
    # Sem isto a prévia aberta da lista serviria 100 documentos por pedido a quem não tem orçamento.
    if rel == "/asns" and query.get("asns"):
        return Classification(METERED, "avancada")

    paged_open = _matches(_PAGED, rel)
    if paged_open or _matches(_PAGED_METERED, rel):
        page = _int(query.get("page"), 1)
        limit = _int(query.get("limit"), PREVIEW_LIMIT)
        if page is None or limit is None or page > 1 or limit > PREVIEW_LIMIT:
            return Classification(LOGIN, "lista-expandida")
        if paged_open:
            return Classification(OPEN, "lista-previa")
        return Classification(METERED, "avancada")

    if method.upper() == "GET" and _matches(_OPEN, rel):
        return Classification(OPEN, "entrada")

    return Classification(METERED, "avancada")
