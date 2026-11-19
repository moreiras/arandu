# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sub-asignações de IPv4 (aluguel regulado, política LAC-2025-5): **adaptador com esquema HIPOTÉTICO**, pronto e desativado.

Até 2026-11-02 não existe fonte oficial: a bitácora pública da política só será publicada depois que o LACNIC e o Registro.br a regulamentarem, e o formato é desconhecido. O vigia de diretórios
(`sources/ipv4_vigia`) avisa no dia em que aparecer um arquivo novo. Este módulo define o esquema que **supomos** (bloco, ASN do receptor, início, fim, cedente, RIR) para que, quando o formato
real for conhecido, só o `parse` precise mudar. Nada aqui é publicado como fato enquanto a fonte não estiver ativada (`ARANDU_SUBASIGNACAO_URL`).

`validar` aplica as regras que o estudo (seção 4.3) extrai da política: o receptor origina o bloco? há ROA para ele? o bloco está entre /24 e /22? o receptor tem ASN e IPv6? passaram 3 anos desde a
última transferência ou recuperação do bloco? o bloco não é infraestrutura crítica? Cada validação devolve `ok` verdadeiro, falso ou `None` (sem dado para decidir): nunca se inventa o resultado.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import ipaddress
import json
from typing import Optional

from core.ipv4_listas import normalizar_cidr

PRAZO_ANOS = 3
VALIDACOES = {
    "receptor_origina": "O ASN do receptor origina o bloco na tabela global",
    "tem_roa": "Existe ROA do bloco para o ASN do receptor",
    "tamanho": "O bloco está entre /24 e /22",
    "receptor_ipv6": "O ASN do receptor tem IPv6",
    "prazo_3_anos": "Passaram 3 anos desde a última transferência ou recuperação do bloco",
    "nao_infra_critica": "O bloco não é de infraestrutura crítica",
}


def parse(conteudo: str | bytes, formato: str = "json") -> tuple[list[dict], list[str]]:
    """Registros de sub-asignação no esquema hipotético: `bloco`, `receptor_asn`, `inicio`, `fim` (opcional), `cedente_asn` (opcional), `rir` (opcional). JSON (lista ou `{subasignacoes: [...]}`) ou CSV
    com esses cabeçalhos. Registro inválido é contado e devolvido, não descartado em silêncio."""
    txt = conteudo.decode("utf-8") if isinstance(conteudo, bytes) else conteudo
    if formato == "csv":
        linhas = list(csv.DictReader(io.StringIO(txt)))
    else:
        d = json.loads(txt)
        linhas = d.get("subasignacoes", d) if isinstance(d, dict) else d
    regs, ign = [], []
    for r in linhas:
        try:
            bloco = normalizar_cidr(str(r["bloco"]))
            asn = int(str(r["receptor_asn"]).upper().removeprefix("AS"))
            ini = dt.date.fromisoformat(str(r["inicio"])[:10])
            fim = dt.date.fromisoformat(str(r["fim"])[:10]) if r.get("fim") else None
            if not bloco or ":" in bloco or (fim and fim < ini):
                raise ValueError("bloco ou datas inválidos")
        except (KeyError, ValueError, TypeError):
            ign.append(json.dumps(r, ensure_ascii=False)[:200])
            continue
        ced = r.get("cedente_asn")
        regs.append({"id": hashlib.sha1(f"{bloco}|{asn}|{ini}".encode()).hexdigest()[:12], "bloco": bloco, "receptor_asn": asn, "inicio": ini.isoformat(), "fim": fim.isoformat() if fim else None,
                     "cedente_asn": int(str(ced).upper().removeprefix("AS")) if ced not in (None, "") else None, "rir": r.get("rir") or None})
    return regs, ign


def ativa(hoje: dt.date, r: dict) -> bool:
    return r["inicio"] <= hoje.isoformat() and (r["fim"] is None or r["fim"] >= hoje.isoformat())


def validar(r: dict, origens: Optional[set[int]], roas: Optional[set[int]], receptor_ipv6: Optional[bool], ultimo_evento: Optional[str], criticos: Optional[list[str]]) -> dict[str, Optional[bool]]:
    """Resultado de cada validação: True, False ou None (sem dado). `origens`/`roas`: ASNs que originam / têm ROA do bloco; `ultimo_evento`: data da última transferência ou recuperação do bloco
    (ou None se nenhuma); `criticos`: blocos de infraestrutura crítica (None = lista ausente)."""
    net = ipaddress.ip_network(r["bloco"])
    out: dict[str, Optional[bool]] = {
        "receptor_origina": None if origens is None else r["receptor_asn"] in origens,
        "tem_roa": None if roas is None else r["receptor_asn"] in roas,
        "tamanho": 22 <= net.prefixlen <= 24,
        "receptor_ipv6": receptor_ipv6,
        "prazo_3_anos": True if ultimo_evento is None else (dt.date.fromisoformat(r["inicio"]) - dt.date.fromisoformat(ultimo_evento)).days >= 365 * PRAZO_ANOS,
        "nao_infra_critica": None if criticos is None else not any(net.overlaps(ipaddress.ip_network(c)) for c in criticos),
    }
    return out


def parse_infra_critica(texto: str) -> list[str]:
    """Blocos IPv4 do `critical-infra-AAAAMMDD` do LACNIC (`rir|pais|tipo|recurso|cantidad|fecha|estado|orgid|id_documento|nombre`); o `recurso` é início do bloco e `cantidad` o número de endereços."""
    from core.ipv4_listas import faixa_para_cidrs
    out = []
    for ln in texto.splitlines():
        c = ln.split("|")
        if len(c) < 5 or c[2].lower() != "ipv4":
            continue
        try:
            out.extend(faixa_para_cidrs(c[3], int(c[4])))
        except ValueError:
            continue
    return out
