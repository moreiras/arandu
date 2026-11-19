# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Região: quais ASNs "são" de cada município e os fatos de rede deles, para a página de município e de raio responderem sobre PTTs, trânsito e carregadores.

Entrada:  documentos de ASN (fragmentos `base` e `relacoes`, ou os `asns/{asn}.json` publicados), `sici_municipios.json.gz` e `sici_movel_municipios.json.gz`, `config/municipios-referencia.json`.
Saída:    published/{date}/territorio/regiao.json.gz — por município, os ASNs com o vínculo (SICI, sede, IPs geolocalizados), e uma tabela compacta por ASN.

Um ASN entra no município por um de três vínculos, todos INFERIDOS e rotulados assim:
  * `s` SICI: a operadora (CNPJ) declara acessos no município e o Registro.br liga o CNPJ ao ASN; guarda os acessos fixo e móvel;
  * `h` sede: o endereço do CNPJ do ASN (matriz) é o município;
  * `g` IPs geolocalizados: prefixos do ASN que a base DB-IP põe no município (precisão de cidade); guarda só a contagem, nunca o prefixo.
Só ASNs do Brasil entram nos municípios. A tabela por ASN inclui também os ASNs de fora que aparecem como trânsito ou carregador de algum deles, para saber em que PTTs estão.

Uso:
    python -m products.regiao.build --date 2026-11-03
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Optional

from core import compose
from core.common import configure_logging, data_dir, now_iso, published_path, today_str
from core.geoip import normaliza
from core.jsonio import carregar_json_gz, gravar_json_gz

_CONFIG = Path(__file__).resolve().parent.parent.parent / "config"
NIVEIS = {"confirmado": 0, "provavel": 1, "possivel": 2}
LIMITES = (
    "Inferência, não cadastro: o ASN entra no município por um de três vínculos (a operadora declara acessos ali no SICI; a sede do CNPJ está ali; a base DB-IP põe prefixos dele ali, com precisão de cidade). "
    "Um ASN grande aparece em todos os municípios onde a operadora declara acessos e não quer dizer que a rede dele está dentro do município. Provedor pequeno que compra trânsito de outro e não tem ASN próprio não aparece. "
    "PTT direto é sessão no próprio PTT; indireto é o ASN visto como origem de rotas no PTT por meio de outro ASN. Trânsito vem das relações inferidas (ARC v1, com probabilidade); carregador é o ASN vizinho "
    "observado nos caminhos dos looking glasses dos PTTs. Nenhuma posição de prefixo é publicada, só a contagem por município."
)


def _municipios_ref() -> dict[tuple[str, str], str]:
    ref = json.loads((_CONFIG / "municipios-referencia.json").read_text(encoding="utf-8"))
    return {(uf, normaliza(nome)): codigo for codigo, (nome, uf, _a) in ref.items()}


def documentos(base: Path, date_str: str) -> Iterator[tuple[int, dict]]:
    """(asn, documento) com os campos que o produto lê. No fluxo de fragmentos o documento final só existe depois do compose; no antigo lê os publicados."""
    if compose.ativo() and compose.fluxo_novo(base, date_str):
        yield from compose.iterar_documentos(base, date_str, ("base", "relacoes"))
        return
    pub = published_path(base, date_str)
    idx = json.loads((pub / "asns" / "index.json").read_text(encoding="utf-8")) if (pub / "asns" / "index.json").exists() else []
    for e in idx:
        p = pub / "asns" / f"{e['asn']}.json"
        if p.exists():
            yield e["asn"], json.loads(p.read_text(encoding="utf-8"))


def _limpa_nome(nome: str) -> str:
    """"AS4230 - CLARO S.A., BR" → "CLARO S.A., BR"."""
    return re.sub(r"^AS\d+\s*-\s*", "", nome or "").strip()


def _compacto(asn: int, d: dict) -> dict:
    prov = []
    for p in (d.get("relacoes") or {}).get("provedores") or []:
        nivel = NIVEIS.get(p.get("nivel"))
        if nivel is not None and p.get("asn") != asn:
            prov.append([p["asn"], round(100 * float(p.get("p") or 0)), nivel, _limpa_nome(p.get("nome") or "")])
    return {"n": d.get("name") or "", "br": bool(d.get("is_br")), "d": sorted(d.get("ixps_direct") or []), "o": sorted(d.get("ixps_origin") or []),
            "c": sorted({a for a in (d.get("upstreams") or []) if a != asn}), "p": prov}


