# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Parsers das listas de numeração do Registro.br e do LACNIC: transferências, recuperação, recuperados e o `delegated-extended`.

Formatos (verificados em 2026-11-02):
  * Registro.br `transferencias-diretas-latest`: `data|origem|RIR origem|país|destino|RIR destino|país|recurso`; a variante `-lacnic-` acrescenta `|conjunto original|data do registro
    original`. Latin-1; blocos em CIDR com zeros omitidos (`200.234.0/22`) em alguns registros.
  * `recuperacao-latest`: `recurso|início - fim` (blocos e ASNs); `recuperados-latest`: um recurso por linha.
  * LACNIC `transfers_latest.json`: `{transfers: [{ip4nets: [{original_set, transfer_set}], source/recipient_organization, ..., transfer_date}]}`.
  * `delegated-lacnic-extended`: `registro|país|tipo|início|quantidade|data|status|opaque-id`; a quantidade de IPv4 é número de endereços (não precisa ser potência de 2).

Linha que não casa com o formato é **contada e devolvida** (`ignoradas`), nunca descartada em silêncio. Nome de pessoa física provável é mascarado só na saída pública (`mascarar_nome`);
a heurística é conservadora para o que aparece como pessoa jurídica: só mascara nome brasileiro sem nenhum marcador de empresa.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import unicodedata
from typing import Iterable, Optional

RIRS_BR = {"NICBR", "LACNIC"}
_MARCADORES_PJ = re.compile(
    r"\b(LTDA|LTD|ME|EPP|EIRELI|MEI|S/?A|S\.A\.?|SA|SS|CIA|COMPANHIA|ASSOCIACAO|ASSOC|FUNDACAO|COOPERATIVA|COOP|INSTITUTO|UNIVERSIDADE|FACULDADE|ESCOLA|PREFEITURA|MUNICIPIO|"
    r"CAMARA|SECRETARIA|MINISTERIO|TRIBUNAL|BANCO|TELECOM\w*|TELECOMUNICACOES|COMUNICACOES|COMUNICACAO|INTERNET|REDES?|NET|TECNOLOGIA|INFORMATICA|SERVICOS|SISTEMAS|DIGITAL|"
    r"PROVEDOR|FIBRA|WIRELESS|LINK|DADOS|CABO|TV|SOLUCOES|GRUPO|HOLDING|EMPRESA|CONSULTORIA|COMERCIO|INDUSTRIA|SERVICE|SERVICES|NETWORKS?|TECHNOLOGY|LLC|INC|CORP|GMBH)\b")


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def tipo_pessoa(nome: str, pais: Optional[str] = "BR") -> str:
    """`pj` (tem marcador de empresa ou não é do Brasil) ou `pf_provavel` (nome brasileiro sem nenhum marcador de empresa). Heurística: só orienta a máscara."""
    if (pais or "BR") != "BR" or not nome:
        return "pj"
    n = sem_acento(nome)
    if _MARCADORES_PJ.search(n) or re.search(r"[0-9]{3,}", n):
        return "pj"
    return "pf_provavel" if len(n.split()) >= 2 else "pj"


def mascarar_nome(nome: str, pais: Optional[str] = "BR") -> str:
    """Nome para a saída pública: pessoa física provável vira `Pessoa física`; o resto passa."""
    return "Pessoa física" if tipo_pessoa(nome, pais) == "pf_provavel" else nome


def normalizar_cidr(texto: str) -> Optional[str]:
    """`200.234.0/22` → `200.234.0.0/22`; IPv4 ou IPv6; `None` se não for um bloco válido."""
    t = texto.strip()
    if not t:
        return None
    ip, _, pref = t.partition("/")
    try:
        if ":" in ip:
            return str(ipaddress.ip_network(t, strict=False))
        partes = ip.split(".")
        if len(partes) > 4 or not all(p.isdigit() for p in partes):
            return None
        ip = ".".join(partes + ["0"] * (4 - len(partes)))
        return str(ipaddress.ip_network(f"{ip}/{pref}" if pref else f"{ip}/32", strict=False))
    except ValueError:
        return None


def enderecos(cidrs: Iterable[str]) -> int:
    return sum(ipaddress.ip_network(c).num_addresses for c in cidrs if ":" not in c)


def faixa_para_cidrs(inicio: str, quantidade: int) -> list[str]:
    """Bloco do `delegated` (início + número de endereços) → lista mínima de CIDRs."""
    a = ipaddress.IPv4Address(inicio)
    return [str(n) for n in ipaddress.summarize_address_range(a, ipaddress.IPv4Address(int(a) + quantidade - 1))]


def _id(*partes: object) -> str:
    return hashlib.sha1("|".join(str(p) for p in partes).encode()).hexdigest()[:12]


def _blocos(resource: str) -> list[str]:
    return [b for b in (normalizar_cidr(x) for x in re.split(r"[ ,;]+", resource.strip())) if b]


