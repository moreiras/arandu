# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rotas rejeitadas e communities dos membros nos route servers do IX.br pelo Alice-LG (níveis 2 e 3).

Fonte:       https://lg.ix.br/api/v1/routeservers/{rs}/neighbors/{id}/routes/{filtered|received}?page=0&page_size=250
Entrada:     data/normalized/{date}/summary/rs_sessions.json.gz e ixbr_communities.json.gz (gerados pelo `ixbr_alice`, nível 0 e 1, na mesma rodada)
Normalizado: data/normalized/{date}/summary/rs_filtered.json.gz      nível 2: por vizinho, rotas rejeitadas por motivo (+ amostra de prefixos)
             data/normalized/{date}/summary/rs_communities.json.gz   nível 3: por vizinho, uso de cada community nas rotas recebidas
Bruto:       não é guardado (derivados apenas).

O que a API entrega e por que uma requisição por vizinho basta: cada resposta traz `pagination.total_results` e `filters_available`, com a **contagem exata de cada
community sobre o conjunto inteiro** (não só da página). Então a página 0 dá o total e o uso exato de cada community, e as primeiras 250 rotas servem de amostra
de prefixos (o `page_size` é fixo em 250: o servidor ignora valores menores). Sem `filters_available` (versão antiga do Alice), a contagem vem da amostra e fica
marcada `contagem: "amostra"`.

Carga (o `robots.txt` do lg.ix.br pede `Crawl-delay: 1`): pausa de 1 s (`ARANDU_ALICE_PAUSA_S`), uma requisição por vez, repetição com recuo só em erro transitório
(rede, 429, 5xx) e **orçamento de requisições por rodada** (`ARANDU_ALICE_ORCAMENTO`, conta toda tentativa). Para a rodada se o Alice falhar 10 vezes seguidas.
  * Nível 2 (`routes/filtered`): vizinhos com sessão up e `routes_filtered > 0`, na ordem de prioridade dos PTTs; vai primeiro.
  * Nível 3 (`routes/received`): vizinhos com sessão up e rotas recebidas, nos PTTs de `ARANDU_ALICE_PTTS_N3` (padrão `todos`; uma lista separada por vírgula limita).
  * **Rodízio por vizinho:** os dois níveis escolhem os vizinhos por idade da leitura (`core.rodizio.escolher_por_idade`): primeiro quem nunca foi lido,
    depois quem foi lido há mais tempo, com a prioridade do PTT só como desempate. Com os dois níveis, o nível 2 usa no máximo metade do orçamento (o resto vai ao nível 3,
    inclusive o que o nível 2 não gastar). Vizinho cuja consulta falhou vai para o fim da fila (`falhas` no documento). Quem não entra na rodada é **herdado** da
    rodada anterior (`herdado: true`, com o `coletado_em` original) por até `MAX_IDADE_HERDADA_DIAS`. O intervalo mínimo entre requisições (`core.rodizio.Limitador`, 1 s)
    vale para toda requisição, repetições incluídas. A cobertura de cada PTT e a total (elegíveis, lidos na rodada, herdados, sem leitura, idade máxima) vai em `cobertura_rodizio`.
  * Cada vizinho é consultado em **um** route server: o rs1 se o cache de rotas do Alice estiver READY, senão o rs2 (os dois recebem as mesmas rotas do membro).
    Os route servers com o cache de rotas em ERROR são deixados por último.
  * `ARANDU_ALICE_NIVEIS` escolhe os níveis (padrão `2,3`); `ARANDU_ALICE_PTTS_N2` limita os PTTs do nível 2 (padrão `todos`).
  * **Route server lento:** o custo de uma consulta não é uniforme. Medido: o servidor leva ~1 s no SP rs1/rs2 e **~66 s por vizinho** no CE rs2 IPv4 (cada
    vizinho novo é uma consulta nova no route server; só repetir o mesmo vizinho vem do cache de 5 min do Alice). Por isso, 3 consultas seguidas acima de `ARANDU_ALICE_LENTO_S`
    (padrão 20 s) tiram o route server da rodada (`rs_pulados` no documento, vizinhos dele herdados da rodada anterior) e `ARANDU_ALICE_TEMPO_MAX_S` (padrão 25200) limita o relógio
    da rodada inteira. O documento guarda o tempo por route server (`tempo_por_rs`).
  * **Route server com falhas:** 5 falhas seguidas (HTTP 5xx, rede) do mesmo route server o tiram da rodada, como o lento (`rs_pulados`, com o motivo); a rodada só para se 10 falhas seguidas
    ocorrerem em route servers diferentes (o Alice todo fora). A coleta ainda falha
    alto, depois de gravar, se mais de 20% dos vizinhos consultados falharam.

