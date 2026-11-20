# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Pré-carga do MCP: percorre, numa thread de fundo, as tools da data mais recente como um cliente as pediria, para que a primeira
chamada de cada uma não pague a leitura dos arquivos (as mais lentas a frio levavam de 5 a 20 s: mapas de prefixos por PTT, potencial e
assinantes do PTT, usuários por PTT; medido num ambiente de teste em 2026-11-18).

Custo: o MCP fica com a data mais recente inteira em memória desde a subida (~3,1 GiB no snapshot de 2026-11-13, em ~5,5 min de CPU).
Ganho além da velocidade: o pico vem logo na subida, e um teto de contêiner pequeno demais aparece no deploy, não no meio de uma sessão.

Roda ao subir e de novo a cada snapshot publicado (o pipeline publica todo dia; sem isso a data nova ficaria fria até o próximo restart):
a thread confere `resolve_date(None)` a cada `MCP_PRECARGA_INTERVALO_S` (300). Entre uma chamada e outra dorme `MCP_PRECARGA_PAUSA_S`
(0,02): o MCP é um processo só, e sem pausa a thread seguraria o GIL a ponto de o laço de eventos não responder ao healthcheck.

`MCP_PRECARGA=0` desliga. As funções chamadas são as originais das tools, guardadas antes da prévia e do log de uso: a pré-carga não
gasta orçamento de ninguém nem aparece no log de uso.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Iterable, Optional

_log = logging.getLogger("arandurape")

UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()

# tools sem argumento obrigatório que leem o snapshot (as de histórico leem várias datas e ficam de fora)
SEM_ARGUMENTO = ("asn_lista", "ixp_lista", "facility_lista", "cdn_presenca", "rota_prefixos", "rota_analise", "rota_estabilidade",
                 "operadora_ranking", "operadora_divergencia", "uf_detalhe", "outorga_lista", "ixp_usuarios", "ixp_externo",
                 "ixp_communities", "rota_rpki", "describe_schema")
POR_PTT = ("ixp_detalhe", "ixp_assinantes", "ixp_potencial", "ixp_proximos", "ixp_usuarios")
CAMADAS_PTT = ("asns_members", "asns_direct", "asns_origin", "prefixes_v4", "prefixes_v6")


def ligada() -> bool:
    return os.environ.get("MCP_PRECARGA", "1") != "0"


def _env_s(nome: str, padrao: float) -> float:
    try:
        return max(float(os.environ.get(nome, padrao)), 0.0)
    except ValueError:
        return padrao


def chamadas(data: str, ptts: Iterable[str]) -> list[tuple[str, dict]]:
    """A lista de chamadas, na ordem: o que é global primeiro, depois cada PTT e cada UF."""
    out: list[tuple[str, dict]] = [(n, {} if n == "describe_schema" else {"date": data}) for n in SEM_ARGUMENTO]
    out += [("viz", {"kind": k, "date": data}) for k in ("hilbert_v4", "hilbert_v6", "map_pix")]
    for code in ptts:
        out += [(n, {"code": code, "date": data}) for n in POR_PTT]
        out += [("ixp_participantes", {"code": code, "visao": v, "afi": a, "date": data}) for v in ("membros", "peers") for a in ("v4", "v6")]
        out += [("viz", {"kind": "ixp_geo", "layer": c, "code": code, "date": data}) for c in CAMADAS_PTT]
        out += [("viz", {"kind": k, "code": code, "date": data}) for k in ("ixp_hilbert_v4", "ixp_hilbert_v6")]
    for uf in UFS:
        out += [("uf_detalhe", {"uf": uf, "date": data}), ("uf_radar", {"uf": uf, "date": data})]
        out += [("viz", {"kind": k, "uf": uf, "date": data}) for k in ("map_asns", "map_prefixes")]
    return out


def precarregar(funcoes: dict[str, Callable[..., Any]], store: Any, *, data: Optional[str] = None) -> dict[str, Any]:
    """Roda as chamadas e devolve um resumo. Erro de uma tool (PTT sem portas, sem PIX geolocalizado…) não interrompe as outras."""
    t0 = time.perf_counter()
    data = data or store.resolve_date(None)
    if not data:
        return {"data": None}
    try:
        ptts = [i.get("code") for i in (store.ixp_index(data) or []) if i.get("code")]
    except Exception:  # noqa: BLE001
        ptts = []
    feitas = falhas = 0
    pausa = _env_s("MCP_PRECARGA_PAUSA_S", 0.02)
    for nome, args in chamadas(data, ptts):
        fn = funcoes.get(nome)
        if fn is None:
            continue
        if pausa:
            time.sleep(pausa)                      # solta o GIL: o laço de eventos (healthcheck, clientes) segue respondendo
        try:
            fn(**args)
            feitas += 1
        except Exception:  # noqa: BLE001 — a pré-carga nunca derruba o MCP
            falhas += 1
    resumo = {"data": data, "ptts": len(ptts), "chamadas": feitas, "falhas": falhas, "segundos": round(time.perf_counter() - t0, 1)}
    _log.info("pré-carga do MCP: %s", resumo)
    return resumo


def acompanhar(funcoes: dict[str, Callable[..., Any]], store: Any, *, intervalo: Optional[float] = None,
               parar: Optional[threading.Event] = None) -> None:
    """Pré-carrega a data mais recente e, enquanto ligada, repete a cada snapshot novo. `parar` encerra (testes)."""
    intervalo = _env_s("MCP_PRECARGA_INTERVALO_S", 300) if intervalo is None else intervalo
    parar = parar or threading.Event()
    feita: Optional[str] = None
    while ligada() and not parar.is_set():
        try:
            data = store.resolve_date(None)
        except Exception:  # noqa: BLE001
            data = None
        if data and data != feita:
            precarregar(funcoes, store, data=data)
            feita = data
        parar.wait(intervalo)


def iniciar(funcoes: dict[str, Callable[..., Any]], store: Any) -> Optional[threading.Thread]:
    if not ligada():
        return None
    t = threading.Thread(target=acompanhar, args=(funcoes, store), name="precarga-mcp", daemon=True)
    t.start()
    return t
