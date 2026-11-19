# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
"""Confere os resultados do laboratório IPv6 (T7) contra `esperado.json`.

Roda fora do laboratório, só com a biblioteca padrão, sobre o diretório que o
`run_lab.sh` do v6bench preenche. Falha (código 1) se:
  - algum cenário não terminou `ok` (status/);
  - o `/auth/diag` de algum cenário difere do esperado (IP visto, versão,
    allowlist, nível) ou falta;
  - um X-Forwarded-For/X-Real-IP forjado pelo cliente mudou o IP visto;
  - alguma requisição do plano do ScanAPI falhou;
  - o log de uso do alvo está vazio ou contém algum endereço do laboratório
    (a regra de privacidade: o log de uso nunca grava IP).

Uso: python3 tests/ipv6/verificar.py RESULTADOS [tests/ipv6/esperado.json]
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

FORJADO = "203.0.113.9"
CAMPOS = ("ip_visto", "versao", "na_allowlist", "tier")


def _diag(res: Path, chave: str, sufixo: str = "") -> dict | None:
    arq = res / "diag" / f"{chave.replace('/', '-')}{sufixo}.json"
    try:
        return json.loads(arq.read_text())
    except (OSError, ValueError):
        return None


def verificar(res: Path, esperado: dict) -> list[str]:
    falhas: list[str] = []
    cenarios = {k: v for k, v in esperado.items() if not k.startswith("_")}

    for chave, exp in cenarios.items():
        cliente, sdom = chave.split("/")
        st_arq = res / "status" / f"{cliente}-{sdom}"
        st = st_arq.read_text().strip() if st_arq.exists() else "ausente"
        if st != "ok":
            falhas.append(f"{chave}: cenário terminou como '{st}'")

        diag = _diag(res, chave)
        if diag is None:
            falhas.append(f"{chave}: sem resposta do /auth/diag")
            continue
        for campo in CAMPOS:
            if diag.get(campo) != exp[campo]:
                falhas.append(f"{chave}: {campo} = {diag.get(campo)!r}, esperado {exp[campo]!r}")

        forjado = _diag(res, chave, "-forjado")
        if forjado is None:
            falhas.append(f"{chave}: sem resposta do /auth/diag com cabeçalho forjado")
        elif forjado.get("ip_visto") != diag.get("ip_visto"):
            falhas.append(f"{chave}: cabeçalho forjado mudou o IP visto para {forjado.get('ip_visto')!r}")

    relatorios = sorted(res.glob("*-report.csv"))
    if not relatorios:
        falhas.append("plano do ScanAPI: nenhum relatório")
    for rel in relatorios:
        with rel.open(newline="") as f:
            linhas = list(csv.DictReader(f))
        if not linhas:
            falhas.append(f"{rel.name}: relatório sem requisições")
        for linha in linhas:
            if str(linha.get("all_tests_passed", "")).strip() != "True":
                falhas.append(f"{rel.name}: falhou {linha.get('url')}")

    usos = sorted((res / "alvo" / "usage").glob("*.jsonl"))
    conteudo = "".join(u.read_text() for u in usos)
    if not conteudo.strip():
        falhas.append("log de uso do alvo: vazio ou ausente (a verificação de privacidade não teria valor)")
    enderecos = {exp["ip_visto"] for exp in cenarios.values()} | {FORJADO}
    vazados = sorted(e for e in enderecos if e in conteudo)
    if vazados:
        falhas.append(f"log de uso do alvo grava IP: {', '.join(vazados)}")

    return falhas


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    res = Path(argv[1])
    esp = Path(argv[2]) if len(argv) > 2 else Path(__file__).with_name("esperado.json")
    esperado = json.loads(esp.read_text())

    print(f"{'cliente/cenário':28} {'IP visto':18} {'versão':6} {'allowlist':9} nível")
    for chave in (k for k in esperado if not k.startswith("_")):
        d = _diag(res, chave) or {}
        print(f"{chave:28} {str(d.get('ip_visto', '-')):18} {str(d.get('versao', '-')):6} "
              f"{str(d.get('na_allowlist', '-')):9} {d.get('tier', '-')}")

    falhas = verificar(res, esperado)
    if falhas:
        print(f"\n{len(falhas)} falha(s):", file=sys.stderr)
        for f in falhas:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nT7 IPv6: tudo conforme o esperado.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
