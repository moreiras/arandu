# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Testador de carga: visitantes da web, assistentes no MCP, clientes da API e um abusivo, ao mesmo tempo, em degraus de usuários.

Rode pelo `tests/carga/rodar.sh` (amostrador no servidor, canário e relatório). Direto: `CARGA_CENARIO=fumaca locust -f
tests/carga/locustfile.py --host http://HOST --headless`. Cenários em `cenarios.yaml`; páginas gravadas por `gravar_paginas.js`.

Cada usuário virtual tem um IP próprio (198.18.0.0/15, faixa de testes da RFC 2544) no `X-Forwarded-For`: o alvo tem de confiar no
cabeçalho vindo do gerador (ver README.md), senão todos dividem um orçamento e o teste mede o limite, não a capacidade.
"""
from __future__ import annotations

import bisect
import csv
import ipaddress
import itertools
import json
import os
import random
import threading
import time
import urllib.request
from pathlib import Path

import gevent
import yaml
from gevent.pool import Pool
from locust import LoadTestShape, between, events, task
from locust.contrib.fasthttp import FastHttpUser
from locust.runners import MasterRunner, WorkerRunner

AQUI = Path(__file__).resolve().parent
CENARIOS = yaml.safe_load((AQUI / "cenarios.yaml").read_text(encoding="utf-8"))
NOME = os.environ.get("CARGA_CENARIO", "fumaca")
if NOME not in CENARIOS["cenarios"]:
    raise SystemExit(f"cenário desconhecido: {NOME} (há: {', '.join(CENARIOS['cenarios'])})")
CEN = {**CENARIOS["padrao"], **CENARIOS["cenarios"][NOME]}
PAGINAS = json.loads(Path(os.environ.get("CARGA_PAGINAS", AQUI / "saida" / "paginas.json")).read_text(encoding="utf-8"))["paginas"]
SAIDA = Path(os.environ.get("CARGA_SAIDA", AQUI / "saida" / "avulso"))
XFF_SETUP = os.environ.get("CARGA_XFF_SETUP", "127.0.0.1")         # IP da allowlist do alvo, só para montar os conjuntos de entidades
REDE_TESTE = ipaddress.ip_network("198.18.0.0/16")             # usuários; 198.19.240.0/20 é do canário e 198.19.255.254 do abusivo
IP_ABUSIVO = "198.19.255.254"

# ── chamadas comuns a toda página (carga inicial do app): na navegação dentro do app não se repetem ───────────────────────────────
_contagem: dict = {}
for _p in PAGINAS.values():
    for _u in {r["url"] for r in _p["requisicoes"] if r["tipo"] == "api" and r["metodo"] == "GET"}:
        _contagem[_u] = _contagem.get(_u, 0) + 1
INICIAIS = {u for u, n in _contagem.items() if n >= 0.8 * len(PAGINAS)}


# ── conjuntos de entidades (uma vez por processo) ────────────────────────────────────────────────────────────────────────────────
class Conjuntos:
    _trava = threading.Lock()
    pronto = False

    @classmethod
    def carregar(cls, host: str) -> None:
        with cls._trava:
            if cls.pronto:
                return
            def get(p):
                req = urllib.request.Request(host + p, headers={"X-Forwarded-For": XFF_SETUP, "User-Agent": "arandu-carga/1"})
                return json.load(urllib.request.urlopen(req, timeout=120))
            n = int(CEN["paginas_de_entidades"])
            asns = list(itertools.chain.from_iterable(
                get(f"/api/v1/asns?limit=100&page={k}&br_only=true&sort_by=apnic_users&sort_desc=true")["items"] for k in range(1, n + 1)))
            ops = list(itertools.chain.from_iterable(get(f"/api/v1/acessos/operadoras?limit=100&page={k}")["items"] for k in range(1, n + 1)))
            pref = list(itertools.chain.from_iterable(get(f"/api/v1/prefixes?limit=100&page={k}")["items"] for k in range(1, n + 1)))
            mun = get("/api/v1/acessos/municipios")["items"]
            ixps = sorted(get("/api/v1/ixps")["ixps"], key=lambda x: -(x.get("asn_direct_union_count") or 0))
            cls.data = get("/health")["latest_snapshot"]
            # cada lista já vem da mais procurada para a menos (usuários, acessos, membros): o Zipf concentra no topo
            cls.asn = [{"asn": str(a["asn"]), "asn_cnpj": a.get("cnpj"), "nome": a.get("name") or ""} for a in asns]
            cls.operadora = [{"cnpj": o["cnpj"], "cnpj8": o["cnpj"][:8], "nome": o.get("nome") or o.get("razao_social") or ""} for o in ops]
            cls.prefixo = [{"prefixo": p["prefix"], "prefixo_asn": str(p["origin_asn"])} for p in pref if p.get("origin_asn")]
            cls.municipio = [{"ibge": str(m["ibge"]), "uf": m["uf"], "nome_municipio": m["nome"]} for m in mun]
            cls.ptt = [{"code": i["code"]} for i in ixps]
            cls.uf = [{"uf": u} for u in dict.fromkeys(m["uf"] for m in mun)]
            cls.pronto = True


def _zipf_cum(n: int, s: float) -> list:
    acc, cum = 0.0, []
    for k in range(1, n + 1):
        acc += 1.0 / (k ** s) if s > 0 else 1.0
        cum.append(acc)
    return cum


_CUM: dict = {}


def escolher(lista: list, s: float = None) -> dict:
    s = CEN["zipf"] if s is None else s
    cum = _CUM.setdefault((id(lista), s), _zipf_cum(len(lista), s))
    return lista[bisect.bisect_left(cum, random.random() * cum[-1])]


def entidade_para(nome_pagina: str) -> dict:
    """Valores para os marcadores de uma página: a entidade principal e as dependentes dela (CNPJ do ASN, ASN de origem do prefixo)."""
    v = {"data": Conjuntos.data}
    v.update(escolher(Conjuntos.asn)); v.update(escolher(Conjuntos.operadora)); v.update(escolher(Conjuntos.prefixo))
    v.update(escolher(Conjuntos.municipio)); v.update(escolher(Conjuntos.ptt))
    if nome_pagina == "uf":
        v.update(escolher(Conjuntos.uf))
    return v


def preencher(texto, valores: dict):
    if texto is None:
        return None
    for k, x in valores.items():
        if "{" + k + "}" in texto:
            if not x:
                return None                        # dependente ausente (ASN sem CNPJ): o navegador não faria a chamada
            texto = texto.replace("{" + k + "}", str(x))
    return texto


# ── IP por usuário ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
_seq = itertools.count(random.randrange(0, 2 ** 16) * 1)


def novo_ip() -> str:
    n = next(_seq) + os.getpid() * 4096
    if random.random() < float(CEN["ipv6"]):
        return f"2001:db8:{(n >> 16) & 0xffff:x}:{n & 0xffff:x}::1"     # um /64 por usuário
    return str(REDE_TESTE[2 + n % (REDE_TESTE.num_addresses - 4)])


def _falha(status: int, corpo_erro: str = "") -> str:
    if status == 0:
        return "conexao"
    if status == 429:
        return "429_limite"
    if status == 503:
        return "503_ocupada"
    if status >= 500:
        return f"{status}_erro"
    return corpo_erro


def _nome(url: str, tipo: str) -> str:
    if tipo == "tiles":
        return "web tiles"
    if tipo == "estatico":
        return "web estatico"
    return "web " + url.split("?")[0]


class Base(FastHttpUser):
    abstract = True
    concurrency = 6                             # conexões por usuário (como o navegador com HTTP/1.1)
    network_timeout = 60.0
    connection_timeout = 10.0

    def on_start(self):
        Conjuntos.carregar(self.host)
        self.ip = novo_ip()

    def h(self, extra=None):
        d = {"X-Forwarded-For": self.ip, "User-Agent": "arandu-carga/1 (teste de capacidade)"}
        d.update(extra or {})
        return d

    def pedir(self, metodo, url, nome, headers=None, corpo=None, ok_429=False) -> int:
        for tentativa in (1, 2):
            t = time.perf_counter()
            with self.client.request(metodo, url, name=nome, headers=self.h(headers), data=corpo, catch_response=True) as r:
                st = r.status_code or 0
                # conexão reaproveitada que o servidor já fechou por inatividade (keepalive_timeout): falha em menos de uma volta de
                # rede; o navegador repete sozinho, então repete-se uma vez e a tentativa perdida sai com outro nome
                if st == 0 and tentativa == 1 and time.perf_counter() - t < 1.0:
                    r.request_meta["name"] = "reconexao"
                    r.success()
                    continue
                if st == 429 and ok_429:
                    r.success()
                elif st == 0 or st == 429 or st >= 500:
                    r.failure(_falha(st))
                else:
                    r.success()                 # 404 de combinação sem dado é resposta válida (o app trata)
                return st
        return 0


# ── visitante da web ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
class Visitante(Base):
    """Uma visita: carga inicial do app numa página de entrada e navegação dentro dele, com leitura entre as páginas.
    Cache do navegador por usuário: estáticos, tiles e GETs da API não se repetem na mesma visita."""
    weight = 0

    def on_start(self):
        super().on_start()
        self.cache = set()

    @task
    def visita(self):
        if random.random() < CEN["visitante_novo"]:
            self.ip, self.cache = novo_ip(), set()
        pesos = CEN["paginas"]
        nomes = [n for n in pesos if n in PAGINAS]
        n_pag = random.randint(*CEN["paginas_por_visita"])
        for i in range(n_pag):
            nome = random.choices(nomes, weights=[pesos[n] for n in nomes])[0]
            self.pagina(nome, carga_inicial=(i == 0))
            if i < n_pag - 1:
                gevent.sleep(random.uniform(*CEN["pensar_pagina_s"]))
        gevent.sleep(random.uniform(*CEN["pausa_entre_visitas_s"]))

    def pagina(self, nome: str, carga_inicial: bool):
        v = entidade_para(nome)
        reqs = []
        for r in PAGINAS[nome]["requisicoes"]:
            if r["tipo"] in ("estatico", "tiles") and not CEN["estaticos"]:
                continue                        # atrás da Cloudflare quem serve é o cache dela (ver cenarios.yaml)
            if r["tipo"] == "documento" and not carga_inicial:
                continue                        # navegação dentro do app: o HTML não volta
            if r["url"] in INICIAIS and not carga_inicial:
                continue
            url = preencher(r["url"], v)
            if url is None:
                continue
            chave = (r["metodo"], url, r["range"])
            if r["metodo"] == "GET" and r["tipo"] != "documento" and chave in self.cache:
                continue
            reqs.append((r, url, chave))
        t0 = time.perf_counter()
        falhas = []

        def um(item):
            r, url, chave = item
            hdr = {"Range": r["range"]} if r["range"] else {}
            corpo = preencher(r["corpo"], v)
            if corpo:
                hdr["Content-Type"] = "application/json"
            st = self.pedir(r["metodo"], url, _nome(r["url"], r["tipo"]), headers=hdr, corpo=corpo)
            if st == 0 or st == 429 or st >= 500:
                falhas.append(st)
            elif r["metodo"] == "GET":
                self.cache.add(chave)

        doc = [x for x in reqs if x[0]["tipo"] == "documento"]
        for x in doc:                           # o HTML vem antes do resto
            um(x)
        pool = Pool(self.concurrency)
        pool.map(um, [x for x in reqs if x[0]["tipo"] != "documento"])
        ms = (time.perf_counter() - t0) * 1000
        events.request.fire(request_type="PAGINA", name=("carga " if carga_inicial else "nav ") + nome, response_time=ms,
                            response_length=len(reqs), exception=(Exception(f"{len(falhas)} falha(s): {sorted(set(falhas))}") if falhas else None),
                            context={})


# ── assistente no MCP ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _mcp_json(texto: str):
    texto = (texto or "").strip()
    if texto.startswith("{"):
        return json.loads(texto)
    for linha in texto.splitlines():
        if linha.startswith("data:"):
            return json.loads(linha[5:].strip())
    return None


QUERIES = [
    lambda v: {"collection": "asns", "filter": {"and": [{"field": "ixps_direct", "op": "contains", "value": v["code"]},
                                                        {"field": "ixps_direct", "op": "ncontains", "value": "sp"}]}, "limit": 50},
    lambda v: {"collection": "asns", "filter": {"field": "uf", "op": "eq", "value": v["uf"]}, "limit": 100},
    lambda v: {"collection": "asns", "near": {"place": v["nome_municipio"], "radius_km": 150}, "limit": 50},
    lambda v: {"collection": "operadoras", "filter": {"field": "uf_sede", "op": "eq", "value": v["uf"]}, "limit": 50},
    lambda v: {"collection": "acessos_municipio", "filter": {"field": "ibge", "op": "eq", "value": v["ibge"]}, "limit": 50},
    lambda v: {"collection": "asns", "group_by": ["uf"], "aggregate": [{"fn": "count"}]},
]

# (peso, tool, argumentos a partir da entidade sorteada)
TOOLS = [
    (10, "asn_detalhe", lambda v: {"asn": int(v["asn"])}),
    (10, "query", lambda v: random.choice(QUERIES)(v)),
    (5, "ixp_detalhe", lambda v: {"code": v["code"]}),
    (4, "asn_lista", lambda v: {"q": (v["nome"].split()[0] if v["nome"] else "telecom")[:12], "br_only": True, "limit": 20}),
    (4, "operadora_acessos", lambda v: {"cnpj": v["cnpj"]}),
    (4, "municipio_banda_larga", lambda v: {"ibge": v["ibge"]}),
    (3, "municipio_resolver", lambda v: {"place": v["nome_municipio"]}),
    (3, "operadora_resolver", lambda v: {"name": (v["nome"].split()[0] if v["nome"] else "claro")}),
    (3, "asn_interconexao", lambda v: {"asn": int(v["asn"])}),
    (2, "ixp_proximos", lambda v: {"code": v["code"], "radius_km": 300}),
    (2, "ixp_participantes", lambda v: {"code": v["code"], "visao": "peers", "afi": "v4"}),
    (2, "rota_prefixo", lambda v: {"prefix": v["prefixo"]}),
    (2, "operadora_ranking", lambda v: {"uf": v["uf"], "limit": 20}),
    (2, "historico_serie", lambda v: {"escopo": "uf:" + v["uf"]}),
    (2, "asn_rede", lambda v: {"asn": int(v["asn"])}),
    (1, "viz", lambda v: {"kind": "hilbert_v4"}),
]


class Assistente(Base):
    """Uma conversa: sessão nova, lista de tools, 5 a 20 chamadas com o tempo de o modelo pensar entre elas, sessão encerrada."""
    weight = 0

    def rpc(self, corpo: dict, nome: str):
        hdr = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if getattr(self, "sid", None):
            hdr["Mcp-Session-Id"] = self.sid
        with self.client.post("/mcp", name=nome, headers=self.h(hdr), data=json.dumps(corpo), catch_response=True) as r:
            st = r.status_code or 0
            if st == 0 or st == 429 or st >= 500:
                r.failure(_falha(st)); return None, r
            if st >= 400:
                r.failure(f"{st}"); return None, r
            if "id" not in corpo:
                r.success(); return None, r
            try:
                j = _mcp_json(r.text)
            except ValueError:
                r.failure("resposta ilegível"); return None, r
            if not j or "error" in j:
                r.failure("jsonrpc_erro"); return j, r
            if (j.get("result") or {}).get("isError"):
                txt = ((j["result"].get("content") or [{}])[0].get("text") or "").replace("Error executing tool ", "")
                if "sem login" in txt:          # anônimo pedindo o que exige conta: a política de acesso respondendo
                    r.request_meta["name"] = nome + " (exige login)"
                    r.success(); return j, r
                r.failure("tool_erro: " + txt[:50]); return j, r
            r.success()
            return j, r

    @task
    def conversa(self):
        self.sid = None
        if random.random() < CEN["visitante_novo"]:
            self.ip = novo_ip()
        j, r = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "arandu-carga", "version": "1"}}}, "mcp initialize")
        if j is None:
            gevent.sleep(random.uniform(*CEN["mcp_pausa_entre_conversas_s"])); return
        self.sid = r.headers.get("mcp-session-id") or r.headers.get("Mcp-Session-Id")
        self.rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, "mcp notifications/initialized")
        self.rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, "mcp tools/list")
        if random.random() < 0.5:
            self.rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "describe_schema", "arguments": {}}},
                     "mcp tool:describe_schema")
        pesos = [t[0] for t in TOOLS]
        for i in range(random.randint(*CEN["mcp_chamadas_por_conversa"])):
            gevent.sleep(random.uniform(*CEN["mcp_pensar_s"]))
            _, nome, args = random.choices(TOOLS, weights=pesos)[0]
            v = entidade_para("mcp")
            self.rpc({"jsonrpc": "2.0", "id": 10 + i, "method": "tools/call", "params": {"name": nome, "arguments": args(v)}},
                     f"mcp tool:{nome}")
        if self.sid:
            self.client.request("DELETE", "/mcp", name="mcp encerrar", headers=self.h({"Mcp-Session-Id": self.sid}))
        gevent.sleep(random.uniform(*CEN["mcp_pausa_entre_conversas_s"]))


# ── cliente da API (scripts) ─────────────────────────────────────────────────────────────────────────────────────────────────────
class ClienteApi(Base):
    weight = 0
    wait_time = between(0.5, 3)

    @task(4)
    def entidade(self):
        v = entidade_para("api")
        nome, alvo = random.choice([("asns/{asn}", f"/api/v1/asns/{v['asn']}"), ("ixps/{code}", f"/api/v1/ixps/{v['code']}"),
                                    ("operadoras/{cnpj}", f"/api/v1/operadoras/{v['cnpj']}"),
                                    ("municipios/{ibge}", f"/api/v1/municipios/{v['ibge']}"),
                                    ("prefixes/{prefixo}", f"/api/v1/prefixes/{v['prefixo']}")])
        self.pedir("GET", alvo, "api /api/v1/" + nome)

    @task(2)
    def lista(self):
        self.pedir("GET", f"/api/v1/asns?limit=100&page={random.randint(1, 20)}&br_only=true", "api /api/v1/asns (lista)")

    @task(2)
    def consulta(self):
        q = random.choice(QUERIES)(entidade_para("api"))
        col = q.pop("collection")
        self.pedir("POST", f"/api/v1/query/{col}", f"api /api/v1/query/{col}", headers={"Content-Type": "application/json"},
                   corpo=json.dumps(q))


# ── abusivo: um IP só, sem pausa, nas rotas caras (os limites devem barrá-lo sem afetar os demais) ─────────────────────────────────
class Abusivo(Base):
    weight = 0
    wait_time = between(0, 0.05)

    def on_start(self):
        super().on_start()
        self.ip = IP_ABUSIVO

    @task
    def martelar(self):
        v = entidade_para("abuso")
        if random.random() < 0.5:
            self.pedir("GET", f"/api/v1/asns/{v['asn']}/paths", "abuso /asns/{asn}/paths")
        else:
            self.pedir("POST", "/api/v1/map/query", "abuso /map/query", headers={"Content-Type": "application/json"},
                       corpo=json.dumps({"filter": {"field": "uf", "op": "eq", "value": v["uf"]}}))


CLASSES = {"visitante": Visitante, "assistente": Assistente, "api": ClienteApi, "abusivo": Abusivo}
for _k, _cls in CLASSES.items():
    _cls.weight = int(CEN["pesos"].get(_k, 0))


# ── degraus de usuários ──────────────────────────────────────────────────────────────────────────────────────────────────────────
class Degraus(LoadTestShape):
    """Sobe de degrau em degrau (`degraus`, `degrau_s`) e para no fim. Só as classes com peso > 0 entram."""

    def tick(self):
        t = self.get_run_time()
        k = int(t // CEN["degrau_s"])
        if k >= len(CEN["degraus"]):
            return None
        classes = [c for c in CLASSES.values() if c.weight > 0]
        return CEN["degraus"][k], CEN["taxa_de_entrada"], classes


# ── registro bruto de cada requisição (o relatório agrupa por degrau) ────────────────────────────────────────────────────────────
_arq = None
_esc = None


@events.test_start.add_listener
def _inicio(environment, **_):
    global _arq, _esc
    SAIDA.mkdir(parents=True, exist_ok=True)
    if not isinstance(environment.runner, WorkerRunner):
        (SAIDA / "inicio.json").write_text(json.dumps({"t0": time.time(), "cenario": NOME, "config": CEN}, ensure_ascii=False, indent=1))
    if not isinstance(environment.runner, MasterRunner):
        _arq = open(SAIDA / f"requisicoes-{os.getpid()}.csv", "w", newline="")
        _esc = csv.writer(_arq)
        _esc.writerow(["ts", "tipo", "nome", "ms", "tamanho", "falha"])


@events.request.add_listener
def _req(request_type, name, response_time, response_length, exception, **_):
    if _esc is not None:
        _esc.writerow([f"{time.time():.3f}", request_type, name, f"{response_time:.1f}", response_length or 0,
                       "" if exception is None else str(exception)[:60]])


@events.test_stop.add_listener
def _fim(environment, **_):
    if _arq is not None:
        _arq.flush()
        _arq.close()
