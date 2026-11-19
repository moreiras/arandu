# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Espaço IPv4 sem uso e hipóteses de uso por terceiros. Saída: `published/{date}/ipv4/{ips_sem_uso,uso_por_terceiros}.json.gz`.

Parte dos blocos IPv4 do Brasil no `delegated` (alocados/atribuídos), da tabela de origens do snapshot (`origin-prefixes-v4`), dos ROAs (`rpki/vrp_list`) e do cadastro de ASN.

`ips_sem_uso`: cada bloco ganha uma classe (`anunciado`, `parcial`, `roa_sem_anuncio`, `nao_anunciado`, `em_recuperacao`) e, para os não anunciados, **quantas tabelas de origem distintas seguidas** sem
anúncio foram observadas (a tabela é semanal; só as que temos; antes disso, desconhecido). **"Não anunciado" não é "sem uso"**: rede interna, enlace ponto a ponto, reserva técnica e pool de CGNAT não aparecem na tabela global.

`uso_por_terceiros`: sinais que, juntos ou separados, **sugerem** que o bloco é usado por quem não é o titular. É hipótese, nunca "aluguel": cada sinal traz confiança e os falsos positivos conhecidos.
  S1 origem ≠ titular · S2 ROA de outro ASN · S3 bloco sem ASN titular anunciado por terceiro · S4 origem mudou sem transferência registrada (histórico)
  S5 geofeed divergente · S6 contato divergente · S7 rota em PTT novo: ainda não avaliados (sem coleta de geofeed por bloco, contatos não são públicos, o histórico não guarda PTT por prefixo).
