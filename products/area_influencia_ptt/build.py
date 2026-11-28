# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Área de influência observada de cada PTT do IX.br: a que distância atuam as operadoras que aparecem nele.

Entradas em `published/{date}/`: `sici_municipios.json.gz` (acessos fixos por município e CNPJ, com os ASNs de cada CNPJ), `ixps/index.json` (PTTs) e os
documentos de ASN (`ixp_presence`: sessão direta e prefixos próprios vistos em cada PTT); em `config/`, `pix.yaml` (locais dos PIX) e
`municipios-centroides.json`. Saída: `territorio/area_influencia_ptt.json.gz`.

Quatro visões por PTT. Duas da participação de um ASN no PTT (com disputa entre PTTs):
  * `diretos`: o ASN tem sessão própria no PTT E prefixo próprio visto nele;
  * `todos`: o ASN tem prefixo próprio visto no PTT, com sessão ou levado por outro participante. `diretos` está contido em `todos`.

Método (INFERIDO, não é cobertura de rede):
  * a operadora é o CNPJ do SICI; ela enxerga os PTTs de todos os ASNs ligados ao CNPJ (a ligação é a do SICI, `operadores[].asns`). A unidade de contagem é o
    par (município, CNPJ): um CNPJ com vários ASNs soma os PTTs deles e conta os acessos uma vez só;
  * os acessos de cada par (município, CNPJ) vão para o PTT mais próximo entre os que a operadora enxerga na visão (cada acesso conta uma vez);
  * distância: linha reta (geodésica) do centroide do município ao PIX mais próximo do PTT. PIX sem coordenada em `config/pix.yaml` vai para o centroide do município do
    endereço; sem endereço reconhecível, para o da sede do PTT (o produto diz quais PTTs caíram nessa regra);
  * sem exclusão de operadoras;
  * P50, P80 e P90 da distância ponderados por acessos, por PTT e visão; ao lado, a mediana por operadora (cada operadora conta 1), que mede outra população;
  * faixas por município em cada PTT: 1 = até o P50, 2 = acima do P50 até o P80, 3 = acima do P80;
  * visões de alcance, só por PTT e fora do índice nacional: `alcance_diretos` e `alcance_todos` usam a mesma participação de `diretos` e `todos`, mas sem disputa. Todo par (município, CNPJ)
    cuja operadora está no PTT entra no alcance dele, ainda que outro PTT seja mais próximo; os percentis e as faixas pesam pelos acessos desse alcance total. Os acessos de um município
    contam em cada PTT de alcance (não se somam entre PTTs). O alcance de um PTT contém a influência provável dele na mesma visão.

Uso:
    python -m products.area_influencia_ptt.build --date 2026-11-22
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Optional

import yaml

from core import compose
from core.common import configure_logging, data_dir, now_iso, published_path, today_str
from core.geoip import normaliza
from core.jsonio import carregar_json_gz