def _geo_por_municipio(d: dict, por_nome: dict[tuple[str, str], str]) -> dict[str, int]:
    """Quantos prefixos (v4 + v6) do ASN a base põe em cada município. Cidade que não casa com um município é ignorada."""
    n: dict[str, int] = defaultdict(int)
    for chave in ("geo_prefixes_v4", "geo_prefixes_v6"):
        for g in (d.get(chave) or {}).values():
            if g.get("country") != "BR" or not g.get("uf") or not g.get("city"):
                continue
            ibge = por_nome.get((g["uf"], normaliza(g["city"])))
            if ibge:
                n[ibge] += 1
    return n


def calcular(docs: Iterable[tuple[int, dict]], sici: dict, movel: dict, por_nome: dict[tuple[str, str], str]) -> dict:
    tabela: dict[int, dict] = {}
    vinc: dict[str, dict] = defaultdict(lambda: {"s": {}, "h": [], "g": {}})
    for asn, d in docs:
        c = _compacto(asn, d)
        tabela[asn] = c
        if not c["br"]:
            continue
        sede = (d.get("geo_org") or {}).get("codigo_municipio_ibge")
        if sede:
            vinc[str(sede)]["h"].append(asn)
        for ibge, n in _geo_por_municipio(d, por_nome).items():
            vinc[ibge]["g"][str(asn)] = n
    for idx, campo in ((0, sici), (1, movel)):
        for ibge, m in (campo.get("municipios") or {}).items():
            for op in m.get("operadores") or []:
                for asn in op.get("asns") or []:
                    if asn not in tabela or not tabela[asn]["br"]:
                        continue
                    par = vinc[ibge]["s"].setdefault(str(asn), [0, 0])
                    par[idx] += int(op.get("acessos") or 0)
    membros = {int(a) for v in vinc.values() for k in ("s", "g") for a in v[k]} | {a for v in vinc.values() for a in v["h"]}
    precisa = set(membros)
    for a in membros:
        precisa.update(c for c in tabela[a]["c"])
        precisa.update(p[0] for p in tabela[a]["p"])
    asns = {}
    for a in sorted(precisa):
        t = tabela.get(a)
        if t is None:
            # trânsito sem documento próprio: só o nome que as relações trazem
            nome = next((p[3] for m in membros for p in tabela[m]["p"] if p[0] == a), "")
            asns[str(a)] = {"n": nome, "m": 0, "d": [], "o": [], "c": [], "p": []}
        elif a in membros:
            asns[str(a)] = {"n": t["n"], "m": 1, "d": t["d"], "o": t["o"], "c": t["c"], "p": [[p[0], p[1], p[2]] for p in t["p"]]}
        else:
            asns[str(a)] = {"n": t["n"], "m": 0, "d": t["d"], "o": t["o"], "c": [], "p": []}
    for a, t in asns.items():             # nomes de trânsito vindos das relações, quando o documento não tem nome
        if not t["n"]:
            t["n"] = next((p[3] for m in membros for p in tabela[m]["p"] if str(p[0]) == a), "")
    municipios = {i: {"s": v["s"], "h": sorted(v["h"]), "g": v["g"]} for i, v in sorted(vinc.items()) if v["s"] or v["h"] or v["g"]}
    return {"asns": asns, "municipios": municipios}


def _nomes_ptts(pub: Path) -> dict[str, str]:
    """Código → nome de cada PTT, dos documentos `ixps/{code}.json` publicados."""
    out: dict[str, str] = {}
    for f in sorted((pub / "ixps").glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        nome = doc.get("name") if isinstance(doc, dict) else None
        if nome:
            out[f.stem] = nome
    return out


def publicar_regiao(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    sici = carregar_json_gz(pub / "sici_municipios.json.gz") or {}
    movel = carregar_json_gz(pub / "sici_movel_municipios.json.gz") or {}
    docs = list(documentos(base, date_str))
    if not docs:
        log.info("documentos de ASN ausentes: regiao não gerada")
        return {}
    r = calcular(docs, sici, movel, _municipios_ref())
    destino = pub / "territorio"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "regiao.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "natureza": "inferido", "limites": LIMITES,
        "fontes": {"sici": sici.get("mes_referencia"), "sici_movel": movel.get("mes_referencia"), "geo": "DB-IP Lite (cidade)", "relacoes": "ARC v1", "ptts": "looking glasses do IX.br"},
        "ptts_nomes": _nomes_ptts(pub), **r})
    log.info("regiao written", municipios=len(r["municipios"]), asns=len(r["asns"]))
    return {"municipios": len(r["municipios"]), "asns": len(r["asns"])}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASNs por município e fatos de rede para a página de município")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; o produto é sempre recalculado")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        publicar_regiao(data_dir(), a.date, log)
    except Exception:
        log.exception("falha no cálculo da região")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