"""
from __future__ import annotations

import bisect
import datetime as dt
import gzip
import ipaddress
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Optional

from core.common import normalized_path, now_iso, published_path
from core.ipv4_listas import faixa_para_cidrs, mascarar_nome
from core.jsonio import carregar_json, carregar_json_gz, gravar_json_gz
from products.ipv4.build import _documentos_asn, casar

TABELAS_DURACAO = 10                                # tabelas de origem distintas consultadas para trás (a tabela é semanal; ver `duracao_sem_anuncio`)
LIMITES = (
    "Não anunciado não é sem uso: rede interna, enlace ponto a ponto, reserva técnica e CGNAT não aparecem na tabela global. A duração só conta as tabelas de origem distintas que temos (a tabela é semanal). Os sinais de uso por "
    "terceiros são hipóteses com falsos positivos conhecidos (provedor que anuncia o bloco do cliente é o caso comum): não se afirma aluguel nem intenção, e a regra de cada sinal está visível."
)
SINAIS = {
    "S1": {"nome": "Origem diferente do titular", "avaliado": True, "falsos_positivos": "Provedor que anuncia o bloco de um cliente com ASN próprio ou sem ASN; organização do mesmo grupo com outro ASN; migração em curso."},
    "S2": {"nome": "ROA de outro ASN", "avaliado": True, "falsos_positivos": "ROA do provedor ou do grupo econômico; ROA preventivo para um ASN de contingência."},
    "S3": {"nome": "Bloco sem ASN titular anunciado por terceiro", "avaliado": True, "falsos_positivos": "Organização sem ASN que contrata trânsito: o provedor anuncia o bloco, o caso mais comum e legítimo."},
    "S4": {"nome": "Origem mudou sem transferência registrada", "avaliado": True, "falsos_positivos": "Troca de provedor de trânsito, fusão não registrada nas listas, correção de cadastro; a janela de confirmação do histórico reduz o ruído."},
    "S5": {"nome": "Geofeed divergente", "avaliado": False, "motivo": "Sem coleta de geofeed por bloco (só uma amostra de 35 bytes existe em ftp.registro.br/pub/geofeed)."},
    "S6": {"nome": "Contato divergente", "avaliado": False, "motivo": "Contatos de pessoa não são públicos nem servidos (política de privacidade)."},
    "S7": {"nome": "Rota em PTT novo", "avaliado": False, "motivo": "O histórico não guarda os PTTs por prefixo, só por ASN."},
}
NIVEIS = ("baixa", "media", "alta")


def _mascara(n: int) -> int:
    return (0xFFFFFFFF << (32 - n)) & 0xFFFFFFFF if n else 0


class Tabela:
    """Prefixos IPv4 com os ASNs de origem: cobertura de um bloco (fração de endereços e origens), por prefixo cobrindo e por mais específicos dentro do bloco."""

    def __init__(self, origem_por_prefixo: Iterable[tuple[str, int]]):
        por: dict[tuple[int, int], set[int]] = defaultdict(set)
        for p, a in origem_por_prefixo:
            n = ipaddress.ip_network(p, strict=False)
            if n.version == 4 and n.prefixlen >= 8:
                por[(int(n.network_address), n.prefixlen)].add(a)
        self.por = dict(por)
        self.starts = sorted(por)
        self._ini = [s for s, _ in self.starts]

    def cobertura(self, ini: int, fim: int) -> tuple[float, set[int]]:
        tam = fim - ini + 1
        plen = 32 - (tam - 1).bit_length() if tam & (tam - 1) == 0 else 32 - tam.bit_length()
        origens: set[int] = set()
        coberto = False
        for p in range(max(plen, 8), 7, -1):
            o = self.por.get((ini & _mascara(p), p))
            if o:
                coberto = True
                origens |= o
        i0, i1 = bisect.bisect_left(self._ini, ini), bisect.bisect_right(self._ini, fim)
        faixas = []
        for k in range(i0, i1):
            s, p = self.starts[k]
            e = s + (1 << (32 - p)) - 1
            if e <= fim:
                faixas.append((s, e))
                origens |= self.por[(s, p)]
        if coberto:
            return 1.0, origens
        soma, ult = 0, -1
        for s, e in sorted(faixas):
            s = max(s, ult + 1)
            if e >= s:
                soma += e - s + 1
                ult = e
        return min(1.0, soma / tam), origens


class Roas:
    def __init__(self, vrps: list[dict]):
        por: dict[tuple[int, int], set[int]] = defaultdict(set)
        for v in vrps:
            try:
                n = ipaddress.ip_network(v["prefix"], strict=False)
            except (ValueError, KeyError):
                continue
            if n.version == 4:
                por[(int(n.network_address), n.prefixlen)].add(int(v["asn"]))
        self.por = dict(por)
        self._ini = sorted(s for s, _ in self.por)
        self._pl = defaultdict(list)
        for (s, p) in self.por:
            self._pl[s].append(p)

    def asns(self, ini: int, fim: int) -> set[int]:
        tam = fim - ini + 1
        plen = 32 - (tam - 1).bit_length() if tam & (tam - 1) == 0 else 32 - tam.bit_length()
        out: set[int] = set()
        for p in range(max(plen, 8), 7, -1):
            out |= self.por.get((ini & _mascara(p), p), set())
        for k in range(bisect.bisect_left(self._ini, ini), bisect.bisect_right(self._ini, fim)):
            for p in self._pl[self._ini[k]]:
                if self._ini[k] + (1 << (32 - p)) - 1 <= fim:
                    out |= self.por[(self._ini[k], p)]
        return out


def _intervalo(b: dict) -> tuple[int, int]:
    i = int(ipaddress.IPv4Address(b["inicio"]))
    return i, i + b["quantidade"] - 1


def _sobe(n: str) -> str:
    return NIVEIS[min(NIVEIS.index(n) + 1, 2)]


def classificar(blocos: list[dict], tab: Tabela, roas: Roas, idx: dict[str, dict], recuperacao: list[ipaddress.IPv4Network], relacionados: set[tuple[int, int]],
                cnpj_por_asn: dict[int, str], mudancas: list[dict], transferencias: list[dict], eventos: list[dict]) -> list[dict]:
    """Uma linha por bloco do Brasil (alocado/atribuído) com classe, titular, origens, ROAs e sinais."""
    out = []
    for b in blocos:
        ini, fim = _intervalo(b)
        pct, origens = tab.cobertura(ini, fim)
        roa = roas.asns(ini, fim)
        hit = next((h for h in (casar(c, idx) for c in faixa_para_cidrs(b["inicio"], b["quantidade"])) if h), None)
        rec = any(ipaddress.ip_network(c).overlaps(n) for c in faixa_para_cidrs(b["inicio"], b["quantidade"]) for n in recuperacao)
        classe = "em_recuperacao" if rec else "anunciado" if pct >= 0.99 else "parcial" if pct > 0 else "roa_sem_anuncio" if roa else "nao_anunciado"
        titular = {"asn": hit["asn"], "org": mascarar_nome(hit["org"] or "", "BR") if hit.get("org") else None, "cnpj": hit.get("cnpj")} if hit else None
        sinais = []
        if titular and origens and titular["asn"] not in origens:                                                    # S1
            rel = any((titular["asn"], o) in relacionados or (o, titular["asn"]) in relacionados or (cnpj_por_asn.get(o) and cnpj_por_asn.get(o) == titular["cnpj"]) for o in origens)
            sinais.append({"id": "S1", "confianca": "baixa" if rel else "media", "evidencia": f"anunciado por AS{', AS'.join(str(o) for o in sorted(origens)[:4])}, titular AS{titular['asn']}" + (" (relacionados na tabela de relações ou no mesmo CNPJ)" if rel else "")})
        if roa and titular and titular["asn"] not in roa:                                                              # S2
            rel = all((titular["asn"], o) in relacionados or (o, titular["asn"]) in relacionados for o in roa)
            sinais.append({"id": "S2", "confianca": "baixa" if rel else "media", "evidencia": f"ROA para AS{', AS'.join(str(o) for o in sorted(roa)[:4])}, titular AS{titular['asn']}"})
        if not titular and origens:                                                                                    # S3
            estrangeiro = any(o not in cnpj_por_asn for o in origens)
            sinais.append({"id": "S3", "confianca": "media" if estrangeiro else "baixa", "evidencia": f"sem ASN titular; anunciado por AS{', AS'.join(str(o) for o in sorted(origens)[:4])}"})
        nets = [ipaddress.ip_network(c) for c in faixa_para_cidrs(b["inicio"], b["quantidade"])]
        for m in mudancas:                                                                                             # S4
            if m["_i0"] <= fim and m["_i1"] >= ini:
                d0 = dt.date.fromisoformat(m["data"])
                perto = lambda d: abs((dt.date.fromisoformat(d) - d0).days) <= 45                                      # noqa: E731
                com_transferencia = any(perto(t["data"]) and any(ipaddress.ip_network(x).overlaps(n) for x in t["blocos"] if ":" not in x for n in nets) for t in transferencias)
                com_titularidade = any(e["tipo"] == "titularidade" and perto(e["data"]) and e["_i0"] <= fim and e["_i1"] >= ini for e in eventos)
                if not (com_transferencia or com_titularidade):
                    sinais.append({"id": "S4", "confianca": "media", "evidencia": f"origem AS{m['de']} → AS{m['para']} em {m['data']} sem transferência nem mudança de titularidade em ±45 dias"})
                    break
        conf = None
        if sinais:
            conf = max((s["confianca"] for s in sinais), key=NIVEIS.index)
            if len(sinais) >= 2:
                conf = _sobe(conf)
        out.append({"inicio": b["inicio"], "quantidade": b["quantidade"], "status": b["status"], "ano_registro": (b.get("data") or "")[:4] or None, "classe": classe, "anunciado_pct": round(100 * pct, 1),
                    "origens": sorted(origens)[:8], "roa_asns": sorted(roa)[:8], "titular": titular, "sinais": sinais, "confianca": conf})
    return out


def anunciado_em(dados: dict, blocos: list[dict]) -> list[bool]:
    """Para cada bloco, se havia anúncio na tabela de origens `dados` ({asn: [prefixos]})."""
    tab = Tabela((p, int(a)) for a, ps in dados.items() for p in ps)
    return [tab.cobertura(*_intervalo(b))[0] > 0 for b in blocos]


def duracao_sem_anuncio(base: Path, date_str: str, blocos: list[dict], linhas: list[dict]) -> dict:
    """Tabelas de origem **distintas** seguidas sem anúncio, só para os blocos de hoje não anunciados. A tabela é semanal e os snapshots diários a reaproveitam: contar snapshots superestimaria
    a duração, então cada conteúdo distinto conta uma vez (identificado pelo hash do arquivo). Só entram as tabelas que temos."""
    import hashlib
    cand = [i for i, l in enumerate(linhas) if l["classe"] in ("nao_anunciado", "roa_sem_anuncio")]
    for i in cand:
        linhas[i]["tabelas_sem_anuncio"], linhas[i]["sem_anuncio_desde"] = 1, date_str
    raiz = base / "normalized"
    ant = sorted((p.name for p in raiz.iterdir() if p.is_dir() and p.name < date_str and (p / "summary" / "origin-prefixes-v4.json.gz").exists()), reverse=True) if raiz.exists() else []
    atual = hashlib.sha256((raiz / date_str / "summary" / "origin-prefixes-v4.json.gz").read_bytes()).hexdigest() if (raiz / date_str / "summary" / "origin-prefixes-v4.json.gz").exists() else None
    hashes = {d: hashlib.sha256((raiz / d / "summary" / "origin-prefixes-v4.json.gz").read_bytes()).hexdigest() for d in ant}
    primeira: dict[str, str] = {}                      # primeira data (mais antiga) em que cada conteúdo aparece como snapshot
    for d in ant:                                       # ordem decrescente: o último que sobra é o mais antigo
        primeira[hashes[d]] = d
    vistos = {atual}
    vivos = set(cand)
    usadas = []
    for d in ant:
        if not vivos or len(usadas) >= TABELAS_DURACAO:
            break
        h = hashes[d]
        if h in vistos:
            continue
        vistos.add(h)
        dados = carregar_json_gz(raiz / d / "summary" / "origin-prefixes-v4.json.gz")
        if not dados:
            continue
        ordem = sorted(vivos)
        r = anunciado_em(dados, [blocos[i] for i in ordem])
        usadas.append(d)
        for i, anunciado in zip(ordem, r):
            if anunciado:
                vivos.discard(i)
            else:
                linhas[i]["tabelas_sem_anuncio"] += 1
                linhas[i]["sem_anuncio_desde"] = primeira[h]
    return {"tabelas_anteriores_consultadas": usadas, "maximo_de_tabelas": TABELAS_DURACAO + 1}


def resumo(linhas: list[dict], uf_por_asn: dict[int, str]) -> dict:
    por_classe: dict[str, dict] = {}
    por_uf: dict[str, dict] = defaultdict(lambda: {"blocos": 0, "enderecos": 0, "nao_anunciado": 0})
    top: Counter = Counter()
    nomes: dict[int, str] = {}
    for l in linhas:
        c = por_classe.setdefault(l["classe"], {"blocos": 0, "enderecos": 0})
        c["blocos"] += 1
        c["enderecos"] += l["quantidade"]
        t = l["titular"]
        uf = uf_por_asn.get(t["asn"]) if t else None
        u = por_uf[uf or "sem_asn"]
        u["blocos"] += 1
        u["enderecos"] += l["quantidade"]
        if l["classe"] in ("nao_anunciado", "roa_sem_anuncio"):
            u["nao_anunciado"] += l["quantidade"]
            if t:
                top[t["asn"]] += l["quantidade"]
                nomes[t["asn"]] = t["org"] or ""
    total = sum(l["quantidade"] for l in linhas) or 1
    return {"total_blocos": len(linhas), "total_enderecos": total if linhas else 0, "por_classe": dict(sorted(por_classe.items())), "por_uf": dict(sorted(por_uf.items())),
            "maiores_titulares_nao_anunciado": [{"asn": a, "org": nomes[a], "enderecos": e} for a, e in top.most_common(10)]}


def _carregar_mudancas(base: Path, ate: str) -> list[dict]:
    pasta = base / "history" / "events"
    out = []
    if pasta.exists():
        for f in sorted(pasta.glob("*.jsonl.gz")):
            for ln in gzip.decompress(f.read_bytes()).decode().splitlines():
                e = json.loads(ln) if ln else {}
                if e.get("tipo") == "mudanca_origem" and e.get("estado") in (None, "confirmado") and e["data"] <= ate and e.get("entidade", "").startswith("prefixo:"):
                    try:
                        n = ipaddress.ip_network(e["entidade"][8:], strict=False)
                    except ValueError:
                        continue
                    if n.version == 4:
                        out.append({"data": e["data"], "de": e.get("de"), "para": e.get("para"), "_i0": int(n.network_address), "_i1": int(n.broadcast_address)})
    return out


def publicar_ipv4_uso(base: Path, date_str: str, log) -> dict:
    from sources.ipv4_delegated.enrich import carregar_estado, todos_eventos
    norm = normalized_path(base, date_str, "summary")
    pub = published_path(base, date_str)
    estado = carregar_estado(base)
    origin = carregar_json_gz(norm / "origin-prefixes-v4.json.gz")
    if not estado or not origin:
        log.info("estado do delegated ou tabela de origens ausentes: espaço sem uso não gerado")
        return {}
    listas = carregar_json_gz(norm / "ipv4_listas.json.gz") or {}
    blocos = sorted((b for b in estado["blocos"].values() if b.get("cc") == "BR" and b["status"] in ("allocated", "assigned")), key=lambda b: int(ipaddress.IPv4Address(b["inicio"])))
    idx, cnpj_por_asn, uf_por_asn = {}, {}, {}
    for asn, d in _documentos_asn(base, date_str):
        if d.get("is_br"):
            cnpj_por_asn[int(asn)] = d.get("cnpj") or ""
            for pfx in d.get("rir_prefixes_v4") or []:
                idx.setdefault(pfx, {"asn": asn, "org": d.get("name"), "cnpj": d.get("cnpj")})
    geo = carregar_json_gz(norm / "geo_orgs.json.gz") or {}
    for a, o in (geo.get("orgs") or {}).items():
        if o.get("uf"):
            uf_por_asn[int(a)] = o["uf"]
    rel = carregar_json_gz(pub / "as_relationships.json.gz") or {}
    relacionados = {(int(r["a"]), int(r["b"])) for r in rel.get("relacoes", [])}
    vrps = carregar_json_gz(pub / "rpki" / "vrp_list.json.gz") or []
    recup = [ipaddress.ip_network(r["recurso"]) for r in listas.get("recuperacao", []) if r["tipo"] == "bloco"]
    tab = Tabela((p, int(a)) for a, ps in origin.items() for p in ps)
    evs = []
    for e in todos_eventos(base):
        if e["data"] <= date_str and e["tipo"] == "titularidade":
            i0 = int(ipaddress.IPv4Address(e["inicio"]))
            evs.append({**e, "_i0": i0, "_i1": i0 + e["quantidade"] - 1})
    linhas = classificar(blocos, tab, Roas(vrps), idx, recup, relacionados, cnpj_por_asn, _carregar_mudancas(base, date_str), listas.get("transferencias_registrobr", []), evs)
    dur = duracao_sem_anuncio(base, date_str, blocos, linhas)
    r = resumo(linhas, uf_por_asn)
    destino = pub / "ipv4"
    destino.mkdir(parents=True, exist_ok=True)
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "natureza": "inferido", "fonte": "Registro.br e LACNIC (delegated), tabela de origens do snapshot e ROAs", "limites": LIMITES, "ultima_foto": estado["dia"]}
    gravar_json_gz(destino / "ips_sem_uso.json.gz", {**meta, "resumo": r, "duracao": dur, "colunas": ["inicio", "quantidade", "classe", "anunciado_pct", "asn", "org", "cnpj", "uf", "tabelas_sem_anuncio", "sem_anuncio_desde", "ano_registro", "roa_asns"],
                                                     "blocos": [[l["inicio"], l["quantidade"], l["classe"], l["anunciado_pct"], (l["titular"] or {}).get("asn"), (l["titular"] or {}).get("org"), (l["titular"] or {}).get("cnpj"),
                                                                 uf_por_asn.get((l["titular"] or {}).get("asn")), l.get("tabelas_sem_anuncio"), l.get("sem_anuncio_desde"), l["ano_registro"], l["roa_asns"]]
                                                                for l in linhas if l["classe"] != "anunciado"]})
    com = [l for l in linhas if l["sinais"]]
    cont = Counter(s["id"] for l in com for s in l["sinais"])
    gravar_json_gz(destino / "uso_por_terceiros.json.gz", {**meta, "rotulo": "hipótese de uso por terceiros", "sinais": SINAIS, "por_sinal": dict(cont), "por_confianca": dict(Counter(l["confianca"] for l in com)),
                                                          "blocos_avaliados": len(linhas), "total": len(com),
                                                          "itens": sorted(com, key=lambda l: (-NIVEIS.index(l["confianca"]), -len(l["sinais"]), -l["quantidade"]))})
    log.info("ipv4_uso written", blocos=len(linhas), com_sinal=len(com), **{k.replace("/", "_"): v["blocos"] for k, v in r["por_classe"].items()})
    return {"blocos": len(linhas), "com_sinal": len(com), "por_classe": {k: v["blocos"] for k, v in r["por_classe"].items()}, "por_sinal": dict(cont)}