_CONFIG = Path(__file__).resolve().parent.parent.parent / "config"
RAIO_TERRA_KM = 6371.0088
VISOES = ("diretos", "todos")
VISOES_ALCANCE = ("alcance_diretos", "alcance_todos")                    # só por PTT (não entram no índice nacional por município)
VISOES_PTT = VISOES + VISOES_ALCANCE
_BASE_ALCANCE = {"alcance_diretos": "diretos", "alcance_todos": "todos"}
QUANTIS = (("p50_km", 0.50), ("p80_km", 0.80), ("p90_km", 0.90))
FAIXAS = {1: "ate_p50", 2: "p50_a_p80", 3: "alem_p80"}
ORIGENS_PIX = ("coordenada", "endereco", "sede")
LIMITES = (
    "Inferência, não cobertura de rede. Mostra onde as operadoras que aparecem no PTT declaram acessos de banda larga fixa ao SICI (mês de referência diferente da data do snapshot), "
    "com cada par (município, operadora) atribuído ao PTT mais próximo entre os que ela enxerga na visão. Não diz que a rede da operadora chega ao município nem que o tráfego passe pelo PTT. "
    "As visões de alcance (`alcance_diretos`, `alcance_todos`) não disputam: cada município onde uma operadora do PTT declara acessos entra no alcance do PTT, mesmo que exista PTT mais próximo, e o mesmo município pode estar no alcance de vários PTTs; nelas o P50, o P80 e o P90 pesam pelos acessos do alcance total. "
    "A distância é em linha reta, do centroide do município ao PIX mais próximo; PIX sem coordenada foi posicionado no centroide do município do endereço ou da sede do PTT. "
    "O CNPJ liga-se aos ASNs pelo cadastro do SICI (CNPJ do registro do ASN); operadora sem ASN ligado não entra, e um CNPJ com vários ASNs conta os acessos uma vez. Não há exclusão de operadoras. "
    "O P50, o P80 e o P90 pesam por acessos; a mediana por operadora conta cada operadora uma vez e mede outra população."
)
METODO = {
    "diretos": "ASN com sessão própria no PTT e prefixo próprio visto nele.",
    "todos": "ASN com prefixo próprio visto no PTT, com sessão ou levado por outro participante (inclui os diretos).",
    "alcance_diretos": "Alcance total, sem disputa entre PTTs: todos os municípios onde as operadoras diretamente conectadas a este PTT declaram acessos ao SICI, mesmo que haja outro PTT mais próximo onde elas também estão.",
    "alcance_todos": "Alcance total, sem disputa entre PTTs: o mesmo para todas as operadoras com prefixo próprio visto no PTT (diretas e indiretas). Um município pode estar no alcance de vários PTTs.",
    "atribuicao": "Os acessos de cada par (município, CNPJ) vão para o PTT mais próximo entre os que o CNPJ enxerga na visão (união dos PTTs dos ASNs ligados a ele); cada acesso conta uma vez.",
    "distancia": "Linha reta (geodésica) do centroide do município ao PIX mais próximo do PTT.",
    "percentis": "Menor distância cujo acumulado de acessos atinge a fração do total do PTT (P50, P80, P90).",
    "mediana_operadora": "Mediana, entre as operadoras do PTT, da distância mediana (por acessos) de cada uma; cada operadora conta 1.",
    "faixas": {"1": "até o P50 (onde atua a maioria)", "2": "acima do P50 até o P80 (quase todos)", "3": "acima do P80 (os restantes)"},
}


# --- entradas -------------------------------------------------------------------------------------------------------------------------------

