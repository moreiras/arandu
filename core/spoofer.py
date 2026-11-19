# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""CAIDA Spoofer: agregados por ASN dos testes de validação de endereço de origem (SAV), sem guardar o endereço do cliente.

A API devolve, em cada sessão, o /24 do cliente (`client4`/`client6`); `sanear` o descarta antes de qualquer gravação. Cada sessão testa o envio de pacotes com origem forjada, um de endereço privado
(`privatespoof`) e um de endereço roteado (`routedspoof`), em IPv4 e/ou IPv6: `blocked` (a rede barrou), `received` (o pacote forjado chegou), `rewritten` (um NAT reescreveu a origem; **não é falha**),
`unknown` ou nulo. Uma sessão é **conclusiva** quando algum teste deu `blocked` ou `received`; atrás de NAT (IPv4) o resultado não fala da rede do ASN, então só contam as sessões IPv4 fora de NAT e as IPv6.
O Spoofer é voluntário e concentrado em poucos ASNs: sem `minimo` sessões conclusivas o ASN fica sem pontuação neste pilar.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

CAMPOS = ("session", "timestamp", "asn4", "asn6", "country", "nat4", "nat6", "privatespoof", "routedspoof", "privatespoof6", "routedspoof6")
CONCLUSIVOS = ("blocked", "received")
JANELA_DIAS = 365
MINIMO_CONCLUSIVAS = 5


def sanear(sessao: dict) -> dict:
    """Só os campos de resultado e de ASN; `client4`/`client6` e os campos JSON-LD (`@id`, `@type`) ficam de fora."""
    out = {k: sessao.get(k) for k in CAMPOS}
    for k in ("asn4", "asn6"):
        out[k] = int(out[k]) if str(out[k] or "").isdigit() else None
    return out


def _data(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _por_familia(s: dict):
    """(asn, família, atrás de NAT, resultado privado, resultado roteado) de cada família com ASN na sessão."""
    if s.get("asn4"):
        yield s["asn4"], 4, bool(s.get("nat4")), s.get("privatespoof"), s.get("routedspoof")
    if s.get("asn6"):
        yield s["asn6"], 6, bool(s.get("nat6")), s.get("privatespoof6"), s.get("routedspoof6")


def agregar(sessoes: list[dict], fim: dt.date, janela_dias: int = JANELA_DIAS, minimo: int = MINIMO_CONCLUSIVAS) -> tuple[dict[str, dict], dict]:
    """Agrega por ASN as sessões da janela (`fim - janela_dias`, `fim`], com `fim` incluído até o fim do dia. Devolve `({asn: métricas}, resumo)`."""
    limite = dt.datetime.combine(fim + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    inicio = limite - dt.timedelta(days=janela_dias + 1)
    ac: dict[int, dict] = defaultdict(lambda: {"sessoes": set(), "v4": 0, "v6": 0, "nat4": 0, "ultima": None, "conclusivas_v4": 0, "conclusivas_v6": 0, "priv": [0, 0], "rot": [0, 0], "com_recebido": 0})
    na_janela = 0
    for s in sessoes:
        t = _data(s["timestamp"])
        if not (inicio < t < limite):
            continue
        na_janela += 1
        for asn, fam, nat, priv, rot in _por_familia(s):
            a = ac[asn]
            a["sessoes"].add(s["session"])
            a["v4" if fam == 4 else "v6"] += 1
            a["nat4"] += fam == 4 and nat
            if a["ultima"] is None or t > a["ultima"]:
                a["ultima"] = t
            if nat or not (priv in CONCLUSIVOS or rot in CONCLUSIVOS):
                continue
            a["conclusivas_v" + str(fam)] += 1
            recebido = False
            for tipo, r in (("priv", priv), ("rot", rot)):
                if r in CONCLUSIVOS:
                    a[tipo][0 if r == "received" else 1] += 1
                    recebido = recebido or r == "received"
            a["com_recebido"] += recebido
    asns = {}
    for asn, a in sorted(ac.items()):
        conc = a["conclusivas_v4"] + a["conclusivas_v6"]
        pct = lambda n, d: round(100 * n / d, 1) if d else None      # noqa: E731
        asns[str(asn)] = {"sessoes": len(a["sessoes"]), "sessoes_v4": a["v4"], "sessoes_v6": a["v6"], "pct_nat_v4": pct(a["nat4"], a["v4"]), "ultima_sessao": a["ultima"].date().isoformat(),
                          "conclusivas": conc, "conclusivas_v4": a["conclusivas_v4"], "conclusivas_v6": a["conclusivas_v6"], "suficiente": conc >= minimo,
                          "pct_bloqueado": pct(conc - a["com_recebido"], conc) if conc else None,
                          "pct_recebido_privado": pct(a["priv"][0], sum(a["priv"])), "pct_recebido_roteado": pct(a["rot"][0], sum(a["rot"]))}
    resumo = {"sessoes_na_janela": na_janela, "asns": len(asns), "asns_suficientes": sum(1 for v in asns.values() if v["suficiente"]), "minimo_conclusivas": minimo,
              "janela": {"inicio": inicio.date().isoformat(), "fim": fim.isoformat(), "dias": janela_dias}}
    return asns, resumo