Uso:
    python -m sources.ixbr_alice_rotas.collect --date 2026-11-06
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date as _date
from pathlib import Path
from typing import Callable, Optional

import httpx

from core.rodizio import Limitador, escolher_por_idade
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.ixbr_communities import Dicionario, chaves_da_rota
from core.site import USER_AGENT

BASE = "https://lg.ix.br/api/v1"
HEADERS = {"User-Agent": USER_AGENT}
PAUSA_S = float(os.environ.get("ARANDU_ALICE_PAUSA_S", "1.0"))
ORCAMENTO = int(os.environ.get("ARANDU_ALICE_ORCAMENTO", "10000"))   # 2,38 s por requisição (medido): 10000 ≈ 6,6 h; com as outras etapas (~5,75 h) e o pipeline semanal (~7,5 h) o dia de publicação fica ≈ 20 h
NIVEIS = tuple(int(x) for x in os.environ.get("ARANDU_ALICE_NIVEIS", "2,3").split(",") if x.strip())
PTTS_N3 = tuple(x.strip().lower() for x in os.environ.get("ARANDU_ALICE_PTTS_N3", "todos").split(",") if x.strip())
AMOSTRA = int(os.environ.get("ARANDU_ALICE_AMOSTRA", "25"))        # rotas por vizinho guardadas como amostra (nível 2)
PTTS_N2 = tuple(x.strip().lower() for x in os.environ.get("ARANDU_ALICE_PTTS_N2", "todos").split(",") if x.strip())
LENTO_S = float(os.environ.get("ARANDU_ALICE_LENTO_S", "20"))
LENTOS_SEGUIDOS = 3
TEMPO_MAX_S = float(os.environ.get("ARANDU_ALICE_TEMPO_MAX_S", "25200"))   # relógio máximo da rodada: 7 h
PRIORIDADE = ("sp", "rj", "ce", "df")                               # PTTs que vêm antes dos demais, nesta ordem
MAX_IDADE_HERDADA_DIAS = 35
TENTATIVAS = 3
FALHAS_SEGUIDAS_PARA_PARAR = 10                                     # falhas seguidas (em route servers que ainda não foram tirados da rodada) que interrompem a rodada inteira: o Alice como um todo está fora
FALHAS_SEGUIDAS_POR_RS = 5                                          # falhas seguidas num mesmo route server: ele sai da rodada (como o lento), as outras seguem (um route server com HTTP 500 em série não pode parar a rodada inteira0 requisições, deixando os PTTs seguintes sem leitura
MAX_FALHA = 0.2                                                     # fração de vizinhos consultados que falharam acima da qual a coleta falha (depois de gravar)
PAGE_SIZE = 250


def id_vizinho(asn: int, ip: str) -> str:
    """Id do vizinho no Alice: `AS{asn}_{endereço com '.' e ':' trocados por '_'}` (conferido contra os 4.072 vizinhos v4 e v6 de 2026-11-06)."""
    return f"AS{asn}_{ip.replace('.', '_').replace(':', '_')}"