def carregar_centroides() -> dict[str, tuple[float, float]]:
    """{ibge: (lon, lat)} de `config/municipios-centroides.json` (substituído nos testes)."""
    try:
        bruto = json.loads((_CONFIG / "municipios-centroides.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {i: (c[0], c[1]) for i, c in bruto.items() if isinstance(c, list) and len(c) >= 2}


def carregar_pix() -> dict[str, list[dict]]:
    """{ptt: [{name, address, lat?, lon?}]} de `config/pix.yaml`, os locais dos PIX com e sem coordenada (substituído nos testes)."""
    try:
        cfg = yaml.safe_load((_CONFIG / "pix.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    out: dict[str, list[dict]] = {}
    for code, lista in (cfg.get("pix") or {}).items():
        itens = []
        for e in lista or []:
            if not isinstance(e, dict):
                continue
            item = {"name": str(e.get("name") or ""), "address": " ".join(str(e.get("address") or "").split())}
            if isinstance(e.get("lat"), (int, float)) and isinstance(e.get("lon"), (int, float)):
                item["lat"], item["lon"] = float(e["lat"]), float(e["lon"])
            itens.append(item)
        out[str(code)] = itens
    return out


def carregar_referencia() -> dict[str, tuple[str, str]]:
    """{ibge: (nome, uf)} de `config/municipios-referencia.json`, para casar o município do endereço de um PIX."""
    try:
        bruto = json.loads((_CONFIG / "municipios-referencia.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {i: (v[0], v[1]) for i, v in bruto.items() if isinstance(v, list) and len(v) >= 2}


def participacao_por_visao(documentos: Iterator[tuple[int, dict]], asns: set[int]) -> dict[str, dict[int, set[str]]]:
    """{visão: {asn: {ptt}}} a partir de `ixp_presence` dos ASNs pedidos.

    `diretos`: sessão direta (v4 ou v6) E prefixo próprio visto (v4 ou v6); `todos`: prefixo próprio visto, com sessão ou não."""
    out: dict[str, dict[int, set[str]]] = {v: defaultdict(set) for v in VISOES}
    for asn, doc in documentos:
        if asn not in asns:
            continue
        for ptt, pres in (doc.get("ixp_presence") or {}).items():
            familias = [pres.get(f) or {} for f in ("v4", "v6")]
            if not any(f.get("prefixes") for f in familias):
                continue
            out["todos"][asn].add(ptt)
            if any(f.get("direct") for f in familias):
                out["diretos"][asn].add(ptt)
    return out


def _documentos_asn(base: Path, date_str: str) -> Iterator[tuple[int, dict]]:
    """(asn, documento) com `ixp_presence`: do fragmento `base` no fluxo de fragmentos; senão, dos `asns/{asn}.json` publicados."""
    if compose.ativo() and compose.fluxo_novo(base, date_str):
        yield from compose.iterar_documentos(base, date_str, ("base",))
        return
    pub = published_path(base, date_str)
    idx = json.loads((pub / "asns" / "index.json").read_text(encoding="utf-8")) if (pub / "asns" / "index.json").exists() else []
    for e in idx:
        p = pub / "asns" / f"{e['asn']}.json"
        if p.exists():
            yield e["asn"], json.loads(p.read_text(encoding="utf-8"))


# --- cálculo --------------------------------------------------------------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(a))


def percentil(pares: list[tuple[float, float]], q: float) -> Optional[float]:
    """Menor valor cujo peso acumulado (em ordem crescente) atinge `q` do peso total. `pares` = [(valor, peso)]; `None` se vazio."""
    if not pares:
        return None
    pares = sorted(pares)
    total = sum(w for _, w in pares)
    acc = 0.0
    for v, w in pares:
        acc += w
        if acc >= q * total:
            return v
    return pares[-1][0]


_ENDERECO = re.compile(r"(?:^|[,\-])\s*([^,\-]+?)\s*-\s*([A-Z]{2})\s*$")      # "..., Cidade - UF" ou "... - Cidade - UF" no fim do endereço


def posicionar_pix(cadastro: dict[str, list[dict]], ptts: dict[str, dict], centroides: dict[str, tuple[float, float]], por_nome: dict[tuple[str, str], str]
                   ) -> dict[str, list[tuple[float, float, str]]]:
    """{ptt: [(lat, lon, origem)]} com a origem `coordenada`, `endereco` (centroide do município do endereço) ou `sede` (centroide da sede do PTT).

    PTT sem nenhum PIX no cadastro recebe um ponto só, na sede. Município sem centroide não gera ponto."""
    sede = {c: por_nome.get((normaliza(p.get("name") or ""), p.get("uf") or "")) for c, p in ptts.items()}
    pix: dict[str, list[tuple[float, float, str]]] = {}
    for code in ptts:
        pts: list[tuple[float, float, str]] = []
        for e in cadastro.get(code) or [{"name": "", "address": ""}]:
            if "lat" in e and "lon" in e:
                pts.append((e["lat"], e["lon"], "coordenada"))
                continue
            ibge, origem = None, "endereco"
            m = _ENDERECO.search(e.get("address") or "")
            if m:
                ibge = por_nome.get((normaliza(m.group(1)), m.group(2)))
            if not ibge or ibge not in centroides:
                ibge, origem = sede.get(code), "sede"
            if ibge and ibge in centroides:
                lon, lat = centroides[ibge]
                pts.append((lat, lon, origem))
        if pts:
            pix[code] = pts
    return pix


def _resumir_ptt(ptt: str, o: list[tuple[float, int, str, str]], dist) -> tuple[dict, dict[str, list[int]]]:
    """Resumo de um PTT numa visão a partir de `o` = [(km, acessos, ibge, cnpj)]: operadoras, municípios, acessos, P50/P80/P90, mediana por operadora e faixas.

    Devolve também `{ibge: [acessos, faixa]}`. A faixa de cada município vem da distância ao PIX do PTT (1 até o P50, 2 até o P80, 3 além)."""
    pares = [(x[0], float(x[1])) for x in o]
    por_op: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for km, ac, _, cnpj in o:
        por_op[cnpj].append((km, float(ac)))
    medianas = [(percentil(v, 0.5), 1.0) for v in por_op.values()]
    r: dict = {"operadoras": len(por_op), "acessos": sum(x[1] for x in o), "municipios": len({x[2] for x in o})}
    for nome, q in QUANTIS:
        r[nome] = round(percentil(pares, q), 1)
    r["mediana_operadora_km"] = round(percentil(medianas, 0.5), 1)
    acessos_mun: dict[str, int] = defaultdict(int)
    for _, ac, ibge, _ in o:
        acessos_mun[ibge] += ac
    faixas = {n: {"municipios": 0, "acessos": 0} for n in FAIXAS.values()}
    muns: dict[str, list[int]] = {}
    for ibge, ac in sorted(acessos_mun.items()):
        km = dist(ibge, ptt)
        f = 1 if km <= r["p50_km"] else 2 if km <= r["p80_km"] else 3
        muns[ibge] = [ac, f]
        faixas[FAIXAS[f]]["municipios"] += 1
        faixas[FAIXAS[f]]["acessos"] += ac
    r["faixas"] = faixas
    r["municipios_faixa"] = muns
    return r, muns


def calcular(municipios: dict[str, dict], centroides: dict[str, tuple[float, float]], participacao: dict[str, dict[int, set[str]]],
             pix: dict[str, list[tuple[float, float, str]]]) -> dict:
    """Atribui os acessos de cada (município, CNPJ) ao PTT mais próximo da visão e resume por PTT e por município.

    `municipios`: `municipios` de sici_municipios (cada um com `operadores`: cnpj, acessos, asns). Devolve `{visao: {"ptts": {...}, "municipios": {...}, "total": {...}}}`."""
    dist_cache: dict[tuple[str, str], float] = {}

    def dist(ibge: str, ptt: str) -> float:
        k = (ibge, ptt)
        if k not in dist_cache:
            lon, lat = centroides[ibge]
            dist_cache[k] = min(haversine_km(lat, lon, a, b) for a, b, _ in pix[ptt])
        return dist_cache[k]

    saida: dict[str, dict] = {}
    for visao in VISOES:
        part = participacao.get(visao) or {}
        obs: dict[str, list[tuple[float, int, str, str]]] = defaultdict(list)       # ptt -> [(km, acessos, ibge, cnpj)]
        total = {"acessos": 0, "acessos_atribuidos": 0, "acessos_sem_ptt": 0, "acessos_sem_centroide": 0}
        multi_asn: set[str] = set()
        for ibge, m in municipios.items():
            for op in m.get("operadores") or []:
                acessos = int(op.get("acessos") or 0)
                if acessos <= 0:
                    continue
                total["acessos"] += acessos
                if ibge not in centroides:
                    total["acessos_sem_centroide"] += acessos
                    continue
                asns = op.get("asns") or []
                if len(asns) > 1:
                    multi_asn.add(op["cnpj"])
                candidatos: set[str] = set()
                for a in asns:
                    candidatos |= part.get(int(a), set())
                candidatos = {p for p in candidatos if p in pix}
                if not candidatos:
                    total["acessos_sem_ptt"] += acessos
                    continue
                km, ptt = min((dist(ibge, p), p) for p in candidatos)
                obs[ptt].append((km, acessos, ibge, op["cnpj"]))
                total["acessos_atribuidos"] += acessos
        total["cnpjs_com_varios_asns"] = len(multi_asn)

        ptts: dict[str, dict] = {}
        por_mun: dict[str, dict[str, int]] = defaultdict(dict)                       # ibge -> {ptt: acessos}
        faixa_de: dict[tuple[str, str], int] = {}
        for ptt, o in sorted(obs.items()):
            r, muns = _resumir_ptt(ptt, o, dist)
            for ibge, (ac, f) in muns.items():
                faixa_de[(ibge, ptt)] = f
                por_mun[ibge][ptt] = ac
            ptts[ptt] = r

        indice: dict[str, list] = {}
        for ibge, d in por_mun.items():
            principal = min(d, key=lambda p: (-d[p], p))
            indice[ibge] = [principal, faixa_de[(ibge, principal)], d[principal], sum(d.values()), len(d)]
        saida[visao] = {"ptts": ptts, "municipios": dict(sorted(indice.items())), "total": total}

    for alcance, base in _BASE_ALCANCE.items():
        part = participacao.get(base) or {}
        obs_a: dict[str, list[tuple[float, int, str, str]]] = defaultdict(list)
        for ibge, m in municipios.items():
            if ibge not in centroides:
                continue
            for op in m.get("operadores") or []:
                acessos = int(op.get("acessos") or 0)
                if acessos <= 0:
                    continue
                candidatos: set[str] = set()
                for a in op.get("asns") or []:
                    candidatos |= part.get(int(a), set())
                for ptt in candidatos:
                    if ptt in pix:
                        obs_a[ptt].append((dist(ibge, ptt), acessos, ibge, op["cnpj"]))
        saida[alcance] = {"ptts": {ptt: _resumir_ptt(ptt, o, dist)[0] for ptt, o in sorted(obs_a.items())}}
    return saida


def montar(date_str: str, sici: dict, ptts_idx: list[dict], cadastro: dict[str, list[dict]], centroides: dict[str, tuple[float, float]],
           referencia: dict[str, tuple[str, str]], participacao: dict[str, dict[int, set[str]]]) -> dict:
    """O documento publicado: cabeçalho, PTTs (com as duas visões e o posicionamento dos PIX) e o índice nacional por município."""
    municipios = sici.get("municipios") or {}
    ptts = {e["code"]: e for e in ptts_idx if e.get("code")}
    por_nome: dict[tuple[str, str], str] = {}
    for ibge, (nome, uf) in referencia.items():
        por_nome[(normaliza(nome), uf)] = ibge
    for ibge, m in municipios.items():
        por_nome[(normaliza(m.get("nome") or ""), m.get("uf") or "")] = ibge
    pix = posicionar_pix(cadastro, ptts, centroides, por_nome)
    r = calcular(municipios, centroides, participacao, pix)
    saida_ptts: dict[str, dict] = {}
    aproximados: list[str] = []
    for code in sorted(ptts):
        origens = Counter(o for _, _, o in pix.get(code, []))
        aproximado = bool(origens["endereco"] or origens["sede"])
        if aproximado:
            aproximados.append(code)
        saida_ptts[code] = {
            "nome": ptts[code].get("name") or code, "uf": ptts[code].get("uf"),
            "pix": {"total": sum(origens.values()), **{o: origens[o] for o in ORIGENS_PIX}, "aproximado": aproximado,
                    "pontos": [[round(a, 4), round(b, 4), o] for a, b, o in pix.get(code, [])]},
            "visoes": {v: r[v]["ptts"].get(code) for v in VISOES_PTT},
        }
    ibges_nomes = {i for v in VISOES for i in r[v]["municipios"]} | {i for p in saida_ptts.values() for v in VISOES_ALCANCE if p["visoes"][v] for i in p["visoes"][v]["municipios_faixa"]}
    return {
        "snapshot_date": date_str, "generated_at": now_iso(), "natureza": "inferido", "limites": LIMITES, "metodo": METODO,
        "fontes": {"sici": sici.get("mes_referencia"), "ptts": "looking glasses do IX.br (snapshot)", "pix": "cadastro de PIX do IX.br (config/pix.yaml)", "centroides": "IBGE"},
        "faixas": {str(k): v for k, v in FAIXAS.items()},
        "ptts_com_pix_aproximado": aproximados,
        "totais": {v: r[v]["total"] for v in VISOES},
        "ptts": saida_ptts,
        "municipios": {v: r[v]["municipios"] for v in VISOES},
        "municipios_nomes": {i: f"{municipios[i].get('nome', '')}/{municipios[i].get('uf', '')}" for i in sorted(ibges_nomes)},
    }


def _gravar_atomico(destino: Path, doc: dict) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
        os.replace(tmp, destino)
    finally:
        if tmp.exists():
            tmp.unlink()


def publicar_area_influencia(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    sici = carregar_json_gz(pub / "sici_municipios.json.gz") or {}
    idx_p = pub / "ixps" / "index.json"
    if not sici.get("municipios") or not idx_p.exists():
        log.info("sici_municipios ou índice de PTTs ausentes: area_influencia_ptt não gerada")
        return {}
    ptts_idx = json.loads(idx_p.read_text(encoding="utf-8"))
    asns = {int(a) for m in sici["municipios"].values() for op in m.get("operadores") or [] for a in op.get("asns") or []}
    part = participacao_por_visao(_documentos_asn(base, date_str), asns)
    doc = montar(date_str, sici, ptts_idx, carregar_pix(), carregar_centroides(), carregar_referencia(), part)
    _gravar_atomico(pub / "territorio" / "area_influencia_ptt.json.gz", doc)
    n = {v: sum(1 for p in doc["ptts"].values() if p["visoes"][v]) for v in VISOES_PTT}
    log.info("area_influencia_ptt written", ptts_diretos=n["diretos"], ptts_todos=n["todos"], ptts_alcance_diretos=n["alcance_diretos"], ptts_alcance_todos=n["alcance_todos"], municipios=len(doc["municipios"]["todos"]),
             pix_aproximado=len(doc["ptts_com_pix_aproximado"]))
    return {"ptts": len(doc["ptts"]), "ptts_com_area": n, "municipios": {v: len(doc["municipios"][v]) for v in VISOES}}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Área de influência observada dos PTTs do IX.br")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; o produto é sempre recalculado")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        publicar_area_influencia(data_dir(), a.date, log)
    except Exception:
        log.exception("falha no cálculo da área de influência dos PTTs")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
