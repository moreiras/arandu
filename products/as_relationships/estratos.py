# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estratos de evidência independente do ARC: definição, ECE por estrato, cobertura e viés do ASPA.

    python -m products.as_relationships.estratos --date 2026-11-06

Definição: o elo, visto no sentido do provedor inferido, está **com evidência independente** se o CAIDA
concorda com o sentido (`caida=ab`) **ou** a tripla está confirmada (`tripla=ab+`). Se um confirma e o outro contradiz (CAIDA `ba` ou `pp`
contra `ab+`; tripla `ba`/`ba+` contra `caida=ab`) o elo é `conflito` e fica fora. Não entram: distância ao clique (prior do próprio ARC),
`tripla=ab` sem o `+`, número de VPs.

O que este módulo mede e o diagnóstico (`diagnostico.py`) não mede:
  - a interseção e a união dos dois critérios (o `ece_por_estrato` olha uma característica por vez);
  - a **cobertura**: fração dos p2c ≥ provável (BR e global) que cai em cada estrato, para saber quantos elos têm `p` calibrada;
  - o **viés do ASPA**: nos eventos em que o ASPA "desmente" o ARC, o que a segunda referência (política do IRR) diz. Se o IRR concorda com o ARC,
    o desmentido do ASPA é provavelmente omissão do ASPA; se discorda, o erro é do ARC (ou das duas referências).
