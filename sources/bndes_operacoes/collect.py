# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Operações de financiamento do BNDES a operadoras de telecom (dados abertos do BNDES).

Fonte: `dadosabertos.bndes.gov.br`, conjunto `operacoes-financiamento` (CKAN), recurso "Operações não automáticas" (CSV latin-1, `;`, aspas, cabeçalho, ~20 MB, CNPJ completo e município
IBGE). Licença ODbL, com atribuição. Guarda só as operações de clientes cujo CNPJ básico está no universo de telecom (`core.universo_telecom`) e só pessoa jurídica (o CNPJ é de 14 dígitos).

NÃO entra o recurso "Operações indiretas automáticas" (1,2 GB): o CNPJ do cliente vem mascarado, então a linha não se liga a uma operadora. Fica fora do passo (registro no catálogo).

Entrada:  normalized/{date}/summary/anatel_{scm,smp,stfc,seac}.json.gz, sici_acessos.json.gz e (se houver) receita_cnpj.json.gz (universo).
Saída:    normalized/{date}/summary/bndes_operacoes.json.gz

Uso:
    python -m sources.bndes_operacoes.collect --date 2026-11-08 [--force]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from pathlib import Path

import httpx

from core import financiamento as fin
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.universo_telecom import basicos as universo_telecom
from core.site import USER_AGENT

CKAN = "https://dadosabertos.bndes.gov.br/api/3/action/package_show?id=operacoes-financiamento"
RECURSO = "Operações não automáticas"


def _recurso(client: httpx.Client) -> tuple[str, str]:
    """(url do CSV, data de modificação do conjunto)."""
    r = client.get(CKAN, timeout=60)
    r.raise_for_status()
    res = r.json()["result"]
    for x in res.get("resources", []):
        if (x.get("name") or "").startswith(RECURSO) and (x.get("format") or "").upper() == "CSV":
            return x["url"], (res.get("metadata_modified") or "")[:10]
    raise RuntimeError(f'recurso "{RECURSO}" ausente no conjunto do BNDES: a estrutura do portal pode ter mudado')


def _recorte(caminho: Path, universo: set[str]) -> tuple[int, dict[str, list[dict]]]:
    lidas, achadas = 0, {}
    with open(caminho, encoding="latin-1", newline="") as f:
        for r in csv.DictReader(f, delimiter=";", quotechar='"'):
            lidas += 1
            cnpj = fin.digitos(r.get("cnpj", ""))
            if len(cnpj) == 14 and cnpj[:8] in universo:
                achadas.setdefault(cnpj, []).append(fin.operacao_bndes(r))
    return lidas, achadas


def run(date_str: str, base: Path, log, force: bool = False) -> dict:
    dst = normalized_path(base, date_str, "summary", "bndes_operacoes.json.gz")
    universo = universo_telecom(base, date_str, log)
    tmpdir = base / "raw" / "_bndes_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        url, modificado = _recurso(client)
        if dst.exists() and not force and (read_json_gz(dst) or {}).get("dump_reference") == modificado:
            log.info("conjunto já coletado; use --force para repetir", dump_reference=modificado)
            return read_json_gz(dst)
        fd, tmp = tempfile.mkstemp(suffix=".csv", dir=str(tmpdir))
        try:
            with os.fdopen(fd, "wb") as f, client.stream("GET", url, timeout=600) as r:
                r.raise_for_status()
                for bloco in r.iter_bytes(1 << 20):
                    f.write(bloco)
            lidas, achadas = _recorte(Path(tmp), universo)
        finally:
            Path(tmp).unlink(missing_ok=True)
    for ops in achadas.values():
        ops.sort(key=lambda o: (o["data"] or "", o["contrato"]))
    saida = {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "BNDES — dados abertos (operações de financiamento, não automáticas)", "fonte_url": CKAN,
             "licenca": "ODbL", "dump_reference": modificado, "universo_cnpjs_basicos": len(universo), "linhas_lidas": lidas,
             "operacoes_guardadas": sum(len(v) for v in achadas.values()), "cnpjs": len(achadas), "operacoes": achadas}
    write_json_gz(dst, saida)
    log.info("bndes_operacoes gravado", caminho=str(dst), cnpjs=len(achadas), operacoes=saida["operacoes_guardadas"], linhas=lidas)
    return saida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Operações do BNDES a operadoras de telecom")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="coleta de novo mesmo que o conjunto não tenha mudado")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log, force=a.force)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
