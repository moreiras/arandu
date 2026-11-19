# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Sanções administrativas (CGU: CEIS e CNEP, Portal da Transparência) a empresas de telecom.

Fonte: ZIPs diários `https://portaldatransparencia.gov.br/download-de-dados/{ceis,cnep}/AAAAMMDD` (redirecionam para `dadosabertos-download.cgu.gov.br`; sem chave). Nem todo dia tem arquivo
(fim de semana e atraso respondem 403): o coletor tenta a data pedida e volta até 10 dias. CSV latin-1, `;`, aspas, com cabeçalho. Guarda só pessoa jurídica (TIPO DE PESSOA = J, CNPJ de 14
dígitos) do universo de telecom (`core.universo_telecom`); a linha de pessoa física (CPF) é descartada na leitura e nunca grava nada. Linguagem de evidência: é o registro do órgão
sancionador, com a data de referência do arquivo; o coletor não julga nem classifica a sanção.

Entrada:  normalized/{date}/summary/anatel_*.json.gz, sici_acessos.json.gz e (se houver) receita_cnpj.json.gz.
Saída:    normalized/{date}/summary/cgu_ceis_cnep.json.gz

Uso:
    python -m sources.cgu_ceis_cnep.collect --date 2026-11-08 [--force]
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import httpx

from core import financiamento as fin
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.universo_telecom import basicos as universo_telecom
from core.site import USER_AGENT

URL = "https://portaldatransparencia.gov.br/download-de-dados/{cad}/{dia}"
CADASTROS = ("ceis", "cnep")
VOLTA_DIAS = 10


def _baixar(client: httpx.Client, cad: str, ate: date, log) -> tuple[str, bytes]:
    """(AAAAMMDD, ZIP) do arquivo mais recente até `ate`; 403/404 é "sem arquivo neste dia"."""
    for i in range(VOLTA_DIAS + 1):
        dia = (ate - timedelta(days=i)).strftime("%Y%m%d")
        r = client.get(URL.format(cad=cad, dia=dia), timeout=300)
        if r.status_code in (403, 404):
            log.info("sem arquivo neste dia", cadastro=cad, dia=dia, status=r.status_code)
            continue
        r.raise_for_status()
        return dia, r.content
    raise RuntimeError(f"{cad}: nenhum arquivo nos últimos {VOLTA_DIAS} dias a partir de {ate}")


def _recorte(conteudo: bytes, cad: str, universo: set[str]) -> tuple[int, int, dict[str, list[dict]]]:
    """(linhas, linhas de pessoa jurídica, sanções por CNPJ de 14 dígitos)."""
    lidas = pj = 0
    achadas: dict[str, list[dict]] = {}
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        membro = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(membro) as f:
            for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";", quotechar='"'):
                lidas += 1
                if (r.get("TIPO DE PESSOA") or "").strip().upper() != "J":
                    continue
                pj += 1
                cnpj = fin.digitos(r.get("CPF OU CNPJ DO SANCIONADO", ""))
                if len(cnpj) == 14 and cnpj[:8] in universo:
                    achadas.setdefault(cnpj, []).append(fin.sancao(r, cad.upper()))
    return lidas, pj, achadas


def run(date_str: str, base: Path, log, force: bool = False) -> dict:
    dst = normalized_path(base, date_str, "summary", "cgu_ceis_cnep.json.gz")
    universo = universo_telecom(base, date_str, log)
    ate = date.fromisoformat(date_str)
    sancoes: dict[str, list[dict]] = {}
    arquivos: dict[str, str] = {}
    lidas = pj = 0
    with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for cad in CADASTROS:
            dia, zipado = _baixar(client, cad, ate, log)
            arquivos[cad.upper()] = f"{dia[:4]}-{dia[4:6]}-{dia[6:]}"
            a, b, achadas = _recorte(zipado, cad, universo)
            lidas, pj = lidas + a, pj + b
            for c, lista in achadas.items():
                sancoes.setdefault(c, []).extend(lista)
            log.info("sanções lidas", cadastro=cad, linhas=a, pessoa_juridica=b, cnpjs=len(achadas))
    for lista in sancoes.values():
        lista.sort(key=lambda s: (s["inicio"] or "", s["cadastro"], s["codigo"]))
    if dst.exists() and not force and (read_json_gz(dst) or {}).get("arquivos") == arquivos and (read_json_gz(dst) or {}).get("universo_cnpjs_basicos") == len(universo):
        log.info("arquivos iguais aos já coletados; use --force para regravar", arquivos=arquivos)
        return read_json_gz(dst)
    saida = {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "CGU — Portal da Transparência (CEIS e CNEP)", "fonte_url": "https://portaldatransparencia.gov.br/sancoes",
             "arquivos": arquivos, "universo_cnpjs_basicos": len(universo), "linhas_lidas": lidas, "linhas_pessoa_juridica": pj,
             "sancoes_guardadas": sum(len(v) for v in sancoes.values()), "cnpjs": len(sancoes), "sancoes": sancoes}
    write_json_gz(dst, saida)
    log.info("cgu_ceis_cnep gravado", caminho=str(dst), cnpjs=len(sancoes), sancoes=saida["sancoes_guardadas"], linhas=lidas)
    return saida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sanções CEIS/CNEP a empresas de telecom")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="regrava mesmo que os arquivos de origem sejam os mesmos")
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
