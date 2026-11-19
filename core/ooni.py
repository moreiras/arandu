# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""OONI: classificação e agregação, por ASN, das medições brutas do bucket aberto `ooni-data-eu-fra`.

O que sai de uma medição é só `(ASN, teste, veredito da sonda)`: nunca `report_id`, `input`, `probe_ip`, nome de rede, resolvedor, versão de software nem horário individual.
O veredito é o **da própria sonda**, calculado no aparelho segundo o `ooni/spec` (nettests/ts-0NN): o backend do OONI está em melhor posição para decidir bloqueio, e o que
se conta aqui NÃO é censura confirmada. Quem lê a saída deve repetir esse aviso.

Critérios por teste (anomalia = a sonda declarou bloqueio/falha; `n` = medições válidas):
  * `whatsapp` (ts-018): algum de `registration_server_status`, `whatsapp_endpoints_status`, `whatsapp_web_status` = "blocked".
  * `telegram` (ts-020): `telegram_web_status` = "blocked" ou `telegram_tcp_blocking`/`telegram_http_blocking` verdadeiro.
  * `signal` (ts-029): `signal_backend_status` = "blocked". Medição com `test_version` <= 0.2.3 é descartada (falsos positivos documentados no spec).
  * `facebookmessenger` (ts-019): `facebook_tcp_blocking` ou `facebook_dns_blocking` verdadeiro.
  * `tor` (ts-023): anomalia = nenhum alvo de nenhum tipo acessível (a soma de `*_accessible` é 0 com `*_total` > 0); somam-se também alvos totais e acessíveis por tipo.
  * `psiphon` (ts-015): `failure` não nulo (falha ao criar o túnel ou usá-lo).
  * `webconnectivity` (ts-017, fase B, por amostra): `blocking` string ("dns", "tcp_ip", "http-failure", "http-diff") é anomalia; `false` não é; `null` é sem veredito.
    `https` nunca recebe veredito de bloqueio pela própria sonda (limitação do spec), então a taxa é piso, não estimativa.
