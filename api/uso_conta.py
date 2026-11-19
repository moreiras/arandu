# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Registro de uso por conta, para controle de acesso e prevenção de abuso, e o perfil de uso mostrado ao titular.

Separado do log de uso anônimo (`api/usage_log.py`, hash diário, sem identificador): aqui há `conta_id` (UUID interno, nunca o e-mail), então é dado
pessoal e segue a seção 2.3 de `/privacidade`: sem IP, sem querystring; detalhe por 90 dias; depois só contagens por dia e classe, por 12 meses;
ao apagar a conta, o detalhe sai e as contagens perdem o `conta_id`. Só a API escreve (o MCP, somente leitura, manda eventos a ela).
"""
from __future__ import annotations

import json
import threading
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import structlog

_log = structlog.get_logger(__name__)
_lock = threading.Lock()
RETENCAO_DETALHE_DIAS = 90
RETENCAO_AGREGADO_DIAS = 366
ORIGENS = ("site", "api", "mcp")


def _dir(data_dir: Path) -> Path:
    return Path(data_dir) / "ops" / "uso_conta"


def registrar(data_dir: Path, conta_id: str, origem: str, rota: str, status: int, bytes_: int = 0, ms: float = 0.0, classe: str = "n/d") -> None:
    """Uma linha por requisição. `rota` é o modelo da rota (sem parâmetros) e nunca contém querystring."""
    try:
        agora = datetime.now(timezone.utc)
        linha = {"ts": agora.strftime("%Y-%m-%dT%H:%M:%SZ"), "conta": conta_id, "origem": origem if origem in ORIGENS else "api", "rota": rota.split("?", 1)[0][:200], "status": int(status), "bytes": int(bytes_), "ms": round(float(ms), 1), "classe": classe}
        with _lock:
            d = _dir(data_dir)
            d.mkdir(parents=True, exist_ok=True)
            with open(d / f"{agora:%Y-%m-%d}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(linha, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception as exc:  # noqa: BLE001 — o registro nunca derruba a resposta
        _log.debug("uso_conta_falha", erro=type(exc).__name__)


def _linhas(arq: Path):
    try:
        with open(arq, encoding="utf-8") as f:
            for ln in f:
                try:
                    yield json.loads(ln)
                except ValueError:
                    continue
    except OSError:
        return


def resumo_dias(data_dir: Path, conta_id: str, dias: int = 30, hoje: Optional[date] = None) -> list[dict]:
    """Contagem por dia (do detalhe e dos agregados) dos últimos `dias`, para o perfil: só números, sem rotas."""
    hoje = hoje or datetime.now(timezone.utc).date()
    ini = hoje - timedelta(days=dias - 1)
    por_dia: Counter = Counter()
    d = _dir(data_dir)
    for arq in sorted(d.glob("????-??-??.jsonl")):
        if ini <= date.fromisoformat(arq.stem) <= hoje:
            por_dia[arq.stem] += sum(1 for ln in _linhas(arq) if ln.get("conta") == conta_id)
    agg = d / "agregado.jsonl"
    for ln in _linhas(agg):
        if ln.get("conta") == conta_id and ini <= date.fromisoformat(ln["dia"]) <= hoje and ln["dia"] not in por_dia:
            por_dia[ln["dia"]] += ln["n"]
    return [{"dia": k, "chamadas": v} for k, v in sorted(por_dia.items())]


def chamadas_no_dia(data_dir: Path, conta_id: str, dia: Optional[date] = None) -> int:
    dia = dia or datetime.now(timezone.utc).date()
    return sum(1 for ln in _linhas(_dir(data_dir) / f"{dia:%Y-%m-%d}.jsonl") if ln.get("conta") == conta_id)


def manutencao(data_dir: Path, hoje: Optional[date] = None) -> dict:
    """Agrega por (dia, conta, origem, classe) o detalhe com mais de 90 dias, apaga-o e descarta agregados com mais de 12 meses."""
    hoje = hoje or datetime.now(timezone.utc).date()
    d = _dir(data_dir)
    if not d.exists():
        return {"agregados_novos": 0, "detalhes_apagados": 0, "agregados_descartados": 0}
    corte = hoje - timedelta(days=RETENCAO_DETALHE_DIAS)
    novos: Counter = Counter()
    velhos = [a for a in d.glob("????-??-??.jsonl") if date.fromisoformat(a.stem) < corte]
    for arq in velhos:
        for ln in _linhas(arq):
            novos[(arq.stem, ln.get("conta"), ln.get("origem"), ln.get("classe", "n/d"))] += 1
    agg = d / "agregado.jsonl"
    existentes = list(_linhas(agg))
    limite = hoje - timedelta(days=RETENCAO_AGREGADO_DIAS)
    mantidos = [ln for ln in existentes if date.fromisoformat(ln["dia"]) >= limite]
    mantidos += [{"dia": k[0], "conta": k[1], "origem": k[2], "classe": k[3], "n": n} for k, n in sorted(novos.items(), key=lambda kv: kv[0][0])]
    if velhos or len(mantidos) != len(existentes):
        tmp = agg.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(ln, ensure_ascii=False, separators=(",", ":")) + "\n" for ln in mantidos), encoding="utf-8")
        tmp.replace(agg)
    for arq in velhos:
        arq.unlink(missing_ok=True)
    return {"agregados_novos": len(novos), "detalhes_apagados": len(velhos), "agregados_descartados": len(existentes) - len([ln for ln in existentes if date.fromisoformat(ln["dia"]) >= limite])}


def apagar_conta(data_dir: Path, conta_id: str) -> dict:
    """Exclusão efetiva: some o detalhe da conta; nos agregados o `conta_id` é retirado (a contagem fica, sem ligação com ninguém)."""
    d = _dir(data_dir)
    if not d.exists():
        return {"linhas_apagadas": 0, "agregados_anonimizados": 0}
    apagadas = 0
    for arq in d.glob("????-??-??.jsonl"):
        todas = list(_linhas(arq))
        mantidas = [ln for ln in todas if ln.get("conta") != conta_id]
        if len(mantidas) != len(todas):
            apagadas += len(todas) - len(mantidas)
            tmp = arq.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(ln, ensure_ascii=False, separators=(",", ":")) + "\n" for ln in mantidas), encoding="utf-8")
            tmp.replace(arq)
    anon = 0
    agg = d / "agregado.jsonl"
    if agg.exists():
        linhas = list(_linhas(agg))
        for ln in linhas:
            if ln.get("conta") == conta_id:
                ln["conta"] = None
                anon += 1
        if anon:
            tmp = agg.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(ln, ensure_ascii=False, separators=(",", ":")) + "\n" for ln in linhas), encoding="utf-8")
            tmp.replace(agg)
    return {"linhas_apagadas": apagadas, "agregados_anonimizados": anon}