class Orcamento:
    """Requisições e relógio da rodada, e o tempo medido por route server (para pular o que está lento)."""

    def __init__(self, limite: int, tempo_max_s: float = 0, relogio: Callable[[], float] = time.monotonic, lento_s: float = LENTO_S):
        self.limite, self.usadas = limite, 0
        self.tempo_max_s, self.relogio, self.lento_s = tempo_max_s, relogio, lento_s
        self.t0 = relogio()
        self.tempo: dict[str, dict] = {}          # rs → {n, s_total, s_max, ms_servidor_total}
        self.lentos_seguidos: dict[str, int] = {}
        self.pulados: dict[str, dict] = {}

    def resta(self) -> int:
        if self.tempo_max_s and self.relogio() - self.t0 > self.tempo_max_s:
            return 0                              # relógio da rodada esgotado: tratado como orçamento esgotado
        return max(0, self.limite - self.usadas)

    def registra(self, rs: str, segundos: float, ms_servidor: Optional[float]) -> bool:
        """Anota o tempo de uma consulta; True se o route server passou a ser pulado (3 consultas seguidas acima de `lento_s`)."""
        t = self.tempo.setdefault(rs, {"n": 0, "s_total": 0.0, "s_max": 0.0, "ms_servidor_total": 0.0})
        t["n"] += 1
        t["s_total"] += segundos
        t["s_max"] = max(t["s_max"], segundos)
        t["ms_servidor_total"] += ms_servidor or 0
        self.lentos_seguidos[rs] = self.lentos_seguidos.get(rs, 0) + 1 if segundos > self.lento_s else 0
        if self.lentos_seguidos[rs] >= LENTOS_SEGUIDOS and rs not in self.pulados:
            self.pulados[rs] = {"rs": rs, "motivo": f"{LENTOS_SEGUIDOS} consultas seguidas acima de {self.lento_s:g} s", "media_s": round(t["s_total"] / t["n"], 1)}
            return True
        return False

    def tira_por_falhas(self, rs: str, n: int) -> bool:
        """Tira o route server da rodada depois de `n` falhas seguidas dele (5xx, rede); True se foi tirado agora. Os vizinhos dele ficam herdados da rodada anterior."""
        if rs in self.pulados:
            return False
        self.pulados[rs] = {"rs": rs, "motivo": f"{n} falhas seguidas do route server (HTTP 5xx ou rede)", "media_s": None}
        return True

    def resumo_tempo(self) -> dict:
        return {rs: {"consultas": t["n"], "s_medio": round(t["s_total"] / t["n"], 2), "s_max": round(t["s_max"], 1), "ms_servidor_medio": round(t["ms_servidor_total"] / t["n"])}
                for rs, t in sorted(self.tempo.items())}


class AliceParou(Exception):
    """Falhas seguidas demais: a rodada para sem insistir no servidor."""


