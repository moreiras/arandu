# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Cadastro das empresas de telecom (dados abertos do CNPJ da Receita Federal).

Mesma pasta mensal do `receita_socios` (compartilhamento Nextcloud em arquivos.receitafederal.gov.br), com `Estabelecimentos*`, `Empresas*`, `Simples` e as
tabelas de apoio (`Municipios`, `Naturezas`, `Cnaes`). A coleta é autorizada pelo mantenedor, apesar do `robots.txt` do host (`Disallow: /`), com as
condições da decisão: `User-Agent` identificado, UMA requisição por vez, pausa entre downloads e só os arquivos do mês corrente.

São ~7,5 GB por mês (Estabelecimentos 5,8 GB em 10 partes, Empresas 1,4 GB, Simples 0,3 GB). Nada vai inteiro para `raw/`: cada parte é baixada para um arquivo temporário
em `data/raw/_receita_tmp/`, lida em fluxo (sem carregar o CSV na memória) e apagada. Só fica o recorte de telecom:

  * Estabelecimentos: os de CNPJs das outorgas (SCM, SMP, STFC, SeAC) e do SICI, e todo o que tem CNAE 61 principal ou secundário (`core.receita_cnpj`);
  * Empresas e Simples: os CNPJs básicos desses estabelecimentos.

Limite assumido: é UMA passada pelos Estabelecimentos. Uma filial de CNAE diferente de 61 de uma empresa que só se revela telecom por outro
estabelecimento, e que não está nas outorgas nem no SICI, não entra. Não entram e-mail, telefone, endereço de rua nem CEP; empresário individual (natureza 213-5) fica sem
razão social e sem nome fantasia.

Entrada:  normalized/{date}/summary/anatel_{scm,smp,stfc,seac}.json.gz e sici_acessos.json.gz (universo de CNPJs; sem nenhuma, só vale o CNAE 61).
Saída:    normalized/{date}/summary/receita_cnpj.json.gz

Uso:
    python -m sources.receita_cnpj.collect --date 2026-11-07 [--force]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import httpx

from core import receita_cnpj as rc
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from sources.receita_socios.collect import WEBDAV_ROOT, _discover_latest_month, _propfind_children, _webdav_auth_header
from core.site import USER_AGENT

PAUSA_S = float(os.environ.get("RECEITA_PAUSA_S", "2"))          # entre downloads: uma requisição por vez e respiro para o servidor
_OUTORGAS = ("anatel_scm.json.gz", "anatel_smp.json.gz", "anatel_stfc.json.gz", "anatel_seac.json.gz")


def _universo(base: Path, date_str: str, log) -> set[str]:
    """CNPJs básicos (8 dígitos) das outorgas e do SICI."""
    basicos: set[str] = set()
    for nome in _OUTORGAS:
        p = normalized_path(base, date_str, "summary", nome)
        if p.exists():
            basicos.update(c[:8] for c in ((read_json_gz(p) or {}).get("by_cnpj") or {}) if len(c) == 14)
        else:
            log.info("fonte de outorga ausente", fonte=nome)
    p = normalized_path(base, date_str, "summary", "sici_acessos.json.gz")
    if p.exists():
        cn = (read_json_gz(p) or {}).get("cnpjs") or {}
        basicos.update(c[:8] for c in (cn.keys() if isinstance(cn, dict) else cn) if isinstance(c, str) and len(c) == 14)
    return basicos


def _arquivos(client: httpx.Client, mes: str, log) -> dict[str, list[str]]:
    """Arquivos do mês por prefixo (a quantidade de partes varia de um mês para outro: nunca fixa)."""
    nomes = [c["name"] for c in _propfind_children(client, f"{WEBDAV_ROOT}{mes}/") if not c["is_dir"] and c["name"].lower().endswith(".zip")]
    por = {p: sorted(n for n in nomes if n.lower().startswith(p.lower())) for p in ("Estabelecimentos", "Empresas", "Simples", "Municipios", "Naturezas", "Cnaes")}
    log.info("arquivos do mês", mes=mes, **{k: len(v) for k, v in por.items()})
    return por


def _baixar(client: httpx.Client, url: str, tmpdir: Path, log) -> Path:
    tmpdir.mkdir(parents=True, exist_ok=True)
    fd, caminho = tempfile.mkstemp(suffix=".zip", dir=str(tmpdir))
    total = 0
    with os.fdopen(fd, "wb") as f, client.stream("GET", url, headers=_webdav_auth_header(), timeout=900) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes(chunk_size=1024 * 1024):
            f.write(chunk)
            total += len(chunk)
    log.info("parte baixada", url=url, mb=round(total / 1_048_576, 1))
    return Path(caminho)


def _linhas(zip_path: Path):
    """Linhas (listas de campos) de todos os CSV do ZIP, em fluxo. Latin-1, `;`, aspas."""
    with zipfile.ZipFile(zip_path) as zf:
        for membro in zf.namelist():
            with zf.open(membro) as bruto, io.TextIOWrapper(bruto, encoding="latin-1", newline="") as texto:
                yield from csv.reader(texto, delimiter=";")


def _tabela(client: httpx.Client, mes: str, nome: str, tmpdir: Path, log) -> dict[str, str]:
    """Tabela de apoio (código;descrição), pequena."""
    caminho = _baixar(client, f"{WEBDAV_ROOT}{mes}/{nome}", tmpdir, log)
    try:
        return {r[0].strip(): r[1].strip() for r in _linhas(caminho) if len(r) >= 2}
    finally:
        caminho.unlink(missing_ok=True)