def parse_transferencias_registrobr(texto: str) -> tuple[list[dict], list[str]]:
    """Lista de transferências diretas do Registro.br (com ou sem as duas últimas colunas). Devolve (registros, linhas ignoradas)."""
    regs, ign = [], []
    for ln in texto.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        c = ln.split("|")
        if len(c) < 8 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c[0]):
            ign.append(ln)
            continue
        blocos = _blocos(c[7])
        if not blocos:
            ign.append(ln)
            continue
        r = {"id": _id("rb", c[0], c[1], c[4], c[7]), "data": c[0], "origem": c[1], "rir_origem": c[2], "pais_origem": c[3], "destino": c[4], "rir_destino": c[5], "pais_destino": c[6],
             "blocos": blocos, "enderecos": enderecos(blocos)}
        if len(c) >= 10:
            r["blocos_originais"] = _blocos(c[8])
            r["data_registro_original"] = c[9].strip() or None
        regs.append(r)
    return regs, ign


def parse_recuperacao(texto: str) -> tuple[list[dict], list[str]]:
    regs, ign = [], []
    for ln in texto.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        rec, _, janela = ln.partition("|")
        m = re.fullmatch(r"\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})\s*", janela)
        if not m or not rec.strip():
            ign.append(ln)
            continue
        regs.append({**_recurso(rec.strip()), "inicio": m.group(1), "fim": m.group(2)})
    return regs, ign


def parse_recuperados(texto: str) -> tuple[list[dict], list[str]]:
    regs, ign = [], []
    for ln in texto.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        r = _recurso(ln.strip())
        (regs if r["tipo"] != "invalido" else ign).append(r if r["tipo"] != "invalido" else ln)
    return regs, ign


def _recurso(s: str) -> dict:
    if re.fullmatch(r"\d+", s):
        return {"tipo": "asn", "recurso": s}
    b = normalizar_cidr(s)
    if b:
        return {"tipo": "bloco" if ":" not in b else "bloco6", "recurso": b}
    return {"tipo": "invalido", "recurso": s}


def parse_lacnic_log(texto: str) -> tuple[list[dict], list[str]]:
    """Log de transferências do LACNIC (JSON). Só IPv4 entra em `blocos` (o log traz também ASNs e IPv6, hoje vazios)."""
    ign: list[str] = []
    doc = json.loads(texto)
    regs = []
    for t in doc.get("transfers", []):
        try:
            orig = [b for n in t.get("ip4nets", []) for s in n.get("original_set", []) for b in faixa_ip(s)]
            tr = [b for n in t.get("ip4nets", []) for s in n.get("transfer_set", []) for b in faixa_ip(s)]
            so, ro = t.get("source_organization") or {}, t.get("recipient_organization") or {}
            data = (t.get("transfer_date") or "")[:10]
            regs.append({"id": _id("lc", data, so.get("name"), ro.get("name"), ",".join(tr)), "data": data, "origem": so.get("name"), "pais_origem": so.get("country_code"),
                         "rir_origem": t.get("source_rir"), "destino": ro.get("name"), "pais_destino": ro.get("country_code"), "rir_destino": t.get("recipient_rir"),
                         "blocos": tr, "blocos_originais": orig, "enderecos": enderecos(tr), "asns": t.get("asns") or [], "ipv6": bool(t.get("ip6nets")),
                         "data_registro_original": (t.get("source_registration_date") or "")[:10] or None, "tipo_log": t.get("type")})
        except (KeyError, ValueError, TypeError):
            ign.append(json.dumps(t)[:200])
    return regs, ign


def faixa_ip(s: dict) -> list[str]:
    a, b = ipaddress.ip_address(s["start_address"]), ipaddress.ip_address(s["end_address"])
    return [str(n) for n in ipaddress.summarize_address_range(a, b)]


def parse_delegated_ipv4(texto: str) -> tuple[dict[str, dict], list[str]]:
    """IPv4 do `delegated-lacnic-extended`: {início/quantidade: {cc, status, data, opaque, inicio, quantidade}}. A chave identifica o registro no diff diário."""
    blocos: dict[str, dict] = {}
    ign: list[str] = []
    for ln in texto.splitlines():
        if not ln.startswith("lacnic|") or "|ipv4|" not in ln:
            continue
        c = ln.split("|")
        if len(c) < 7 or c[3] == "*":
            if c[3] != "*":
                ign.append(ln)
            continue
        try:
            q = int(c[4])
            ipaddress.IPv4Address(c[3])
        except ValueError:
            ign.append(ln)
            continue
        blocos[f"{c[3]}/{q}"] = {"cc": c[1] or None, "status": c[6], "data": c[5] or None, "opaque": (c[7] if len(c) > 7 else "") or None, "inicio": c[3], "quantidade": q}
    return blocos, ign