def _consulta(client: httpx.Client, caminho: str, dormir: Callable[[float], None], orc: Orcamento, lim: Optional[Limitador] = None) -> dict:
    ultimo: Optional[Exception] = None
    for tentativa in range(TENTATIVAS):
        if orc.resta() <= 0:
            raise AliceParou("orçamento de requisições esgotado")
        orc.usadas += 1
        if lim is not None:
            lim.esperar()                         # intervalo mínimo entre duas requisições ao Alice (1 s), repetições incluídas
        try:
            r = client.get(f"{BASE}/{caminho}")
            if r.status_code == 404:
                raise LookupError(f"404 {caminho}")
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError(f"{r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            return r.json()
        except LookupError:
            raise
        except (httpx.HTTPError, ValueError) as e:
            ultimo = e
            dormir(PAUSA_S * (2 ** tentativa) * 2)
    raise RuntimeError(f"alice {caminho}: {ultimo}")


def _prioridade_ptt(ixp: str) -> int:
    return PRIORIDADE.index(ixp) if ixp in PRIORIDADE else len(PRIORIDADE)


def elegiveis(rs_doc: dict, nivel: int, ptts: Optional[tuple[str, ...]] = None) -> list[dict]:
    """Vizinhos a consultar: sessão up (nível 2: com rotas filtradas; nível 3: com rotas recebidas), um por (PTT, família, ASN, IP), no route server com cache de rotas pronto."""
    estado = {r["rs"]: r.get("estado_rotas") for r in rs_doc.get("rs") or []}
    campo = "filtradas" if nivel == 2 else "recebidas"
    melhor: dict[tuple, dict] = {}
    for s in sorted(rs_doc.get("sessoes") or [], key=lambda s: (estado.get(s["rs"]) == "ERROR", estado.get(s["rs"]) != "READY", s["rs"])):
        if s.get("estado") != "up" or not (s.get("rotas") or {}).get(campo) or s.get("asn") is None or not s.get("neighbor_ip"):
            continue
        if ptts is not None and "todos" not in ptts and s["ixp"] not in ptts:
            continue
        melhor.setdefault((s["ixp"], s["afi"], s["asn"], s["neighbor_ip"]), s)
    return sorted(melhor.values(), key=lambda s: (_prioridade_ptt(s["ixp"]), s["ixp"], s["afi"], s["asn"], s["neighbor_ip"]))


def _chave(s: dict) -> tuple:
    return (s["ixp"], s["afi"], s["asn"], s.get("neighbor_ip") or s.get("ip"))


def _contagens(resp: dict, rotas: list[dict]) -> tuple[dict[str, int], str]:
    """({community: nº de rotas}, 'exata'|'amostra'): `filters_available` conta sobre o conjunto inteiro; sem ele, só dá para contar a página."""
    filtros = resp.get("filters_available")
    if isinstance(filtros, list) and any(isinstance(f, dict) and f.get("key") == "communities" for f in filtros):
        out: dict[str, int] = {}
        for f in filtros:
            if f.get("key") in ("communities", "large_communities", "ext_communities"):
                for x in f.get("filters") or []:
                    if x.get("name") and isinstance(x.get("cardinality"), int):
                        out[x["name"]] = x["cardinality"]
        return out, "exata"
    out = {}
    for r in rotas:
        for c in set(chaves_da_rota(r.get("bgp") or {})):
            out[c] = out.get(c, 0) + 1
    return out, "amostra"


def _origem(r: dict) -> Optional[int]:
    p = (r.get("bgp") or {}).get("as_path") or []
    return p[-1] if p else None


def resumir_filtradas(resp: dict, s: dict, dic: Dicionario, amostra: int) -> dict:
    rotas = resp.get("filtered") or []
    total = (resp.get("pagination") or {}).get("total_results")
    cont, forma = _contagens(resp, rotas)
    motivos = {c: n for c, n in cont.items() if dic.classificar(c)["classe"] in ("rejeicao", "blackhole")}
    amostras = []
    for r in rotas[:amostra]:
        ms = [c for c in chaves_da_rota(r.get("bgp") or {}) if c in motivos or dic.classificar(c)["classe"] in ("rejeicao", "blackhole")]
        amostras.append({"p": r.get("network"), "o": _origem(r), "m": sorted(set(ms))})
    return {"rs": s["rs"], "ixp": s["ixp"], "afi": s["afi"], "asn": s["asn"], "ip": s["neighbor_ip"], "coletado_em": _em(resp), "consultado_em": now_iso(), "total": total if total is not None else len(rotas),
            "sessao_filtradas": (s.get("rotas") or {}).get("filtradas"), "contagem": forma, "motivos": motivos,
            "sem_motivo": max(0, (total or len(rotas)) - sum(motivos.values())), "amostra": amostras}


def resumir_recebidas(resp: dict, s: dict) -> dict:
    rotas = resp.get("imported") or []
    total = (resp.get("pagination") or {}).get("total_results")
    cont, forma = _contagens(resp, rotas)
    return {"rs": s["rs"], "ixp": s["ixp"], "afi": s["afi"], "asn": s["asn"], "ip": s["neighbor_ip"], "coletado_em": _em(resp), "consultado_em": now_iso(), "total": total if total is not None else len(rotas),
            "sessao_recebidas": (s.get("rotas") or {}).get("recebidas"), "contagem": forma, "comunidades": dict(sorted(cont.items()))}


def _em(resp: dict) -> str:
    return ((resp.get("api") or {}).get("cache_status") or {}).get("cached_at") or now_iso()


def _anterior(base: Path, date_str: str, nome: str) -> tuple[Optional[str], Optional[dict]]:
    """Documento `nome` da rodada mais recente anterior a `date_str` (para herdar o que esta rodada não renovou)."""
    raiz = base / "normalized"
    datas = sorted((p.name for p in raiz.iterdir() if p.is_dir() and p.name < date_str and (p / "summary" / nome).exists()), reverse=True) if raiz.exists() else []
    for d in datas[:3]:
        try:
            return d, read_json_gz(raiz / d / "summary" / nome)       # type: ignore[return-value]
        except Exception:
            continue
    return None, None


def _herdar(anterior: Optional[dict], novos: dict[tuple, dict], vivos: set[tuple], date_str: str) -> list[dict]:
    """Vizinhos da rodada anterior que esta não renovou, ainda com sessão up e com idade ≤ MAX_IDADE_HERDADA_DIAS."""
    out = []
    ref = _date.fromisoformat(date_str)
    for v in (anterior or {}).get("vizinhos") or []:
        k = _chave(v)
        if k in novos or k not in vivos:
            continue
        try:
            idade = (ref - _date.fromisoformat(str(v.get("coletado_em"))[:10])).days
        except ValueError:
            continue
        if 0 <= idade <= MAX_IDADE_HERDADA_DIAS:
            out.append({**v, "herdado": True})
    return out


def _consultar_lote(client, log, dormir, orc: Orcamento, tipo: str, ordem: list[dict], dic: Dicionario, amostra: int, lim: Optional[Limitador] = None,
                    teto: Optional[int] = None) -> tuple[dict[tuple, dict], int, int, dict[tuple, dict]]:
    """Consulta a página 0 de cada vizinho de `ordem` (já na ordem do rodízio) até esgotar o orçamento (ou `teto` requisições gastas no total).

    Devolve ({chave: resumo}, tentados, falhas, {chave: falha})."""
    feitos: dict[tuple, dict] = {}
    falhou: dict[tuple, dict] = {}
    falhas = seguidas = tentados = 0
    seguidas_rs: dict[str, int] = {}
    for s in ordem:
        if orc.resta() <= 0 or (teto is not None and orc.usadas >= teto):
            break
        if s["rs"] in orc.pulados:
            continue
        tentados += 1
        caminho = f"routeservers/{s['rs']}/neighbors/{id_vizinho(s['asn'], s['neighbor_ip'])}/routes/{tipo}?page=0&page_size={PAGE_SIZE}"
        t = orc.relogio()
        try:
            resp = _consulta(client, caminho, dormir, orc, lim)
        except AliceParou:
            break
        except (RuntimeError, LookupError) as e:
            falhas += 1
            seguidas += 1
            seguidas_rs[s["rs"]] = seguidas_rs.get(s["rs"], 0) + 1
            falhou[_chave(s)] = {"ixp": s["ixp"], "afi": s["afi"], "asn": s["asn"], "ip": s["neighbor_ip"], "em": now_iso(), "erro": str(e)[:120]}
            log.warning("rotas do vizinho falharam", rs=s["rs"], asn=s["asn"], tipo=tipo, erro=str(e)[:160])
            if seguidas_rs[s["rs"]] >= FALHAS_SEGUIDAS_POR_RS and orc.tira_por_falhas(s["rs"], seguidas_rs[s["rs"]]):
                log.warning("route server com falhas seguidas: fora da rodada", rs=s["rs"], falhas_seguidas=seguidas_rs[s["rs"]])
                seguidas = 0                                  # a falha é deste route server, não do Alice todo
                continue
            if seguidas >= FALHAS_SEGUIDAS_PARA_PARAR:
                log.error("alice falhou seguidamente; rodada interrompida", tipo=tipo, falhas_seguidas=seguidas)
                break
            continue
        seguidas = 0
        seguidas_rs[s["rs"]] = 0
        if orc.registra(s["rs"], orc.relogio() - t, resp.get("request_duration_ms")):
            log.warning("route server lento: fora da rodada", **orc.pulados[s["rs"]])
        feitos[_chave(s)] = resumir_filtradas(resp, s, dic, amostra) if tipo == "filtered" else resumir_recebidas(resp, s)
    return feitos, tentados, falhas, falhou


def ordem_do_rodizio(el: list[dict], anterior: Optional[dict]) -> list[dict]:
    """`el` na ordem do rodízio: sem leitura primeiro, depois a leitura (ou tentativa que falhou) mais antiga; empate pela prioridade do PTT.

    A última leitura vem do documento da rodada anterior: `vizinhos[].consultado_em` (o relógio da nossa consulta, não o `cached_at` do Alice, que pode ser mais velho) ou, em documento antigo, `coletado_em`; e `falhas[].em`."""
    ultima = {_chave(v): str(v.get("consultado_em") or v.get("coletado_em") or "") for v in (anterior or {}).get("vizinhos") or []}
    for f in (anterior or {}).get("falhas") or []:
        k = (f["ixp"], f["afi"], f["asn"], f["ip"])
        ultima[k] = max(ultima.get(k, ""), str(f.get("em") or ""))
    por_id = {(_prioridade_ptt(s["ixp"]), *_chave(s)): s for s in el}
    return [por_id[i] for i in escolher_por_idade(por_id, lambda i: ultima.get(i[1:], ""), 0)]


def _falhas_para_gravar(anterior: Optional[dict], novas: dict[tuple, dict], feitos: dict, vivos: set[tuple], date_str: str) -> list[dict]:
    """Falhas recentes: as desta rodada mais as anteriores de quem ainda não foi lido, ainda com sessão up e com idade ≤ MAX_IDADE_HERDADA_DIAS."""
    out = dict(novas)
    ref = _date.fromisoformat(date_str)
    for f in (anterior or {}).get("falhas") or []:
        k = (f["ixp"], f["afi"], f["asn"], f["ip"])
        if k in out or k in feitos or k not in vivos:
            continue
        try:
            if 0 <= (ref - _date.fromisoformat(str(f.get("em"))[:10])).days <= MAX_IDADE_HERDADA_DIAS:
                out[k] = f
        except ValueError:
            continue
    return sorted(out.values(), key=lambda f: (f["ixp"], f["afi"], f["asn"], f["ip"]))


def _cobertura(elegiveis_: list[dict], feitos: dict, herdados: list[dict], pulados: Optional[set] = None) -> dict:
    por: dict[str, dict] = {}
    for s in elegiveis_:
        por.setdefault(s["ixp"], {"elegiveis": 0, "coletados": 0, "herdados": 0})["elegiveis"] += 1
        if pulados and s["rs"] in pulados and _chave(s) not in feitos:
            por[s["ixp"]]["pulados_lentos"] = por[s["ixp"]].get("pulados_lentos", 0) + 1
    chaves_el = {_chave(s) for s in elegiveis_}
    for k in feitos:
        por.setdefault(k[0], {"elegiveis": 0, "coletados": 0, "herdados": 0})["coletados"] += 1
    for v in herdados:          # só o herdado que ainda é elegível e não foi relido: `coletados` + `herdados` não passa de `elegiveis`
        if _chave(v) in chaves_el and _chave(v) not in feitos:
            por.setdefault(v["ixp"], {"elegiveis": 0, "coletados": 0, "herdados": 0})["herdados"] += 1
    return dict(sorted(por.items()))


def cobertura_rodizio(el: list[dict], feitos: dict, herdados: list[dict], date_str: str, pulados: Optional[set] = None) -> dict:
    """Cobertura do rodízio por PTT e total, só sobre os vizinhos elegíveis hoje: lidos nesta rodada, herdados, sem leitura nenhuma e idade máxima da leitura (dias)."""
    ref = _date.fromisoformat(date_str)
    her = {_chave(v): v for v in herdados}
    por: dict[str, dict] = {}

    def novo() -> dict:
        return {"elegiveis": 0, "lidos_na_rodada": 0, "herdados": 0, "sem_leitura": 0, "idade_max_dias": None, "pulados_lentos": 0}

    def idade(em) -> Optional[int]:
        try:
            return max(0, (ref - _date.fromisoformat(str(em)[:10])).days)
        except ValueError:
            return None

    total = novo()
    for s in el:
        k = _chave(s)
        for c in (por.setdefault(s["ixp"], novo()), total):
            c["elegiveis"] += 1
            if k in feitos:
                c["lidos_na_rodada"] += 1
                i = idade(feitos[k].get("coletado_em"))
            elif k in her:
                c["herdados"] += 1
                i = idade(her[k].get("coletado_em"))
            else:
                c["sem_leitura"] += 1
                i = None
                if pulados and s["rs"] in pulados:
                    c["pulados_lentos"] += 1
            if i is not None:
                c["idade_max_dias"] = i if c["idade_max_dias"] is None else max(c["idade_max_dias"], i)
    return {"total": total, "por_ptt": dict(sorted(por.items()))}


def coletar(rs_doc: dict, comm_doc: dict, base: Path, date_str: str, client: httpx.Client, log, dormir: Callable[[float], None] = time.sleep,
            niveis: tuple[int, ...] = NIVEIS, orcamento: int = ORCAMENTO, ptts_n3: tuple[str, ...] = PTTS_N3, amostra: int = AMOSTRA, ptts_n2: tuple[str, ...] = PTTS_N2,
            tempo_max_s: float = TEMPO_MAX_S, relogio: Callable[[], float] = time.monotonic, lento_s: float = LENTO_S) -> tuple[Optional[dict], Optional[dict], dict]:
    """Devolve (rs_filtered, rs_communities, resumo); o documento de um nível não pedido é None."""
    dic = Dicionario(comm_doc)
    orc = Orcamento(orcamento, tempo_max_s, relogio, lento_s)
    resumo: dict = {"niveis": list(niveis), "orcamento": orcamento}
    gerado = now_iso()
    vivos = {_chave(s) for s in rs_doc.get("sessoes") or [] if s.get("estado") == "up"}
    cab = {"snapshot_date": date_str, "generated_at": gerado, "fonte": "https://lg.ix.br (Alice-LG)", "versao_alice": rs_doc.get("versao_alice"), "page_size": PAGE_SIZE}
    f_doc = c_doc = None
    tentados_total = falhas_total = 0
    lim = Limitador(PAUSA_S, relogio, dormir)
    if 2 in niveis:
        el = elegiveis(rs_doc, 2, ptts_n2)
        ant_d, ant = _anterior(base, date_str, "rs_filtered.json.gz")
        teto = orc.usadas + (max(1, orcamento // 2) if 3 in niveis else orcamento)      # com os dois níveis, o 2 não come mais que metade; a sobra vai ao 3
        feitos, tentados, falhas, falhou = _consultar_lote(client, log, dormir, orc, "filtered", ordem_do_rodizio(el, ant), dic, amostra, lim, teto)
        herdados = _herdar(ant, feitos, vivos, date_str)
        vizinhos = sorted([*feitos.values(), *herdados], key=lambda v: (v["ixp"], v["afi"], v["asn"], v["ip"]))
        f_doc = {**cab, "nivel": 2, "ptts": list(ptts_n2), "cobertura": _cobertura(el, feitos, herdados, set(orc.pulados)),
                 "cobertura_rodizio": cobertura_rodizio(el, feitos, herdados, date_str, set(orc.pulados)),
                 "falhas": _falhas_para_gravar(ant, falhou, feitos, vivos, date_str), "vizinhos": vizinhos}
        resumo["nivel2"] = {"elegiveis": len(el), "consultados": len(feitos), "falhas": falhas, "herdados": len(herdados)}
        tentados_total += tentados
        falhas_total += falhas
    if 3 in niveis:                       # sem orçamento sobrando o documento sai só com os vizinhos herdados (a coleta anterior não se perde)
        el = elegiveis(rs_doc, 3, ptts_n3)
        ant_d, ant = _anterior(base, date_str, "rs_communities.json.gz")
        feitos, tentados, falhas, falhou = _consultar_lote(client, log, dormir, orc, "received", ordem_do_rodizio(el, ant), dic, amostra, lim)
        herdados = _herdar(ant, feitos, vivos, date_str)
        vizinhos = sorted([*feitos.values(), *herdados], key=lambda v: (v["ixp"], v["afi"], v["asn"], v["ip"]))
        c_doc = {**cab, "nivel": 3, "ptts": list(ptts_n3), "cobertura": _cobertura(el, feitos, herdados, set(orc.pulados)),
                 "cobertura_rodizio": cobertura_rodizio(el, feitos, herdados, date_str, set(orc.pulados)),
                 "falhas": _falhas_para_gravar(ant, falhou, feitos, vivos, date_str), "vizinhos": vizinhos}
        resumo["nivel3"] = {"elegiveis": len(el), "consultados": len(feitos), "falhas": falhas, "herdados": len(herdados)}
        tentados_total += tentados
        falhas_total += falhas
    resumo["requisicoes"] = orc.usadas
    resumo["tentados"], resumo["falhas"] = tentados_total, falhas_total
    resumo["segundos"] = round(orc.relogio() - orc.t0, 1)
    resumo["rs_pulados"] = list(orc.pulados.values())
    for doc in (f_doc, c_doc):
        if doc:
            doc["requisicoes_da_rodada"] = orc.usadas
            doc["orcamento"] = orcamento
            doc["segundos_da_rodada"] = resumo["segundos"]
            doc["tempo_por_rs"] = orc.resumo_tempo()
            doc["rs_pulados"] = list(orc.pulados.values())
    return f_doc, c_doc, resumo


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, dormir: Callable[[float], None] = time.sleep, **kw) -> dict:
    destino = normalized_path(base, date_str, "summary")
    if not (destino / "rs_sessions.json.gz").exists():
        raise RuntimeError("ixbr_alice_rotas: rs_sessions.json.gz ausente (rode o ixbr_alice antes)")
    rs_doc = read_json_gz(destino / "rs_sessions.json.gz")
    comm_doc = read_json_gz(destino / "ixbr_communities.json.gz") if (destino / "ixbr_communities.json.gz").exists() else {}
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    try:
        f_doc, c_doc, resumo = coletar(rs_doc, comm_doc, base, date_str, client, log, dormir, **kw)  # type: ignore[arg-type]
    finally:
        if proprio:
            client.close()
    if f_doc is not None:
        write_json_gz(destino / "rs_filtered.json.gz", f_doc)
    if c_doc is not None:
        write_json_gz(destino / "rs_communities.json.gz", c_doc)
    log.info("ixbr_alice_rotas written", **{k: v for k, v in resumo.items() if not isinstance(v, (dict, list))}, nivel2=resumo.get("nivel2"), nivel3=resumo.get("nivel3"))
    if resumo["tentados"] and resumo["falhas"] > MAX_FALHA * resumo["tentados"]:
        raise RuntimeError(f"ixbr_alice_rotas: {resumo['falhas']} de {resumo['tentados']} vizinhos falharam")
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rotas rejeitadas e communities nos route servers do IX.br (Alice-LG, níveis 2 e 3)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    p.add_argument("--niveis", default=None, help="níveis a coletar, ex. 2 ou 2,3 (padrão: ARANDU_ALICE_NIVEIS)")
    p.add_argument("--orcamento", type=int, default=None, help="requisições por rodada (padrão: ARANDU_ALICE_ORCAMENTO)")
    p.add_argument("--ptts-n3", default=None, help="PTTs do nível 3, ex. df ou sp,rj (padrão: ARANDU_ALICE_PTTS_N3)")
    p.add_argument("--ptts-n2", default=None, help="PTTs do nível 2, ex. df,rj (padrão: ARANDU_ALICE_PTTS_N2, todos)")
    p.add_argument("--tempo-max", type=float, default=None, help="limite de tempo da rodada, em segundos (padrão: ARANDU_ALICE_TEMPO_MAX_S)")
    a = p.parse_args(argv)
    kw: dict = {}
    if a.niveis:
        kw["niveis"] = tuple(int(x) for x in a.niveis.split(","))
    if a.orcamento is not None:
        kw["orcamento"] = a.orcamento
    if a.ptts_n3:
        kw["ptts_n3"] = tuple(x.strip().lower() for x in a.ptts_n3.split(","))
    if a.ptts_n2:
        kw["ptts_n2"] = tuple(x.strip().lower() for x in a.ptts_n2.split(","))
    if a.tempo_max is not None:
        kw["tempo_max_s"] = a.tempo_max
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, **kw))
    except Exception:
        log.exception("falha na coleta de ixbr_alice_rotas")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
