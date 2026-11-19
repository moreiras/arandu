# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Régua de validação do ARC: roda o algoritmo **sem o ASPA como entrada** e mede contra ele.

    python -m products.as_relationships.validacao --date 2026-10-24 [--ptts 4] [--coletores 3]

Saída: `data/ops/relacoes/AAAA-MM-DD.json` (não é publicada; o painel lê). Medidas:
  - precisão/recall dos provedores contra o ASPA (BR e global), por nível mínimo, e o CAIDA como referência;
  - calibração: nas faixas de `p`, a fração dos provedores previstos que o ASPA confirma (limite inferior: ASPA incompleto);
  - subconjuntos difíceis (Jin et al., NSDI 2019): VP-adjacente, poucos VPs, stub–clique, sem cobertura;
  - validação cruzada por PTT e retirada de coletores: queda de precisão/recall e estabilidade do conjunto previsto;
  - concordância (não acurácia) com o CAIDA e estabilidade entre snapshots consecutivos."""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Callable, Optional

from core.common import configure_logging, data_dir, normalized_path, published_path, read_json_gz, today_str
from products.as_relationships import arc, build, irr_relacao, refino, regua
from products.as_relationships.config import Config, carregar
from sources.fulltable_routeviews import caminhos as cm

FAIXAS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.0001)]


_irr_com_politicas = irr_relacao.com_politicas                 # alias: a função vive em irr_relacao, usada também pelo build


def _entradas(base: Path, date_str: str) -> dict:
    reg = read_json_gz(normalized_path(base, date_str, "summary") / "registro_br.json.gz")
    br = {int(a["asn"]) for a in reg.get("asns", [])}
    aspa_path = published_path(base, date_str, "rpki", "aspa_list.json.gz")
    caida_path = build._achar(base, date_str, "summary", "caida_asrel.json.gz")
    caida_doc = read_json_gz(caida_path) if caida_path else None
    irr_doc = _irr_com_politicas(base)
    return {"irr": irr_relacao.relacoes(irr_doc["politicas"]) if irr_doc else None,
            "irr_data": irr_doc["snapshot_date"] if irr_doc else None,
            "br": br, "aspa": read_json_gz(aspa_path) if aspa_path.exists() else [],
            "caida": (caida_doc["p2c"], caida_doc["p2p"]) if caida_doc else None,
            "grupos": {int(a["asn"]): str(a["cnpj"])[:8] for a in reg.get("asns", []) if a.get("cnpj") and len(str(a["cnpj"])) >= 8}}


def _rodar(base: Path, date_str: str, e: dict, cfg: Config, afi: str, sem_ptt: Optional[str] = None,
           sem_coletor: Optional[str] = None, contexto: Optional[dict] = None, so_coletores: Optional[set] = None) -> tuple[list, dict]:
    """Uma execução do ARC SEM ASPA (holdout), opcionalmente sem um PTT, sem um coletor ou só com os coletores de `so_coletores`."""
    rs = ((c, p) for c, p in build._rs(base, date_str, afi) if p != sem_ptt)
    abrir, nomes, _ = build._colecao(base, date_str, afi)
    if abrir is not None and sem_coletor:
        d, _ = build._dir_colecao(base, date_str, afi)
        arqs = [a for a in sorted(d.glob("*.tsv.gz")) if a.name.removesuffix(".tsv.gz") != sem_coletor]
        abrir = (lambda: ((c.asns, c.n_vps, c.vp0) for a in arqs for c in cm.ler(a))) if arqs else None
    if abrir is not None and so_coletores is not None:
        d, _ = build._dir_colecao(base, date_str, afi)
        arqs = [a for a in sorted(d.glob("*.tsv.gz")) if a.name.removesuffix(".tsv.gz") in so_coletores]
        abrir = (lambda: ((c.asns, c.n_vps, c.vp0) for a in arqs for c in cm.ler(a))) if arqs else None
    return arc.inferir(rs, abrir, [], e["caida"], e["grupos"], cfg, so_elos=lambda a, b: a in e["br"] or b in e["br"],
                       contexto=contexto)


def calibracao(vereditos: list, aspa: list[dict]) -> list[dict]:
    clientes = {int(o["customer"]) for o in aspa}
    verdade = regua.verdade_aspa(aspa)
    linhas = []
    for lo, hi in FAIXAS:
        prev = {(v.a, v.b) for v in vereditos if v.tipo == "p2c" and lo <= v.p < hi and v.b in clientes}
        acertos = len(prev & verdade)
        linhas.append({"p_de": lo, "p_ate": min(hi, 1.0), "previstos": len(prev), "confirmados_aspa": acertos,
                       "fracao": round(acertos / len(prev), 4) if prev else None})
    return linhas


def _eventos_aspa(escores: dict, aspa: list[dict]) -> list[tuple[dict, str, bool, int]]:
    """Eventos "p é provedor de c" nos elos em que c tem ASPA: `(log-escores, classe que o afirma, verdade, c)`. O ASPA é incompleto: um
    provedor real que o cliente não listou conta como erro, então o ECE medido é um limite superior."""
    clientes = {int(o["customer"]) for o in aspa}
    verdade = regua.verdade_aspa(aspa)
    out = []
    for (lo, hi), sc in escores.items():
        for p, c in ((lo, hi), (hi, lo)):
            if c in clientes:
                out.append((sc, "ab" if p == lo else "ba", (p, c) in verdade, c))
    return out


def _ece(pares: list[tuple[float, bool]], bins: int = 10) -> Optional[float]:
    if not pares:
        return None
    tot, acc = len(pares), 0.0
    por: dict[int, list[tuple[float, bool]]] = {}
    for q, y in pares:
        por.setdefault(min(bins - 1, int(q * bins)), []).append((q, y))
    for v in por.values():
        acc += len(v) / tot * abs(sum(q for q, _ in v) / len(v) - sum(1 for _, y in v if y) / len(v))
    return acc


def _nll(pares: list[tuple[float, bool]]) -> float:
    import math

    return -sum(math.log(max(1e-9, q if y else 1 - q)) for q, y in pares) / max(1, len(pares))


def calibracao_v2(escores: dict, aspa: list[dict], temperaturas=(0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16)) -> dict:
    """Temperatura que minimiza a log-perda dos eventos ASPA, ECE antes/depois e validação cruzada 2-fold (ajusta numa metade dos
    clientes, mede na outra). `ece_alto` só olha previsões com p ≥ 0,5, o que `p` publicada representa."""
    ev = _eventos_aspa(escores, aspa)
    if not ev:
        return {"estado": "indisponivel", "motivo": "sem eventos ASPA"}

    def pares(eventos, t):
        return [(refino.posterior(sc, t)[c], y) for sc, c, y, _ in eventos]

    def melhor(eventos):
        return min(temperaturas, key=lambda t: _nll(pares(eventos, t)))

    def alto(ps):
        return [x for x in ps if x[0] >= 0.5]

    t_otima = melhor(ev)
    metade = [[e for e in ev if e[3] % 2 == k] for k in (0, 1)]
    cv = []
    for k in (0, 1):
        if metade[k] and metade[1 - k]:
            t = melhor(metade[k])
            cv.append((t, _ece(alto(pares(metade[1 - k], t))), _ece(alto(pares(metade[1 - k], 1.0)))))
    curva = []
    for lo, hi in FAIXAS:
        sel = [(q, y) for q, y in pares(ev, t_otima) if lo <= q < hi]
        curva.append({"p_de": lo, "p_ate": min(hi, 1.0), "previstos": len(sel), "confirmados_aspa": sum(1 for _, y in sel if y),
                      "fracao": round(sum(1 for _, y in sel if y) / len(sel), 4) if sel else None})
    return {"eventos": len(ev), "temperatura_otima": t_otima,
            "ece_alto_bruto": round(_ece(alto(pares(ev, 1.0))) or 0, 4), "ece_alto_calibrado": round(_ece(alto(pares(ev, t_otima))) or 0, 4),
            "ece_todos_calibrado": round(_ece(pares(ev, t_otima)) or 0, 4),
            "validacao_cruzada": [{"t": t, "ece_alto_calibrado": None if a is None else round(a, 4), "ece_alto_bruto": None if b is None else round(b, 4)} for t, a, b in cv],
            "ece_alto_cv": round(sum(a for _, a, _ in cv if a is not None) / max(1, sum(1 for _, a, _ in cv if a is not None)), 4) if cv else None,
            "curva_confiabilidade": curva,
            "nota": "ASPA incompleto: provedor real não declarado conta como erro; o ECE é limite superior"}


def subconjuntos(vereditos: list, aspa: list[dict], vps: set[int], clique: set[int]) -> dict:
    """Recall/precisão nos pares do ASPA que são difíceis. Previsto = p2c de nível ≥ possível."""
    verdade = regua.verdade_aspa(aspa)
    previsto = regua.provedores_inferidos(vereditos, "possivel")
    por_par = {(v.a, v.b): v for v in vereditos if v.tipo == "p2c"}
    tem_cliente = {p for p, _ in previsto}
    cortes = {
        "vp_adjacente": lambda p, c: p in vps or c in vps,
        "poucos_vps": lambda p, c: (por_par.get((p, c)) is not None and 0 < por_par[(p, c)].n_vps <= 2),
        "stub_clique": lambda p, c: p in clique and c not in tem_cliente,
        "sem_cobertura": lambda p, c: (p, c) not in por_par,
    }
    out = {}
    for nome, f in cortes.items():
        v = {pc for pc in verdade if f(*pc)}
        prev = {pc for pc in previsto if f(*pc) and pc[1] in {c for _, c in verdade}}
        out[nome] = regua._prf(prev, v)
    return out


def _estabilidade(a: list, b: list) -> dict:
    """Fração dos p2c de nível ≥ provável em `a` que continuam iguais em `b` (mesma direção)."""
    pa, pb = regua.provedores_inferidos(a, "provavel"), regua.provedores_inferidos(b, "provavel")
    comuns = pa & pb
    return {"a": len(pa), "b": len(pb), "iguais": len(comuns),
            "jaccard": round(len(comuns) / len(pa | pb), 4) if (pa | pb) else None}


def estabilidade_entre_snapshots(base: Path, date_str: str) -> dict:
    atual = published_path(base, date_str, "as_relationships.json.gz")
    anteriores = sorted(d.name for d in (base / "published").iterdir() if d.is_dir() and d.name < date_str
                        and (d / "as_relationships.json.gz").exists()) if (base / "published").exists() else []
    if not atual.exists() or not anteriores:
        return {"estado": "indisponivel", "motivo": "precisa de dois snapshots consecutivos com as_relationships publicado"}
    def p2c(path):
        return {(r["a"], r["b"]) for r in read_json_gz(path)["relacoes"] if r["tipo"] == "p2c" and r["nivel"] in ("declarado", "confirmado", "provavel")}
    a, b = p2c(published_path(base, anteriores[-1], "as_relationships.json.gz")), p2c(atual)
    ambos = a & b
    return {"entre": [anteriores[-1], date_str], "anterior": len(a), "atual": len(b), "mantidos": len(ambos),
            "jaccard": round(len(ambos) / len(a | b), 4) if (a | b) else None}


def _gaps_por_faixa(pares: list[tuple[float, bool]], bins: int = 10) -> list[dict]:
    """Contribuição de cada faixa de `p` ao ECE: peso da faixa × |confiança média − taxa de acerto|."""
    tot = len(pares)
    por: dict[int, list[tuple[float, bool]]] = {}
    for q, y in pares:
        por.setdefault(min(bins - 1, int(q * bins)), []).append((q, y))
    out = []
    for b in sorted(por):
        v = por[b]
        conf, acerto = sum(q for q, _ in v) / len(v), sum(1 for _, y in v if y) / len(v)
        out.append({"p_de": b / bins, "p_ate": (b + 1) / bins, "n": len(v), "confianca": round(conf, 4), "acerto": round(acerto, 4),
                    "contribuicao_ece": round(len(v) / tot * abs(conf - acerto), 4)})
    return out


def ece_por_estrato(escores: dict, carac: dict, carac_esp: dict, aspa: list[dict], temperatura: float,
                    caracteristicas: tuple[str, ...] = ("vps", "dist_clique", "grau", "tripla", "caida")) -> dict:
    """ECE (só previsões com p ≥ 0,5, como a `p` publicada) por valor de cada característica do elo, nos eventos ASPA.
    Mostra onde o erro de calibração se concentra (poucos pontos de vista, perto ou longe do clique, grau, tripla de votos, CAIDA).
    Estratos com menos de 30 eventos saem com `ece` nulo: amostra pequena não calibra nada."""
    clientes = {int(o["customer"]) for o in aspa}
    verdade = regua.verdade_aspa(aspa)
    eventos = []
    for (lo, hi), sc in escores.items():
        for pv, c in ((lo, hi), (hi, lo)):
            if c in clientes:
                f = (carac if pv == lo else carac_esp).get((lo, hi))
                if f is None:
                    continue
                classe = "ab" if pv == lo else "ba"
                eventos.append((refino.posterior(sc, temperatura)[classe], (pv, c) in verdade, f))
    saida: dict = {"eventos": len(eventos), "ece_alto": None, "faixas": [], "por_caracteristica": {}}
    alto = [(q, y) for q, y, _ in eventos if q >= 0.5]
    saida["ece_alto"] = None if not alto else round(_ece(alto) or 0, 4)
    saida["faixas"] = _gaps_por_faixa(alto)
    for nome in caracteristicas:
        por: dict[str, list[tuple[float, bool]]] = {}
        for q, y, f in eventos:
            if q >= 0.5:
                por.setdefault(f.get(nome, "?"), []).append((q, y))
        saida["por_caracteristica"][nome] = {
            v: {"n": len(ps), "ece": round(_ece(ps) or 0, 4) if len(ps) >= 30 else None,
                "confianca": round(sum(q for q, _ in ps) / len(ps), 4), "acerto": round(sum(1 for _, y in ps if y) / len(ps), 4)}
            for v, ps in sorted(por.items())}
    return saida


def rodar(base: Path, date_str: str, log, cfg: Optional[Config] = None, ptts: int = 4, coletores: int = 3) -> dict:
    cfg = cfg or carregar()
    e = _entradas(base, date_str)
    out: dict = {"snapshot_date": date_str, "algoritmo": f"ARC v{cfg.versao}", "aspa_objetos": len(e["aspa"]),
                 "irr_data": e["irr_data"], "irr_como_caracteristica": cfg.refino.irr,
                 "nota": "execuções sem o ASPA como entrada; a precisão contra o ASPA é limite inferior (ASPA incompleto/defasado)"
                         + ("; com `irr` como característica, a concordância com o IRR é circular (não é referência independente): vale só a régua do ASPA" if cfg.refino.irr else "")}
    todos = {}
    for afi in build.AFIS:
        ctx: dict = {}
        base_vs, diag = _rodar(base, date_str, e, cfg, afi, contexto=ctx)
        todos[afi] = base_vs
        _, nomes_col, _ = build._colecao(base, date_str, afi)
        pasta_col, _ = build._dir_colecao(base, date_str, afi)
        vps: set[int] = set()
        for n in nomes_col:
            vps |= set(cm.cabecalho(pasta_col / f"{n}.tsv.gz")["vps"])
        entrada = {"coletores": nomes_col, "clique": diag.get("clique", []), "vereditos": len(base_vs)}
        entrada["aspa"] = regua.avaliar(base_vs, e["aspa"], e["br"])
        entrada["calibracao"] = calibracao(base_vs, e["aspa"])
        entrada["subconjuntos"] = subconjuntos(base_vs, e["aspa"], vps, set(diag.get("clique", [])))
        if e["irr"]:                                                         # 2ª referência (política do IRR; declarada, não praticada)
            entrada["irr"] = irr_relacao.avaliar(base_vs, e["irr"])
        if cfg.versao >= 2:                                                  # ARC v2 sobre a mesma execução sem ASPA
            perfil, restr = build._politica(base, date_str)
            vs2, d2 = refino.refinar(base_vs, ctx, cfg, afi, perfil, restr, usar_aspa=False, irr=e["irr"])
            sub2 = subconjuntos(vs2, e["aspa"], vps, set(diag.get("clique", [])))
            entrada["v2"] = {"aspa": regua.avaliar(vs2, e["aspa"], e["br"]), "calibracao": calibracao(vs2, e["aspa"]),
                             "calibracao_nb": calibracao_v2(d2["escores"], e["aspa"]),
                             "ece_por_estrato": ece_por_estrato(d2["escores"], d2["caracteristicas"], d2["caracteristicas_espelho"], e["aspa"],
                                                                d2["temperatura"]), "subconjuntos": sub2, "iteracoes": d2["iteracoes"],
                             "abstencoes": d2["abstencoes"], "treino": d2["treino"],
                             "ablacao_br_provavel": {f: r["br"]["ate_provavel"] for f, r in refino.ablacao(
                                 d2, lambda novos: regua.avaliar(novos, e["aspa"], e["br"]), vs2, cfg, afi).items()},
                             "cobertura_politica": {"asns_com_perfil": len(perfil), "restricoes": len(restr),
                                                    "elos_com_politica": sum(1 for c in d2["caracteristicas"].values() if c["politica"] != "-/-"),
                                                    "elos_com_restricao": sum(1 for c in d2["caracteristicas"].values() if c["restricao"] != "0")}}
            if e["irr"]:
                entrada["v2"]["irr"] = irr_relacao.avaliar(vs2, e["irr"])
            if e["caida"]:
                entrada["v2"]["concordancia_caida"] = regua.concordancia_caida(vs2, *e["caida"])
            todos[afi + "_v2"] = vs2
            del ctx
        if e["caida"]:
            cai = [type("V", (), {"tipo": "p2c", "nivel": "provavel", "a": a, "b": b})() for a, b in e["caida"][0]]
            entrada["caida_como_previsao"] = regua.avaliar(cai, e["aspa"], e["br"])
            entrada["concordancia_caida"] = regua.concordancia_caida(base_vs, *e["caida"])
        # validação cruzada por PTT (amostra dos que têm mais rotas) e retirada de coletores
        pttnomes = [p for p, _ in build._ptts_com_rotas(base, date_str, afi)][:ptts]
        entrada["sem_ptt"] = {}
        for p in pttnomes:
            vs, _ = _rodar(base, date_str, e, cfg, afi, sem_ptt=p)
            entrada["sem_ptt"][p] = {"br_provavel": regua.avaliar(vs, e["aspa"], e["br"])["br"]["ate_provavel"], "estabilidade": _estabilidade(base_vs, vs)}
        entrada["sem_coletor"] = {}
        for c in nomes_col[:coletores]:
            if len(nomes_col) < 2:
                break
            vs, _ = _rodar(base, date_str, e, cfg, afi, sem_coletor=c)
            entrada["sem_coletor"][c] = {"br_provavel": regua.avaliar(vs, e["aspa"], e["br"])["br"]["ate_provavel"], "estabilidade": _estabilidade(base_vs, vs)}
        out[afi] = entrada
        log.info("regua computed", afi=afi, vereditos=len(base_vs))
    out["estabilidade_entre_snapshots"] = estabilidade_entre_snapshots(base, date_str)
    # com `refino.irr` ligado só para medir (`--irr`), o relatório não sobrescreve o de referência da data (é o termo de comparação)
    destino = base / "ops" / "relacoes" / (f"{date_str}.irr.json" if cfg.refino.irr and not carregar().refino.irr else f"{date_str}.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("regua written", path=str(destino))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Régua de validação do ARC (contra o ASPA, sem usá-lo como entrada)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--ptts", type=int, default=4, help="quantos PTTs retirar, um por vez")
    p.add_argument("--coletores", type=int, default=3, help="quantos coletores retirar, um por vez")
    p.add_argument("--irr", action="store_true", help="liga `refino.irr` só nesta execução: mede o IRR como característica contra o ASPA, sem mudar a configuração")
    a = p.parse_args(argv)
    cfg = carregar()
    if a.irr:
        cfg = dataclasses.replace(cfg, refino=dataclasses.replace(cfg.refino, irr=True))
    rodar(data_dir(), a.date, configure_logging(), cfg=cfg, ptts=a.ptts, coletores=a.coletores)
    return 0


if __name__ == "__main__":
    sys.exit(main())