"""
from __future__ import annotations

import re
from typing import Optional

LICENCA = "CC BY-NC-SA 4.0"
LICENCA_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
ATRIBUICAO = ("Dados: OONI (Open Observatory of Network Interference), https://ooni.org, bucket aberto `ooni-data-eu-fra` (Amazon Open Data), licença CC BY-NC-SA 4.0; "
              "agregados por ASN pelo Arandurapé (adaptação, sob a mesma licença).")

TESTES_LEVES = ("whatsapp", "telegram", "signal", "facebookmessenger", "tor", "psiphon")
TESTE_WEB = "webconnectivity"
TIPOS_TOR = ("dir_port", "obfs4", "or_port_dirauth", "or_port")
TIPOS_WEB = ("dns", "tcp_ip", "http-failure", "http-diff")
MIN_MEDICOES = 10                 # k-anonimato simples: célula (ASN × teste) com menos medições na janela não é publicada

_RE_ASN = re.compile(r"^AS(\d{1,10})$")


def asn_da_sonda(m: dict) -> Optional[int]:
    """ASN da sonda (`probe_asn` = "AS13285"); None se ausente, malformado ou de documentação/0 (a sonda pode ocultá-lo)."""
    r = _RE_ASN.match(str(m.get("probe_asn") or ""))
    if not r:
        return None
    a = int(r.group(1))
    return a if a > 0 else None


def _versao(m: dict) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(m.get("test_version") or ""))[:3])


def _bloqueado(v) -> bool:
    return v == "blocked"


def classificar(teste: str, m: dict) -> Optional[dict]:
    """`{asn, anomalia, partes, alvos}` de uma medição, ou None se inválida/descartada. `partes`: nomes dos componentes que a sonda declarou bloqueados."""
    if m.get("probe_cc") != "BR":
        return None
    asn = asn_da_sonda(m)
    if asn is None:
        return None
    tk = m.get("test_keys") or {}
    partes: list[str] = []
    alvos = None
    if teste == "whatsapp":
        for c, nome in (("registration_server_status", "registro"), ("whatsapp_endpoints_status", "endpoints"), ("whatsapp_web_status", "web")):
            if _bloqueado(tk.get(c)):
                partes.append(nome)
        if not any(c in tk for c in ("registration_server_status", "whatsapp_endpoints_status", "whatsapp_web_status")):
            return None
    elif teste == "telegram":
        if _bloqueado(tk.get("telegram_web_status")):
            partes.append("web")
        if tk.get("telegram_tcp_blocking") is True:
            partes.append("tcp")
        if tk.get("telegram_http_blocking") is True:
            partes.append("http")
        if not any(c in tk for c in ("telegram_web_status", "telegram_tcp_blocking", "telegram_http_blocking")):
            return None
    elif teste == "signal":
        if _versao(m) <= (0, 2, 3) or "signal_backend_status" not in tk:
            return None
        if _bloqueado(tk.get("signal_backend_status")):
            partes.append("backend")
    elif teste == "facebookmessenger":
        for c, nome in (("facebook_tcp_blocking", "tcp"), ("facebook_dns_blocking", "dns")):
            if tk.get(c) is True:
                partes.append(nome)
        if not any(c in tk for c in ("facebook_tcp_blocking", "facebook_dns_blocking")):
            return None
    elif teste == "tor":
        alvos = {}
        for t in TIPOS_TOR:
            tot, ok = tk.get(f"{t}_total"), tk.get(f"{t}_accessible")
            if isinstance(tot, int) and isinstance(ok, int) and tot >= 0:
                alvos[t] = [tot, min(ok, tot)]
        if not alvos:
            return None
        total = sum(v[0] for v in alvos.values())
        if total > 0 and sum(v[1] for v in alvos.values()) == 0:
            partes.append("nenhum_alvo")
    elif teste == "psiphon":
        if "failure" not in tk:
            return None
        if tk.get("failure") is not None:
            partes.append("tunel")
    elif teste == TESTE_WEB:
        b = tk.get("blocking")
        if isinstance(b, str) and b in TIPOS_WEB:
            partes.append(b)
        elif b not in (False, None):
            return None
        return {"asn": asn, "anomalia": bool(partes), "partes": partes, "alvos": None,
                "sem_veredito": b is None, "inacessivel": tk.get("accessible") is False}
    else:
        return None
    return {"asn": asn, "anomalia": bool(partes), "partes": partes, "alvos": alvos}


class Agregador:
    """Acumula `{teste: {asn: {n, anom, partes?, alvos?}}}` em memória; nenhuma medição individual é guardada."""

    def __init__(self) -> None:
        self.dados: dict[str, dict[str, dict]] = {}
        self.lidas = 0
        self.descartadas = 0

    def add(self, teste: str, m: dict) -> None:
        self.lidas += 1
        c = classificar(teste, m)
        if c is None:
            self.descartadas += 1
            return
        cel = self.dados.setdefault(teste, {}).setdefault(str(c["asn"]), {"n": 0, "anom": 0})
        cel["n"] += 1
        if c["anomalia"]:
            cel["anom"] += 1
        for p in c["partes"]:
            cel.setdefault("partes", {})
            cel["partes"][p] = cel["partes"].get(p, 0) + 1
        if c["alvos"]:
            cel.setdefault("alvos", {})
            for t, (tot, ok) in c["alvos"].items():
                a = cel["alvos"].setdefault(t, [0, 0])
                a[0] += tot
                a[1] += ok
        if teste == TESTE_WEB:
            if c["sem_veredito"]:
                cel["sem_veredito"] = cel.get("sem_veredito", 0) + 1
            if c["inacessivel"]:
                cel["inacessivel"] = cel.get("inacessivel", 0) + 1


def somar(celulas: list[dict]) -> dict:
    """Soma células (de vários dias) do mesmo ASN × teste."""
    out: dict = {"n": 0, "anom": 0}
    for c in celulas:
        out["n"] += c.get("n", 0)
        out["anom"] += c.get("anom", 0)
        for k in ("sem_veredito", "inacessivel"):
            if c.get(k):
                out[k] = out.get(k, 0) + c[k]
        for p, v in (c.get("partes") or {}).items():
            out.setdefault("partes", {})
            out["partes"][p] = out["partes"].get(p, 0) + v
        for t, (tot, ok) in (c.get("alvos") or {}).items():
            a = out.setdefault("alvos", {}).setdefault(t, [0, 0])
            a[0] += tot
            a[1] += ok
    return out


def mesclar(dest: dict, orig: dict) -> None:
    """Soma o agregado `orig` (`{teste: {asn: célula}}`) em `dest`, no lugar."""
    for teste, por_asn in orig.items():
        for asn, cel in por_asn.items():
            atual = dest.setdefault(teste, {}).get(asn)
            dest[teste][asn] = somar([atual, cel]) if atual else somar([cel])


ROTULOS = {
    "whatsapp": "WhatsApp", "telegram": "Telegram", "signal": "Signal", "facebookmessenger": "Facebook Messenger",
    "tor": "Tor", "psiphon": "Psiphon", "webconnectivity": "Web Connectivity (amostra)",
}
CRITERIOS = {
    "whatsapp": "A sonda declarou bloqueado o servidor de registro, os endpoints ou o WhatsApp Web (ts-018).",
    "telegram": "A sonda declarou bloqueado o Telegram Web ou o acesso TCP/HTTP aos data centers (ts-020).",
    "signal": "A sonda declarou bloqueado o backend do Signal (ts-029); medições de versão <= 0.2.3 foram descartadas (falsos positivos documentados).",
    "facebookmessenger": "A sonda declarou bloqueio TCP ou DNS dos endpoints do Messenger (ts-019).",
    "tor": "Nenhum alvo do Tor (autoridades de diretório, relays, pontes obfs4) foi acessível na medição (ts-023); a fração de alvos acessíveis por tipo vai à parte.",
    "psiphon": "A sonda não conseguiu criar o túnel Psiphon nem usá-lo (ts-015).",
    "webconnectivity": ("A sonda classificou o site medido como bloqueado por dns, tcp_ip, http-failure ou http-diff (ts-017); AMOSTRA de horas de cada dia; nenhum site é identificado; "
                        "https nunca recebe veredito de bloqueio da sonda, então o valor é um piso."),
}
AVISO = ("Veredito da PRÓPRIA sonda do OONI, calculado no aparelho do voluntário segundo o ooni/spec; não é o veredito do backend do OONI nem prova de censura. Pode ser filtro do cliente "
         "(controle parental, rede corporativa, VPN), falha do serviço medido ou falso positivo. Mostra o que foi medido, não a intenção de quem opera a rede.")