def _estabelecimentos(caminho: Path, universo: set[str], achados: dict[str, list[dict]]) -> tuple[int, int]:
    """Lê uma parte e guarda o recorte de telecom. Devolve (linhas lidas, linhas guardadas).

    Pré-filtro barato antes de interpretar a linha: CNPJ básico no universo (8 dígitos entre aspas no começo) ou um `"61` / `,61` em qualquer campo (CNAE
    principal, ou secundário no começo ou no meio da lista; também pega DDD, CEP e município); o falso positivo é raro e o teste exato vem em seguida."""
    lidas = guardadas = 0
    with zipfile.ZipFile(caminho) as zf:
        for membro in zf.namelist():
            with zf.open(membro) as bruto, io.TextIOWrapper(bruto, encoding="latin-1", newline="") as texto:
                for linha in texto:
                    lidas += 1
                    basico = linha[1:9]
                    if basico not in universo and '"61' not in linha and ',61' not in linha:
                        continue
                    row = next(csv.reader([linha], delimiter=";"))
                    if len(row) < rc.E_COLUNAS:
                        continue
                    if basico not in universo and not rc.eh_telecom(row[rc.E_CNAE].strip(), rc.cnaes_secundarios(row[rc.E_CNAE_SEC])):
                        continue
                    achados.setdefault(row[rc.E_BASICO].strip(), []).append(rc.estabelecimento(row))
                    guardadas += 1
    return lidas, guardadas


def _recorte(client: httpx.Client, mes: str, nomes: list[str], basicos: set[str], tmpdir: Path, log, montar) -> dict[str, dict]:
    """Empresas ou Simples: só os CNPJs básicos dos estabelecimentos guardados."""
    out: dict[str, dict] = {}
    for i, nome in enumerate(nomes):
        if i:
            time.sleep(PAUSA_S)
        caminho = _baixar(client, f"{WEBDAV_ROOT}{mes}/{nome}", tmpdir, log)
        try:
            for r in _linhas(caminho):
                if len(r) >= 7 and r[0].strip() in basicos:
                    out[r[0].strip()] = montar(r)
        finally:
            caminho.unlink(missing_ok=True)
        log.info("parte lida", parte=nome, guardados=len(out))
    return out


def run(date_str: str, base: Path, log, force: bool = False) -> dict:
    dst = normalized_path(base, date_str, "summary", "receita_cnpj.json.gz")
    universo = _universo(base, date_str, log)
    tmpdir = base / "raw" / "_receita_tmp"
    with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        mes = _discover_latest_month(client, log)
        if dst.exists() and not force and (read_json_gz(dst) or {}).get("dump_reference") == mes:
            log.info("mês já coletado; use --force para repetir", mes=mes)
            return read_json_gz(dst)
        arqs = _arquivos(client, mes, log)
        if not arqs["Estabelecimentos"] or not arqs["Empresas"]:
            raise RuntimeError(f"Estabelecimentos ou Empresas ausentes em {WEBDAV_ROOT}{mes}/: a estrutura do compartilhamento pode ter mudado")
        municipios = _tabela(client, mes, arqs["Municipios"][0], tmpdir, log) if arqs["Municipios"] else {}
        cnaes_arq = _tabela(client, mes, arqs["Cnaes"][0], tmpdir, log) if arqs["Cnaes"] else {}
        naturezas = _tabela(client, mes, arqs["Naturezas"][0], tmpdir, log) if arqs["Naturezas"] else {}
        achados: dict[str, list[dict]] = {}
        lidas = guardadas = 0
        try:
            for nome in arqs["Estabelecimentos"]:
                time.sleep(PAUSA_S)
                caminho = _baixar(client, f"{WEBDAV_ROOT}{mes}/{nome}", tmpdir, log)
                try:
                    a, b = _estabelecimentos(caminho, universo, achados)
                finally:
                    caminho.unlink(missing_ok=True)
                lidas, guardadas = lidas + a, guardadas + b
                log.info("estabelecimentos lidos", parte=nome, linhas=a, guardadas=b, empresas=len(achados))
            basicos = set(achados)
            time.sleep(PAUSA_S)
            empresas = _recorte(client, mes, arqs["Empresas"], basicos, tmpdir, log, rc.empresa)
            time.sleep(PAUSA_S)
            simples = _recorte(client, mes, arqs["Simples"], basicos, tmpdir, log, rc.simples)
        finally:
            for f in tmpdir.glob("*.zip"):
                f.unlink(missing_ok=True)
    # empresário individual: o nome fantasia também é o da pessoa
    for basico, e in empresas.items():
        if e.get("nat") == rc.NATUREZA_EI:
            for est in achados.get(basico, []):
                est.pop("n", None)
    saida = {
        "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Receita Federal — dados abertos do CNPJ", "dump_reference": mes,
        "fonte_url": WEBDAV_ROOT,
        "universo_cnpjs_basicos": len(universo), "linhas_lidas": lidas, "estabelecimentos_guardados": guardadas, "empresas": len(achados),
        "municipios_rfb": municipios, "naturezas": naturezas,
        "cnaes": {c: cnaes_arq[c] for c in sorted({x for ests in achados.values() for e in ests for x in [e["p"], *e["x"]]}) if c in cnaes_arq},
        "empresa": empresas, "simples": simples, "estabelecimentos": achados,
    }
    write_json_gz(dst, saida)
    log.info("receita_cnpj gravado", caminho=str(dst), empresas=len(achados), estabelecimentos=guardadas, linhas=lidas)
    return saida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cadastro de telecom (CNPJ, Receita Federal)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="coleta de novo mesmo que o mês já tenha sido coletado")
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
