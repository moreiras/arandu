# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Route servers do DE-CIX Rio de Janeiro e São Paulo pela API do Alice-LG (níveis 0, 1 e 3).

Fonte:       https://lg.de-cix.net/api/v1/{status,routeservers,routeservers/{id}/neighbors,routeservers/{id}/neighbors/{id}/routes/received}
Normalizado: data/normalized/{date}/summary/decix_rs_sessions.json.gz   mesmo esquema do `rs_sessions` do IX.br (`rs`, `sessoes`), com `ixp` = decix-sp ou decix-rj
             data/normalized/{date}/summary/decix_rs_rotas.json.gz      nível 3: por vizinho, rotas lidas, total e contagem de rotas por ASN de origem
Bruto:       não é guardado (derivados apenas): páginas de rotas de 250 prefixos não ficam em disco; só a contagem por origem.

Autorização e condições: o `robots.txt` do lg.de-cix.net é `Disallow: /`; o mantenedor liberou este host (a página do serviço diz "You can use the API in your
own scripts"), exceção à regra do robots.txt só para ele (registrada no catálogo). Condições cumpridas aqui: User-Agent identificado, uma requisição por vez, no mínimo 1 s entre requisições
(`core.rodizio.Limitador`), orçamento de requisições por rodada, e **parada no primeiro sinal de bloqueio** (HTTP 403 ou 429; conexão derrubada só na 2ª vez seguida, depois de 1 repetição a 60 s): a rodada para na hora, o
bloqueio é registrado nos documentos (`bloqueio`) e a execução falha alto; nas rodadas seguintes a coleta nem tenta por `BLOQUEIO_PAUSA_DIAS` dias (só `--ignorar-bloqueio`, depois de o
mantenedor avaliar). Escopo: route servers `rs1/rs2_rio_*` e `rs1/rs2_sao_*` (IPv4 e IPv6); o resto do DE-CIX nunca é consultado.

O Alice do DE-CIX difere do IX.br: o id do route server leva o sufixo `_de-cix` (`rs1_rio_ipv4_de-cix`), o id do vizinho é o `id` da própria resposta do `neighbors`
(`R93_12`, não `AS{asn}_{ip}`) e não há `config` útil (as communities do DE-CIX não são decodificadas aqui).

Nível 3 (`routes/received`): vizinhos com sessão up e rotas recebidas, **um route server por (cidade, família)**: o rs1 se o cache de rotas estiver READY, senão o rs2. Em
rodízio por vizinho (`core.rodizio`): sem leitura primeiro, depois a leitura mais antiga, dentro do orçamento. Cada vizinho é lido por páginas de 250 rotas até
`PAGINAS_MAX_VIZINHO` (padrão 8, 2.000 rotas): vizinho com mais rotas fica **parcial** (`completo: false`) e as origens contadas são um piso, nunca o conjunto inteiro. Quem não
entra na rodada é herdado da anterior com a data original.

Uso:
    python -m sources.decix_alice.collect --date 2026-11-10
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import date as _date
from pathlib import Path
from typing import Callable, Optional

import httpx

from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.rodizio import Limitador
from sources.ixbr_alice.collect import normalizar_sessao
from sources.ixbr_alice_rotas.collect import (
    MAX_IDADE_HERDADA_DIAS, Orcamento, _anterior, _chave, _em, _falhas_para_gravar, _herdar, cobertura_rodizio, elegiveis, ordem_do_rodizio,
)
from core.site import USER_AGENT

BASE = "https://lg.de-cix.net/api/v1"
HEADERS = {"User-Agent": USER_AGENT}
PAUSA_S = float(os.environ.get("ARANDU_DECIX_PAUSA_S", "1.0"))                  # níveis 0 e 1 (11 requisições): 1 s funciona
PAUSA_ROTAS_S = float(os.environ.get("ARANDU_DECIX_PAUSA_ROTAS_S", "10.0"))    # nível 3 (`routes/received`): a 28ª requisição, a ~0,25 req/s, levou HTTP 429; ritmo bem mais lento por segurança
ORCAMENTO = int(os.environ.get("ARANDU_DECIX_ORCAMENTO", "60"))                # requisições por rodada diária (11 dos níveis 0 e 1 e ~49 de rotas, ~9 min)
PAGINAS_MAX_VIZINHO = int(os.environ.get("ARANDU_DECIX_PAGINAS_MAX", "8"))
TEMPO_MAX_S = float(os.environ.get("ARANDU_DECIX_TEMPO_MAX_S", "5400"))
BLOQUEIO_PAUSA_DIAS = int(os.environ.get("ARANDU_DECIX_BLOQUEIO_PAUSA_DIAS", "7"))
ESPERA_CONEXAO_S = float(os.environ.get("ARANDU_DECIX_ESPERA_CONEXAO_S", "60"))      # queda de conexão: uma repetição depois desta espera; a 2ª queda seguida vale bloqueio
CONEXAO = (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError)
PAGE_SIZE = 250
TENTATIVAS = 3
FALHAS_SEGUIDAS_PARA_PARAR = 10
MAX_FALHA = 0.2
MINIMO_RS = 8                                                   # os 8 route servers do escopo (2 cidades × rs1/rs2 × v4/v6)
RS_ESCOPO = re.compile(r"^rs(?P<n>[12])_(?P<cidade>rio|sao)_(?P<afi>ipv4|ipv6)_de-cix$")
CIDADES = {"rio": ("decix-rj", "DE-CIX Rio de Janeiro"), "sao": ("decix-sp", "DE-CIX São Paulo")}


class Bloqueio(Exception):
    """Sinal de bloqueio pelo servidor (403, 429, ou conexão derrubada duas vezes seguidas): a coleta inteira para na hora."""

    def __init__(self, motivo: str, caminho: str):
        super().__init__(f"{motivo} em {caminho}")
        self.motivo, self.caminho = motivo, caminho


def _get(client: httpx.Client, caminho: str, lim: Limitador, dormir: Callable[[float], None], orc: Orcamento) -> dict:
    """GET com intervalo mínimo, orçamento e repetição com recuo em 5xx/timeout. 403/429 → `Bloqueio` na hora (sem repetir). Conexão derrubada ou
    recusada tem **uma** repetição depois de `ESPERA_CONEXAO_S` (pode ser rede ou DNS); a segunda queda seguida → `Bloqueio`."""
    ultimo: Optional[Exception] = None
    caiu = False
    for tentativa in range(TENTATIVAS):
        if orc.resta() <= 0:
            raise RuntimeError("orçamento de requisições esgotado")
        orc.usadas += 1
        lim.esperar()
        try:
            r = client.get(f"{BASE}/{caminho}")
        except CONEXAO as e:
            if caiu:
                raise Bloqueio(f"conexão derrubada duas vezes ({type(e).__name__})", caminho)
            caiu = True
            dormir(ESPERA_CONEXAO_S)
            continue
        except httpx.TimeoutException as e:
            ultimo = e
            dormir(PAUSA_S * (2 ** tentativa) * 2)
            continue
        if r.status_code in (403, 429):
            raise Bloqueio(f"HTTP {r.status_code}", caminho)
        if r.status_code == 404:
            raise LookupError(f"404 {caminho}")
        if r.status_code >= 500:
            ultimo = RuntimeError(f"HTTP {r.status_code}")
            dormir(PAUSA_S * (2 ** tentativa) * 2)
            continue
        try:
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise RuntimeError(f"decix {caminho}: {e}")
    raise RuntimeError(f"decix {caminho}: {ultimo}")


def interpretar_rs(rs_id: str) -> Optional[dict]:
    """{ixp, cidade, numero, afi} do id do route server, ou None se estiver fora do escopo (Rio e São Paulo)."""
    m = RS_ESCOPO.match(rs_id)
    if not m:
        return None
    return {"ixp": CIDADES[m["cidade"]][0], "cidade": CIDADES[m["cidade"]][1], "numero": f"rs{m['n']}", "afi": "v4" if m["afi"] == "ipv4" else "v6"}


def normalizar(status: dict, servidores: dict, vizinhos: dict[str, Optional[list]], erros: dict[str, str], date_str: str, vizinhos_em: dict[str, Optional[str]]) -> dict:
    """`rs_sessions` do DE-CIX: só os route servers do escopo. `vizinhos`: {rs_id: lista de neighbors, ou None se a consulta falhou}."""
    estado_rs = {s.get("name"): s for s in (status.get("routes") or {}).get("route_servers") or []}
    rs, sessoes = [], []
    for r in sorted(servidores.get("routeservers") or [], key=lambda x: x["id"]):
        info = interpretar_rs(r["id"])
        if info is None:
            continue
        rid = r["id"]
        st = estado_rs.get(r.get("name")) or {}
        lista = vizinhos.get(rid)
        linhas = []
        for n in lista or []:
            s = normalizar_sessao(rid, n)
            s.update({"ixp": info["ixp"], "afi": info["afi"], "id_vizinho": n.get("id")})
            linhas.append(s)
        linhas.sort(key=lambda x: (x["asn"] or 0, x["neighbor_ip"] or ""))
        sessoes.extend(linhas)
        rs.append({"rs": rid, "ixp": info["ixp"], "numero": info["numero"], "afi": info["afi"], "nome": r.get("name"), "grupo": r.get("group"),
                   "estado_rotas": st.get("state"), "rotas_atualizadas_em": st.get("updated_at"), "vizinhos_em": vizinhos_em.get(rid),
                   "rotas_importadas": (st.get("routes") or {}).get("imported"), "rotas_filtradas": (st.get("routes") or {}).get("filtered"),
                   "consultado": lista is not None, "erro": erros.get(rid), "sessoes": len(linhas), "sessoes_up": sum(1 for x in linhas if x["estado"] == "up")})
    return {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "https://lg.de-cix.net (Alice-LG)", "versao_alice": status.get("version"),
            "total_rs": len(rs), "rs": rs, "sessoes": sessoes}


def coletar_sessoes(client: httpx.Client, log, lim: Limitador, dormir: Callable[[float], None], orc: Orcamento, date_str: str) -> dict:
    """Níveis 0 e 1: `status`, `routeservers` e o `neighbors` de cada route server do escopo (≈ 11 requisições)."""
    status = _get(client, "status", lim, dormir, orc)
    servidores = _get(client, "routeservers", lim, dormir, orc)
    ids = sorted(r["id"] for r in servidores.get("routeservers") or [] if interpretar_rs(r["id"]))
    if len(ids) < MINIMO_RS:
        raise RuntimeError(f"decix_alice: {len(ids)} route servers de Rio e São Paulo (esperado {MINIMO_RS})")
    vizinhos: dict[str, Optional[list]] = {}
    erros: dict[str, str] = {}
    em: dict[str, Optional[str]] = {}
    for rid in ids:
        try:
            resp = _get(client, f"routeservers/{rid}/neighbors", lim, dormir, orc)
            vizinhos[rid] = resp.get("neighbors") or []
            em[rid] = ((resp.get("api") or {}).get("cache_status") or {}).get("cached_at")
        except (RuntimeError, LookupError) as e:
            vizinhos[rid], erros[rid] = None, str(e)[:200]
            log.warning("neighbors falhou", rs=rid, erro=erros[rid])
    if len(erros) > MAX_FALHA * len(ids):
        raise RuntimeError(f"decix_alice: neighbors falhou em {len(erros)} de {len(ids)} route servers")
    return normalizar(status, servidores, vizinhos, erros, date_str, em)


def _origem(rota: dict, asn_vizinho: int) -> Optional[int]:
    """ASN de origem: o último do AS_PATH (rota própria do vizinho pode vir com o caminho só dele ou vazio)."""
    caminho = [a for a in ((rota.get("bgp") or {}).get("as_path") or []) if isinstance(a, int)]
    return caminho[-1] if caminho else asn_vizinho


def ler_vizinho(client: httpx.Client, s: dict, lim: Limitador, dormir: Callable[[float], None], orc: Orcamento, paginas_max: int) -> dict:
    """Lê as páginas de `routes/received` de um vizinho (até `paginas_max`, enquanto houver orçamento) e conta as rotas por ASN de origem."""
    origens: dict[int, int] = {}
    lidas = paginas = 0
    total: Optional[int] = None
    total_paginas = 1
    coletado_em = None
    for p in range(max(1, paginas_max)):
        if p >= total_paginas or orc.resta() <= 0:
            break
        resp = _get(client, f"routeservers/{s['rs']}/neighbors/{s['id_vizinho']}/routes/received?page={p}&page_size={PAGE_SIZE}", lim, dormir, orc)
        pag = resp.get("pagination") or {}
        total = pag.get("total_results", total)
        total_paginas = int(pag.get("total_pages") or 1)
        coletado_em = coletado_em or _em(resp)
        rotas = resp.get("imported") or []
        for r in rotas:
            o = _origem(r, s["asn"])
            if o is not None:
                origens[o] = origens.get(o, 0) + 1
        lidas += len(rotas)
        paginas += 1
    if total is None:
        total = lidas
    return {"rs": s["rs"], "ixp": s["ixp"], "afi": s["afi"], "asn": s["asn"], "ip": s["neighbor_ip"], "id": s["id_vizinho"], "coletado_em": coletado_em or now_iso(),
            "consultado_em": now_iso(), "total": total, "sessao_recebidas": (s.get("rotas") or {}).get("recebidas"), "lidas": lidas, "paginas": paginas,
            "completo": lidas >= total, "origens": {str(k): v for k, v in sorted(origens.items())}}


def coletar_rotas(sessoes: dict, base: Path, date_str: str, client: httpx.Client, log, lim: Limitador, dormir: Callable[[float], None], orc: Orcamento,
                  paginas_max: int = PAGINAS_MAX_VIZINHO) -> tuple[dict, dict, Optional[Bloqueio]]:
    """Nível 3 em rodízio por vizinho. Devolve (documento, resumo, bloqueio ou None). O documento sai sempre, com o que se leu mais o herdado."""
    el = [s for s in elegiveis(sessoes, 3) if s.get("id_vizinho")]
    vivos = {_chave(s) for s in sessoes.get("sessoes") or [] if s.get("estado") == "up"}
    _, ant = _anterior(base, date_str, "decix_rs_rotas.json.gz")
    feitos: dict[tuple, dict] = {}
    falhou: dict[tuple, dict] = {}
    falhas = seguidas = tentados = 0
    bloqueio: Optional[Bloqueio] = None
    for s in ordem_do_rodizio(el, ant):
        if orc.resta() <= 0:
            break
        if s["rs"] in orc.pulados:
            continue
        tentados += 1
        t = orc.relogio()
        try:
            v = ler_vizinho(client, s, lim, dormir, orc, paginas_max)
        except Bloqueio as b:
            bloqueio = b
            log.error("sinal de bloqueio do DE-CIX: coleta interrompida", motivo=b.motivo, caminho=b.caminho)
            break
        except (RuntimeError, LookupError) as e:
            if orc.resta() <= 0 and "orçamento" in str(e):
                break
            falhas += 1
            seguidas += 1
            falhou[_chave(s)] = {"ixp": s["ixp"], "afi": s["afi"], "asn": s["asn"], "ip": s["neighbor_ip"], "em": now_iso(), "erro": str(e)[:120]}
            log.warning("rotas do vizinho falharam", rs=s["rs"], asn=s["asn"], erro=str(e)[:160])
            if seguidas >= FALHAS_SEGUIDAS_PARA_PARAR:
                log.error("alice do DE-CIX falhou seguidamente; rodada interrompida", falhas_seguidas=seguidas)
                break
            continue
        seguidas = 0
        if orc.registra(s["rs"], orc.relogio() - t, None):
            log.warning("route server lento: fora da rodada", **orc.pulados[s["rs"]])
        feitos[_chave(s)] = v
    herdados = _herdar(ant, feitos, vivos, date_str)
    vizinhos = sorted([*feitos.values(), *herdados], key=lambda v: (v["ixp"], v["afi"], v["asn"], v["ip"]))
    cab = {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "https://lg.de-cix.net (Alice-LG)", "versao_alice": sessoes.get("versao_alice"),
           "page_size": PAGE_SIZE, "paginas_max_vizinho": paginas_max, "nivel": 3}
    doc = {**cab, "cobertura_rodizio": cobertura_rodizio(el, feitos, herdados, date_str, set(orc.pulados)),
           "falhas": _falhas_para_gravar(ant, falhou, feitos, vivos, date_str), "requisicoes_da_rodada": orc.usadas, "orcamento": orc.limite,
           "segundos_da_rodada": round(orc.relogio() - orc.t0, 1), "rs_pulados": list(orc.pulados.values()), "vizinhos": vizinhos}
    if bloqueio:
        doc["bloqueio"] = {"em": now_iso(), "motivo": bloqueio.motivo, "caminho": bloqueio.caminho}
    resumo = {"elegiveis": len(el), "consultados": len(feitos), "falhas": falhas, "herdados": len(herdados), "tentados": tentados}
    return doc, resumo, bloqueio


def _bloqueio_recente(base: Path, date_str: str) -> Optional[dict]:
    """Bloqueio registrado numa rodada anterior há no máximo `BLOQUEIO_PAUSA_DIAS` dias (a coleta nem tenta de novo sem --ignorar-bloqueio)."""
    for nome in ("decix_rs_sessions.json.gz", "decix_rs_rotas.json.gz"):
        d, ant = _anterior(base, date_str, nome)
        b = (ant or {}).get("bloqueio")
        if b and not b.get("liberado") and d and (_date.fromisoformat(date_str) - _date.fromisoformat(d)).days <= BLOQUEIO_PAUSA_DIAS:
            return {**b, "rodada": d}
    return None


def liberar_bloqueio(base: Path, date_str: str, motivo: str, por: str = "mantenedor") -> list[str]:
    """Marca como liberado o bloqueio registrado nos documentos de `date_str` (o registro fica, com quem liberou e por quê): a próxima rodada volta a coletar.
    Devolve os arquivos alterados."""
    alterados = []
    for nome in ("decix_rs_sessions.json.gz", "decix_rs_rotas.json.gz"):
        p = normalized_path(base, date_str, "summary") / nome
        if not p.exists():
            continue
        doc = read_json_gz(p)
        b = doc.get("bloqueio")
        if b and not b.get("liberado"):
            b["liberado"] = {"em": now_iso(), "por": por, "motivo": motivo}
            write_json_gz(p, doc)
            alterados.append(nome)
    return alterados


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, dormir: Callable[[float], None] = time.sleep, force: bool = False,
        orcamento: int = ORCAMENTO, tempo_max_s: float = TEMPO_MAX_S, relogio: Callable[[], float] = time.monotonic, paginas_max: int = PAGINAS_MAX_VIZINHO) -> dict:
    anterior = None if force else _bloqueio_recente(base, date_str)
    if anterior:
        raise RuntimeError(f"decix_alice: bloqueio registrado em {anterior['rodada']} ({anterior['motivo']}); a coleta não tenta de novo antes de {BLOQUEIO_PAUSA_DIAS} dias nem sem --ignorar-bloqueio")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    orc = Orcamento(orcamento, tempo_max_s, relogio)
    lim = Limitador(PAUSA_S, relogio, dormir)
    try:
        try:
            sessoes = coletar_sessoes(client, log, lim, dormir, orc, date_str)
        except Bloqueio as b:
            write_json_gz(destino / "decix_rs_sessions.json.gz", {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "https://lg.de-cix.net (Alice-LG)", "total_rs": 0,
                                                                 "rs": [], "sessoes": [], "bloqueio": {"em": now_iso(), "motivo": b.motivo, "caminho": b.caminho}})
            raise RuntimeError(f"decix_alice: sinal de bloqueio ({b}); coleta interrompida e registrada")
        write_json_gz(destino / "decix_rs_sessions.json.gz", sessoes)                  # antes do nível 3: o que se tem não se perde se a rodada parar
        lim_rotas = Limitador(PAUSA_ROTAS_S, relogio, dormir).continuar_de(lim)
        doc, resumo, bloqueio = coletar_rotas(sessoes, base, date_str, client, log, lim_rotas, dormir, orc, paginas_max)
    finally:
        if proprio:
            client.close()
    write_json_gz(destino / "decix_rs_rotas.json.gz", doc)
    resumo = {"rs": sessoes["total_rs"], "sessoes": len(sessoes["sessoes"]), "requisicoes": orc.usadas, "segundos": round(orc.relogio() - orc.t0, 1), "nivel3": resumo}
    log.info("decix_alice written", rs=resumo["rs"], sessoes=resumo["sessoes"], requisicoes=orc.usadas, nivel3=resumo["nivel3"])
    if bloqueio:
        raise RuntimeError(f"decix_alice: sinal de bloqueio ({bloqueio}); coleta interrompida, o que foi lido foi gravado")
    n3 = resumo["nivel3"]
    if n3["tentados"] and n3["falhas"] > MAX_FALHA * n3["tentados"]:
        raise RuntimeError(f"decix_alice: {n3['falhas']} de {n3['tentados']} vizinhos falharam")
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Route servers do DE-CIX Rio e São Paulo (Alice-LG, níveis 0, 1 e 3)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; não ignora bloqueio registrado")
    p.add_argument("--liberar-bloqueio", metavar="DATA", help="marca como liberado o bloqueio registrado em DATA (só depois de o mantenedor avaliar) e não coleta nada")
    p.add_argument("--motivo", default="", help="com --liberar-bloqueio: por que foi liberado")
    p.add_argument("--ignorar-bloqueio", action="store_true", help="coleta mesmo com bloqueio registrado numa rodada recente (só depois de o mantenedor avaliar)")
    p.add_argument("--orcamento", type=int, default=None, help="requisições por rodada (padrão: ARANDU_DECIX_ORCAMENTO)")
    p.add_argument("--paginas-max", type=int, default=None, help="páginas de 250 rotas por vizinho (padrão: ARANDU_DECIX_PAGINAS_MAX)")
    a = p.parse_args(argv)
    if a.liberar_bloqueio:
        if not a.motivo:
            p.error("--liberar-bloqueio exige --motivo")
        print({"liberados": liberar_bloqueio(data_dir(), a.liberar_bloqueio, a.motivo)})
        return 0
    kw: dict = {"force": a.ignorar_bloqueio}
    if a.orcamento is not None:
        kw["orcamento"] = a.orcamento
    if a.paginas_max is not None:
        kw["paginas_max"] = a.paginas_max
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, **kw))
    except Exception:
        log.exception("falha na coleta de decix_alice")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