Não escreve em `published/`. Saída: `data/ops/relacoes/estratos-AAAA-MM-DD.json`."""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import zlib
from pathlib import Path
from typing import Optional

from core.common import configure_logging, data_dir, today_str
from products.as_relationships import build, refino, regua, validacao
from products.as_relationships.config import Config, carregar

CLASSES = ("ambos", "so_caida", "so_tripla", "conflito", "sem_evidencia")
COM_EVIDENCIA = ("ambos", "so_caida", "so_tripla")
MIN_EVENTOS = 30                                                   # abaixo disto o estrato não recebe ECE (mesma regra do `ece_por_estrato`)


classe_estrato = refino.classe_estrato                                   # a regra mora em `refino` (o ARC a usa ao publicar); este módulo só mede


def _resumo(pares: list[tuple[float, bool]]) -> dict:
    n = len(pares)
    if not n:
        return {"n": 0, "ece": None, "confianca": None, "acerto": None}
    return {"n": n, "ece": round(validacao._ece(pares) or 0, 4) if n >= MIN_EVENTOS else None,
            "confianca": round(sum(q for q, _ in pares) / n, 4), "acerto": round(sum(1 for _, y in pares if y) / n, 4)}


def _eventos(d2: dict, aspa: list[dict]) -> list[dict]:
    """Eventos "p é provedor de c" nos elos em que c tem ASPA, com p ≥ 0,5, com o estrato e a posição do elo."""
    clientes = {int(o["customer"]) for o in aspa}
    verdade = regua.verdade_aspa(aspa)
    out = []
    for (lo, hi), sc in d2["escores"].items():
        for pv, c in ((lo, hi), (hi, lo)):
            if c not in clientes:
                continue
            f = (d2["caracteristicas"] if pv == lo else d2["caracteristicas_espelho"]).get((lo, hi))
            if f is None:
                continue
            q = refino.posterior(sc, d2["temperatura"])["ab" if pv == lo else "ba"]
            if q >= 0.5:
                out.append({"q": q, "y": (pv, c) in verdade, "estrato": classe_estrato(f), "pv": pv, "c": c, "vps": f.get("vps")})
    return out


def _classe_veredito(v, d2: dict) -> tuple[str, Optional[str]]:
    """(estrato, vps) de um veredito p2c, nas características vistas do provedor `v.a`."""
    lo, hi = min(v.a, v.b), max(v.a, v.b)
    f = (d2["caracteristicas"] if v.a == lo else d2["caracteristicas_espelho"]).get((lo, hi))
    return (classe_estrato(f), f.get("vps")) if f is not None else ("sem_evidencia", None)


def _dobra(asn: int) -> int:
    return zlib.crc32(str(asn).encode()) % 2


def _calibrar_cv(ev: list[dict], chave) -> dict:
    """`p_calibrada` por estrato: taxa de acerto observada no ASPA, validação cruzada de 2 dobras por ASN do cliente (CRC32 do ASN, determinístico).
    Ajusta numa dobra, mede o ECE na outra e junta. `chave(evento)` define o estrato de calibração."""
    pares, por = [], {}
    for treino, teste in ((0, 1), (1, 0)):
        tab: dict = {}
        for e in ev:
            if _dobra(e["c"]) == treino:
                a = tab.setdefault(chave(e), [0, 0]); a[0] += 1; a[1] += e["y"]
        for e in ev:
            if _dobra(e["c"]) == teste and tab.get(chave(e), [0, 0])[0] >= MIN_EVENTOS:
                k = chave(e); q = tab[k][1] / tab[k][0]
                pares.append((q, e["y"])); por.setdefault(k, []).append((q, e["y"]))
    return {"ece_cv": round(validacao._ece(pares) or 0, 4) if pares else None, "eventos": len(pares), "de": len(ev),
            "por_estrato": {str(k): _resumo(v) for k, v in sorted(por.items(), key=lambda x: str(x[0]))}}


def _rebaixar(vs: list, d2: dict, fora) -> list:
    """Rebaixa de "provável" para "possível" os p2c em que `fora(estrato, vps)` (o nível "confirmado" e o "declarado" ficam como estão)."""
    return [dataclasses.replace(v, nivel="possivel") if v.tipo == "p2c" and v.nivel == "provavel" and fora(*_classe_veredito(v, d2)) else v for v in vs]


def _prf_br(vs: list, aspa: list[dict], br: set[int]) -> dict:
    r = regua.avaliar(vs, aspa, br)["br"]["ate_provavel"]
    return {"previstos": r["previstos"], "precisao": r["precisao"], "recall": r["recall"]}


def _irr_vs_arc(ev: dict, irr: dict) -> str:
    r = irr.get((min(ev["pv"], ev["c"]), max(ev["pv"], ev["c"])))
    if r is None or r["rotulo"] == "conflito" or not r["rotulo"].startswith("p2c"):
        return "sem_irr"
    return "irr_concorda" if (r["provedor"], r["cliente"]) == (ev["pv"], ev["c"]) else "irr_discorda"


def medir(vs: list, d2: dict, aspa: list[dict], irr: Optional[dict], br: set[int]) -> dict:
    """Estratos de uma família de endereço (v2 sobre uma execução sem ASPA)."""
    ev = _eventos(d2, aspa)
    out: dict = {"eventos_aspa_p_alta": len(ev), "ece_global": round(validacao._ece([(e["q"], e["y"]) for e in ev]) or 0, 4) if ev else None}
    out["por_estrato"] = {c: _resumo([(e["q"], e["y"]) for e in ev if e["estrato"] == c]) for c in CLASSES}
    com = [e for e in ev if e["estrato"] in COM_EVIDENCIA]
    out["com_evidencia"] = _resumo([(e["q"], e["y"]) for e in com])
    out["com_evidencia"]["faixas"] = validacao._gaps_por_faixa([(e["q"], e["y"]) for e in com])
    filt = [e for e in com if e["vps"] != "0"]                         # `vps=0` fica fora do estrato
    out["com_evidencia_sem_vps0"] = {**_resumo([(e["q"], e["y"]) for e in filt]), "por_estrato": {c: _resumo([(e["q"], e["y"]) for e in filt if e["estrato"] == c]) for c in COM_EVIDENCIA}}
    out["calibracao_cv"] = {"por_estrato": _calibrar_cv(filt, lambda e: e["estrato"]),
                            "por_estrato_e_vps": _calibrar_cv(filt, lambda e: (e["estrato"], e["vps"])),
                            "so_ambos": _calibrar_cv([e for e in filt if e["estrato"] == "ambos"], lambda e: e["estrato"])}
    out["com_evidencia"]["por_vps"] = {v: _resumo([(e["q"], e["y"]) for e in com if e["vps"] == v]) for v in sorted({e["vps"] for e in com})}
    # Viés do ASPA: o que a política do IRR diz dos elos em que o ASPA discorda / concorda do ARC
    if irr:
        sai: dict = {}
        for grupo, evs in (("com_evidencia", com), ("sem_evidencia", [e for e in ev if e["estrato"] == "sem_evidencia"])):
            g = {"aspa_confirma": {"irr_concorda": 0, "irr_discorda": 0, "sem_irr": 0}, "aspa_desmente": {"irr_concorda": 0, "irr_discorda": 0, "sem_irr": 0}}
            for e in evs:
                g["aspa_confirma" if e["y"] else "aspa_desmente"][_irr_vs_arc(e, irr)] += 1
            des = g["aspa_desmente"]
            lidos = des["irr_concorda"] + des["irr_discorda"]
            g["desmentidos_com_irr_que_concorda_pct"] = round(100 * des["irr_concorda"] / lidos, 1) if lidos else None
            sai[grupo] = g
        out["vies_aspa"] = sai
    # Cobertura: p2c ≥ provável por estrato (BR = cliente brasileiro, como na régua)
    aceitos = set(regua.NIVEIS[:regua.NIVEIS.index("provavel") + 1])
    cob: dict = {}
    for escopo, filtro in (("global", lambda v: True), ("br", lambda v: v.b in br)):
        c = {k: 0 for k in CLASSES}
        c["p2p"] = 0
        for v in vs:
            if v.nivel not in aceitos or not filtro(v) or v.tipo not in ("p2c", "p2p"):
                continue
            if v.tipo == "p2p":
                c["p2p"] += 1
                continue
            lo, hi = min(v.a, v.b), max(v.a, v.b)
            f = (d2["caracteristicas"] if v.a == lo else d2["caracteristicas_espelho"]).get((lo, hi))
            c[classe_estrato(f) if f is not None else "sem_evidencia"] += 1
        p2c = sum(c[k] for k in CLASSES)
        cob[escopo] = {"p2c_provavel_ou_mais": p2c, **c, "com_evidencia": sum(c[k] for k in COM_EVIDENCIA),
                       "com_evidencia_pct": round(100 * sum(c[k] for k in COM_EVIDENCIA) / p2c, 1) if p2c else None}
    out["cobertura"] = cob
    com_ev = lambda c, v: c in COM_EVIDENCIA and v != "0"
    out["rebaixo"] = {"base": _prf_br(vs, aspa, br),
                      "so_conflito": _prf_br(_rebaixar(vs, d2, lambda c, v: c == "conflito"), aspa, br),
                      "conflito_e_sem_evidencia": _prf_br(_rebaixar(vs, d2, lambda c, v: c in ("conflito", "sem_evidencia")), aspa, br),
                      "tudo_fora_do_estrato": _prf_br(_rebaixar(vs, d2, lambda c, v: not com_ev(c, v)), aspa, br),
                      "provavel_por_estrato_br": {c: sum(1 for v in vs if v.tipo == "p2c" and v.nivel == "provavel" and v.b in br and _classe_veredito(v, d2)[0] == c) for c in CLASSES},
                      "niveis_br": {n: sum(1 for v in vs if v.tipo == "p2c" and v.nivel == n and v.b in br) for n in regua.NIVEIS}}
    return out


def rodar(base: Path, date_str: str, log, cfg: Optional[Config] = None) -> dict:
    cfg = dataclasses.replace(cfg or carregar(), versao=2)
    cfg = dataclasses.replace(cfg, refino=dataclasses.replace(cfg.refino, estratos=dataclasses.replace(cfg.refino.estratos, ativo=False)))   # mede a base SEM o rebaixo
    e = validacao._entradas(base, date_str)
    out: dict = {"snapshot_date": date_str, "irr_data": e["irr_data"], "aspa_objetos": len(e["aspa"]),
                 "definicao": "caida=ab ou tripla=ab+; conflito (um confirma e o outro contradiz) fica fora",
                 "nota": "execução sem o ASPA como entrada (holdout); ASPA incompleto e defasado: `acerto` é limite inferior"}
    for afi in build.AFIS:
        ctx: dict = {}
        vs, _ = validacao._rodar(base, date_str, e, dataclasses.replace(cfg, versao=1), afi, contexto=ctx)
        perfil, restr = build._politica(base, date_str)
        vs2, d2 = refino.refinar(vs, ctx, cfg, afi, perfil, restr, usar_aspa=False)
        out[afi] = medir(vs2, d2, e["aspa"], e["irr"], e["br"])
        log.info("estratos computed", afi=afi, eventos=out[afi]["eventos_aspa_p_alta"])
        del ctx, d2
    destino = base / "ops" / "relacoes" / f"estratos-{date_str}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("estratos written", path=str(destino))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Estratos de evidência independente do ARC")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    rodar(data_dir(), a.date, configure_logging())
    return 0


if __name__ == "__main__":
    sys.exit(main())
