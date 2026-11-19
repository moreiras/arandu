# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Listas de numeração do Registro.br e do LACNIC → normalizado. Fonte derivada: lê o que `registrobr_listas` e `lacnic_listas` guardaram em `raw/`.

Entrada:     data/raw/{date}/summary/{registrobr-transferencias-diretas (+ a variante -lacnic), registrobr-recuperacao, registrobr-recuperados,
             lacnic-transfers}-{date}.gz (a origem só mantém a versão atual; o arquivo do dia vem do nosso bruto)
Normalizado: data/normalized/{date}/summary/ipv4_listas.json.gz   {transferencias_registrobr, transferencias_lacnic, recuperacao, recuperados, resumo}

`primeira_vez_visto` é a primeira data de snapshot em que o registro aparece no nosso bruto; o que já estava na primeira data coletada leva `anterior_a_coleta: true` (a data real
é anterior: as listas não dizem quando entraram). O normalizado guarda os nomes como vêm; a máscara de pessoa física é aplicada só na publicação.

Uso:
    python -m sources.ipv4_listas.enrich --date 2026-11-01
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Callable, Optional

from core import ipv4_listas as L
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz

LISTAS = {
    "transferencias_registrobr": ("registrobr-transferencias-diretas", "texto", L.parse_transferencias_registrobr),
    "recuperacao": ("registrobr-recuperacao", "texto", L.parse_recuperacao),
    "recuperados": ("registrobr-recuperados", "texto", L.parse_recuperados),
    "transferencias_lacnic": ("lacnic-transfers", "json", L.parse_lacnic_log),
}
MINIMOS = {"transferencias_registrobr": 1000, "transferencias_lacnic": 1000, "recuperados": 1000}          # medidos: ~1,4 mil, ~1,9 mil e ~2,9 mil; menos que isso é arquivo truncado


def _ler(caminho: Path, tipo: str) -> str:
    dados = gzip.decompress(caminho.read_bytes())
    return dados.decode("latin-1" if tipo == "texto" else "utf-8")


def _arquivo(base: Path, data: str, prefixo: str) -> Optional[Path]:
    p = raw_path(base, data, "summary") / f"{prefixo}-{data}.gz"
    return p if p.exists() else None


def _chave(lista: str, r: dict) -> str:
    return r["id"] if "id" in r else f"{r['tipo']}:{r['recurso']}:{r.get('inicio', '')}"


def datas_com_bruto(base: Path, prefixo: str, ate: str) -> list[str]:
    raiz = base / "raw"
    return sorted(d.name for d in raiz.iterdir() if d.is_dir() and d.name <= ate and (d / "summary" / f"{prefixo}-{d.name}.gz").exists()) if raiz.exists() else []


def primeiras_vistas(base: Path, lista: str, ate: str, atual: set[str]) -> tuple[dict[str, str], Optional[str]]:
    """{chave: primeira data em que apareceu} varrendo o bruto das datas até `ate`, e a primeira data com bruto (para marcar `anterior_a_coleta`)."""
    prefixo, tipo, parser = LISTAS[lista]
    datas = datas_com_bruto(base, prefixo, ate)
    vistas: dict[str, str] = {}
    for d in datas:
        try:
            regs, _ = parser(_ler(raw_path(base, d, "summary") / f"{prefixo}-{d}.gz", tipo))
        except Exception:
            continue
        for r in regs:
            vistas.setdefault(_chave(lista, r), d)
    return vistas, (datas[0] if datas else None)


def normalizar(base: Path, date_str: str, log) -> dict:
    saida: dict = {}
    resumo: dict = {}
    extras: dict = {}
    for lista, (prefixo, tipo, parser) in LISTAS.items():
        arq = _arquivo(base, date_str, prefixo)
        if arq is None:
            raise FileNotFoundError(f"ipv4_listas: falta o bruto {prefixo}-{date_str}.gz")
        regs, ign = parser(_ler(arq, tipo))
        if len(regs) < MINIMOS.get(lista, 1):
            raise RuntimeError(f"ipv4_listas: {lista} tem só {len(regs)} registros (esperado ≥ {MINIMOS.get(lista, 1)}); arquivo truncado?")
        if lista == "transferencias_registrobr":                    # a variante `-lacnic` traz o conjunto original e a data do registro original
            extra = _arquivo(base, date_str, "registrobr-transferencias-diretas-lacnic")
            if extra is not None:
                comp = {r["id"]: r for r in L.parse_transferencias_registrobr(_ler(extra, tipo))[0]}
                for r in regs:
                    c = comp.get(r["id"])
                    if c:
                        r["blocos_originais"], r["data_registro_original"] = c.get("blocos_originais"), c.get("data_registro_original")
                extras["transferencias_registrobr_com_conjunto_original"] = len(comp)
        vistas, primeira = primeiras_vistas(base, lista, date_str, {_chave(lista, r) for r in regs})
        for r in regs:
            v = vistas.get(_chave(lista, r))
            r["primeira_vez_visto"] = v
            r["anterior_a_coleta"] = v == primeira
        saida[lista] = regs
        resumo[lista] = {"registros": len(regs), "ignoradas": len(ign), "primeira_data_coletada": primeira, "novos_na_data": sum(1 for r in regs if r["primeira_vez_visto"] == date_str and not r["anterior_a_coleta"])}
        if ign:
            log.warning("ipv4_listas: linhas ignoradas", lista=lista, n=len(ign), exemplo=ign[0][:160])
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "ipv4_listas.json.gz", {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Registro.br (ftp.registro.br/pub/numeracao) e LACNIC (ftp.lacnic.net/pub/stats/lacnic)",
                                                    "resumo": resumo, "resumo_extra": extras, **saida})
    log.info("ipv4_listas written", **{k: v["registros"] for k, v in resumo.items()})
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Normaliza as listas de numeração do Registro.br e do LACNIC")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        normalizar(data_dir(), a.date, log)
    except Exception:
        log.exception("falha ao normalizar ipv4_listas")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
