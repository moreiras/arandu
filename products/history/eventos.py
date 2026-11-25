# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Log de eventos do histórico: o que mudou entre dois snapshots consecutivos e a janela de confirmação.

Um evento nasce no snapshot em que a mudança aparece (`estado: pendente`). Passa a `confirmado` quando o novo estado persiste por
`janela` snapshots com histórico, contando o de origem, e a `revertido` se algum snapshot seguinte o desmente. Snapshot de coleta
`parcial` nunca gera evento negativo (o que sumiu pode ser falha de coleta) nem confirma ou desmente evento algum.

Linguagem: o evento descreve uma diferença **observada** entre dois snapshots (ou a ausência de dado nele); não atribui causa nem
intenção, e por isso não leva nome de empresa — só a chave (ASN, PTT, CNPJ, prefixo). Mudança de provedor é inferência (ARC). Mudança de origem de prefixo só entra se uma das
pontas é ASN brasileiro (o recorte do Arandurapé)."""
from __future__ import annotations

import hashlib
from typing import Iterable, Optional

from products.history.linhas import provedores_firmes
from products.history.snapshot import SERVICOS, Snap

# Versão da regra de detecção, gravada no índice do histórico. 1: contagem de ROA, ASPA e RPKI ausente era lida como zero (o
# artefato de 2026-07-05: `roa_list` de estrangeiros publicado só em 2026-06-28). 2: os eventos de ROA, ASPA e RPKI só se geram
# quando o campo-fonte está coberto nos dois snapshots comparados (`linhas.presenca`).
REGRA_VERSAO = 2

# tipo → (janela de confirmação em snapshots, negativo?)
TIPOS: dict[str, tuple[int, bool]] = {
    "asn_novo": (2, False), "asn_sumido": (2, True),
    "ixp_entrada": (1, False), "ixp_saida": (1, True),                                    # cadastral (PeeringDB / IX.br)
    "ixp_entrada_observada": (2, False), "ixp_saida_observada": (2, True),                # par direto nas rotas coletadas
    "provedor_novo": (3, False), "provedor_perdido": (3, True),
    "mudanca_origem": (2, False),
    "roa_ganho": (1, False), "roa_perdido": (1, True),
    "aspa_ganho": (1, False), "aspa_perdido": (1, True),
    "rpki_invalido_novo": (2, False), "rpki_invalido_resolvido": (2, False),
    "outorga_nova": (1, False), "outorga_baixa": (2, True),
    "alerta_novo": (2, False), "alerta_resolvido": (2, False),
}


def _id(tipo: str, entidade: str, chave: str, data: str) -> str:
    return hashlib.sha1(f"{tipo}|{entidade}|{chave}|{data}".encode("utf-8")).hexdigest()[:12]


def _evento(data: str, tipo: str, entidade: str, chave: str, de, para, uf: Optional[str] = None, **detalhe) -> dict:
    janela = TIPOS[tipo][0]
    ev = {"id": _id(tipo, entidade, chave, data), "data": data, "tipo": tipo, "entidade": entidade, "chave": chave,
          "de": de, "para": para, "janela": janela, "estado": "confirmado" if janela == 1 else "pendente"}
    if entidade.startswith("asn:"):
        ev["asn"] = int(entidade[4:])
    if uf:
        ev["uf"] = uf
    if detalhe:
        ev["detalhe"] = detalhe
    ev["confirmado"] = ev["estado"] == "confirmado"
    if ev["confirmado"]:
        ev["confirmado_em"] = data
    return ev


def _ativo(ln: Optional[dict]) -> bool:
    """ASN BR presente na tabela global (e, por ser BR, no Registro.br)."""
    return bool(ln and ln.get("is_br") and (ln.get("p4") or ln.get("p6")))


def _coberto(ln: Optional[dict], campo: str) -> bool:
    """O snapshot cobriu o campo-fonte (`roa_list`, `aspa_providers`, `rpki_validation`) deste ASN: o documento traz o campo ou passou
    pela etapa de saúde, que o gravaria se houvesse. Linha sem os marcadores (regra 1) não está coberta: sem evidência, sem evento."""
    return bool(ln) and (ln.get(f"tem_{campo}") is True or ln.get("tem_saude") is True)


def _alertas(doc: dict) -> set[str]:
    return {a["id"] for a in doc.get("alerts") or []}


def detectar(atual: Snap, anterior: Snap) -> list[dict]:
    """Eventos do snapshot `atual` em relação ao `anterior`."""
    d = atual.date
    parcial = atual.parcial
    ev: list[dict] = []
    ra, rp = atual.linhas, anterior.linhas
    comparavel_alertas = bool(atual.rules_version) and atual.rules_version == anterior.rules_version
    ptts_ok = atual.ptts_ok & anterior.ptts_ok
    candidatos_origem: set[int] = set()

    for asn in sorted(ra):
        a, p = ra[asn], rp.get(asn)
        uf = a.get("uf")
        e = f"asn:{asn}"
        if _ativo(a) and not _ativo(p):
            ev.append(_evento(d, "asn_novo", e, "", False, True, uf))
        if p is None:
            continue
        if not parcial and _ativo(p) and not _ativo(a):
            ev.append(_evento(d, "asn_sumido", e, "", True, False, uf))
        # contagens simples: só com o campo-fonte coberto nos dois snapshots (ausência nunca vira zero)
        if _coberto(a, "roa_list") and _coberto(p, "roa_list"):
            if a.get("n_roa", 0) > 0 and p.get("n_roa", 0) == 0:
                ev.append(_evento(d, "roa_ganho", e, "", p.get("n_roa", 0), a["n_roa"], uf))
            if not parcial and a.get("n_roa", 0) == 0 and p.get("n_roa", 0) > 0:
                ev.append(_evento(d, "roa_perdido", e, "", p["n_roa"], 0, uf))
        if _coberto(a, "aspa_providers") and _coberto(p, "aspa_providers"):
            if a.get("n_aspa", 0) > 0 and p.get("n_aspa", 0) == 0:
                ev.append(_evento(d, "aspa_ganho", e, "", 0, a["n_aspa"], uf))
            if not parcial and a.get("n_aspa", 0) == 0 and p.get("n_aspa", 0) > 0:
                ev.append(_evento(d, "aspa_perdido", e, "", p["n_aspa"], 0, uf))
        if _coberto(a, "rpki_validation") and _coberto(p, "rpki_validation"):
            if a.get("rpki_invalid", 0) > 0 and p.get("rpki_invalid", 0) == 0:
                ev.append(_evento(d, "rpki_invalido_novo", e, "", 0, a["rpki_invalid"], uf))
            if a.get("rpki_invalid", 0) == 0 and p.get("rpki_invalid", 0) > 0:
                ev.append(_evento(d, "rpki_invalido_resolvido", e, "", p["rpki_invalid"], 0, uf))
        # conjuntos: só abre os documentos quando o hash mudou
        mudou = [k for k in ("hash_ixm", "hash_ixd", "hash_relacoes", "hash_pfx") if a.get(k) != p.get(k)]
        if comparavel_alertas and a.get("hash_alertas") != p.get("hash_alertas"):
            mudou.append("hash_alertas")
        if not mudou:
            continue
        if "hash_pfx" in mudou:
            candidatos_origem.add(asn)
        da, dp = atual.doc(asn), anterior.doc(asn)
        if not da or not dp:
            continue
        if "hash_ixm" in mudou:
            novo, velho = set(da.get("ixp_member_codes") or []), set(dp.get("ixp_member_codes") or [])
            ev += [_evento(d, "ixp_entrada", e, c, None, c, uf, ixp=c) for c in sorted(novo - velho)]
            if not parcial:
                ev += [_evento(d, "ixp_saida", e, c, c, None, uf, ixp=c) for c in sorted(velho - novo)]
        if "hash_ixd" in mudou:
            novo, velho = set(da.get("ixps_direct") or []), set(dp.get("ixps_direct") or [])
            ev += [_evento(d, "ixp_entrada_observada", e, c, None, c, uf, ixp=c) for c in sorted(novo - velho) if c in ptts_ok]
            if not parcial:
                ev += [_evento(d, "ixp_saida_observada", e, c, c, None, uf, ixp=c) for c in sorted(velho - novo) if c in ptts_ok]
        if "hash_relacoes" in mudou:
            pa, pp = provedores_firmes(da), provedores_firmes(dp)
            if pa is not None and pp is not None:
                ev += [_evento(d, "provedor_novo", e, str(x), None, x, uf, provedor=x) for x in sorted(set(pa) - set(pp))]
                if not parcial:
                    ev += [_evento(d, "provedor_perdido", e, str(x), x, None, uf, provedor=x) for x in sorted(set(pp) - set(pa))]
        if "hash_alertas" in mudou:
            novo, velho = _alertas(da), _alertas(dp)
            ev += [_evento(d, "alerta_novo", e, x, None, x, uf, regras=atual.rules_version) for x in sorted(novo - velho)]
            ev += [_evento(d, "alerta_resolvido", e, x, x, None, uf, regras=atual.rules_version) for x in sorted(velho - novo)]
    if not parcial:                                            # ASN que deixou de ter documento no snapshot
        ev += [_evento(d, "asn_sumido", f"asn:{asn}", "", True, False, rp[asn].get("uf")) for asn in sorted(set(rp) - set(ra)) if _ativo(rp[asn])]
    ev += _origens(atual, anterior, candidatos_origem)
    ev += _outorgas(atual, anterior, parcial)
    return sorted(ev, key=lambda x: (x["tipo"], x["entidade"], x["chave"]))


def _prefixos(doc: dict) -> set[str]:
    return set(doc.get("global_prefixes_v4") or []) | set(doc.get("global_prefixes_v6") or [])


def _origens(atual: Snap, anterior: Snap, candidatos: set[int]) -> list[dict]:
    """Prefixo cuja **única** origem mudou: saiu de exatamente um ASN e entrou em exatamente um outro, sem outro detentor."""
    retirou: dict[str, set[int]] = {}
    pegou: dict[str, set[int]] = {}
    for asn in sorted(candidatos):
        da, dp = atual.doc(asn), anterior.doc(asn)
        if not da or not dp:
            continue
        pa, pp = _prefixos(da), _prefixos(dp)
        for p in pp - pa:
            retirou.setdefault(p, set()).add(asn)
        for p in pa - pp:
            pegou.setdefault(p, set()).add(asn)
    movidos = {p for p in retirou if p in pegou and len(retirou[p]) == 1 and len(pegou[p]) == 1}
    if not movidos:
        return []
    detentores = atual.detentores(movidos)
    out = []
    for p in sorted(movidos):
        (velho,), (novo,) = tuple(retirou[p]), tuple(pegou[p])
        if velho == novo or detentores[p] != {novo}:
            continue                                                  # MOAS: não é origem única
        if not ((atual.linhas.get(novo) or {}).get("is_br") or (anterior.linhas.get(velho) or {}).get("is_br")):
            continue                                                  # fora do recorte: nenhuma ponta é brasileira
        doc_novo = atual.doc(novo) or {}
        rpki = (doc_novo.get("rpki_validation") or {}).get(p)
        uf = (atual.linhas.get(novo) or {}).get("uf")
        e = _evento(atual.date, "mudanca_origem", f"prefixo:{p}", str(novo), velho, novo, uf, rpki=rpki)
        e["asn"] = novo
        if rpki == "invalid":
            e["destaque"] = True                                      # o novo estado é RPKI inválido
        out.append(e)
    return out


def _outorgas(atual: Snap, anterior: Snap, parcial: bool) -> list[dict]:
    out = []
    oa, op = atual.outorgas, anterior.outorgas
    for sv in SERVICOS:
        if sv not in oa or sv not in op:
            continue
        out += [_evento(atual.date, "outorga_nova", f"cnpj:{c}", sv, None, sv, servico=sv) for c in sorted(oa[sv] - op[sv])]
        if not parcial:
            out += [_evento(atual.date, "outorga_baixa", f"cnpj:{c}", sv, sv, None, servico=sv) for c in sorted(op[sv] - oa[sv])]
    return out


# --- confirmação ------------------------------------------------------------------------------------------------------------------

def vale_em(ev: dict, s: Snap) -> Optional[bool]:
    """O estado novo do evento ainda vale em `s`? None = não dá para dizer (snapshot parcial, bloco ausente, PTT não coletado)."""
    tipo, negativo = ev["tipo"], TIPOS[ev["tipo"]][1]
    if s.parcial and negativo:
        return None
    ent = ev["entidade"]
    if ent.startswith("cnpj:"):
        conj = s.outorgas.get(ev["chave"])
        if conj is None:
            return None
        return (ent[5:] in conj) if tipo == "outorga_nova" else (ent[5:] not in conj)
    if tipo == "mudanca_origem":
        p, velho, novo = ent[8:], ev["de"], ev["para"]
        dn, dv = s.doc(novo), s.doc(velho)
        if not dn:
            return None
        return p in _prefixos(dn) and not (dv and p in _prefixos(dv))
    asn = ev["asn"]
    ln = s.linhas.get(asn)
    if tipo in ("asn_novo", "asn_sumido"):
        return _ativo(ln) if tipo == "asn_novo" else not _ativo(ln)
    if ln is None:
        return None
    for prefixo, campo, contagem in (("roa_", "roa_list", "n_roa"), ("aspa_", "aspa_providers", "n_aspa"),
                                     ("rpki_invalido", "rpki_validation", "rpki_invalid")):
        if tipo.startswith(prefixo):
            if not _coberto(ln, campo):
                return None
            return ln.get(contagem, 0) > 0 if tipo in ("roa_ganho", "aspa_ganho", "rpki_invalido_novo") else ln.get(contagem, 0) == 0
    doc = s.doc(asn)
    if not doc:
        return None
    if tipo in ("ixp_entrada", "ixp_saida"):
        return (ev["chave"] in (doc.get("ixp_member_codes") or [])) == (tipo == "ixp_entrada")
    if tipo in ("ixp_entrada_observada", "ixp_saida_observada"):
        if ev["chave"] not in s.ptts_ok:
            return None
        return (ev["chave"] in (doc.get("ixps_direct") or [])) == (tipo == "ixp_entrada_observada")
    if tipo in ("provedor_novo", "provedor_perdido"):
        prov = provedores_firmes(doc)
        if prov is None:
            return None
        return (int(ev["chave"]) in prov) == (tipo == "provedor_novo")
    if tipo in ("alerta_novo", "alerta_resolvido"):
        if not s.rules_version or s.rules_version != (ev.get("detalhe") or {}).get("regras"):
            return None
        return (ev["chave"] in _alertas(doc)) == (tipo == "alerta_novo")
    return None


def avaliar(ev: dict, posteriores: Iterable[Snap]) -> dict:
    """Reavalia um evento pendente com os snapshots seguintes (em ordem). Devolve o evento (alterado) — sem efeito se já decidido."""
    if ev["estado"] != "pendente":
        return ev
    vistos = 1
    for s in posteriores:
        v = vale_em(ev, s)
        if v is None:
            continue
        if not v:
            ev.update(estado="revertido", confirmado=False, revertido_em=s.date)
            return ev
        vistos += 1
        if vistos >= ev["janela"]:
            ev.update(estado="confirmado", confirmado=True, confirmado_em=s.date)
            return ev
    return ev
