# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consumidor.gov.br: reclamações finalizadas de operadoras de telecomunicações.

Fonte:       https://consumidor.gov.br/pages/publicacao/externo/publicacoes.json?indicadorTipoPublicacao=3 (lista) e
             https://consumidor.gov.br/pages/publicacao/externo/{codigo}/download (um `finalizadas_AAAA-MM.zip` por mês, 4 a 16 MB; o CSV tem ~120 MB e todos os segmentos)
Bruto:       data/raw/{date}/summary/consumidor_gov/finalizadas_AAAA-MM.zip, só dos meses baixados nesta execução (o resto vem do normalizado anterior)
Normalizado: data/normalized/{date}/summary/consumidor_gov.json.gz (um agregado por mês, só do segmento de operadoras; ver `core/consumidor.py`)

Incremental: o mês fechado é imutável, então só se baixa o que não está no normalizado anterior com o mesmo `codigo` de publicação (o arquivo republicado ganha código novo). A primeira execução baixa
`MESES` arquivos; as seguintes, o mês novo. O `robots.txt` é lido antes e a coleta aborta se ele proibir `/pages/publicacao/`. Uma requisição por vez, pausa de 1 s, User-Agent identificado.
Os arquivos têm sexo e faixa etária de quem reclamou: a linha é descartada na leitura (só sobram contagens por empresa × UF × cidade).

Uso:
    python -m sources.consumidor_gov.collect --date 2026-11-06
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional
from urllib.robotparser import RobotFileParser

import httpx

from core import consumidor
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, read_json_gz, today_str, write_json_gz
from core.site import USER_AGENT

BASE = "https://consumidor.gov.br"
URL_LISTA = f"{BASE}/pages/publicacao/externo/publicacoes.json"
URL_DOWNLOAD = f"{BASE}/pages/publicacao/externo/{{codigo}}/download"
HEADERS = {"User-Agent": USER_AGENT}
TIPO_PUBLICACAO = 3                 # "Dados" (arquivos mensais); 1 = boletins em PDF
MESES = 24                          # janela da série; o 12m mais recente alimenta os indicadores, o resto dá a série
PAUSA_S = 1.0
MINIMO_TELECOM_POR_MES = 1000       # hoje 15–30 mil por mês; bem menos é arquivo truncado ou segmento renomeado
NOME = re.compile(r"^finalizadas_(\d{4})-(\d{2})\.zip$")


def verificar_robots(client: httpx.Client) -> None:
    r = client.get(f"{BASE}/robots.txt")
    r.raise_for_status()
    rp = RobotFileParser()
    rp.parse(r.text.splitlines())
    for url in (URL_LISTA, URL_DOWNLOAD.format(codigo="0")):
        if not rp.can_fetch(HEADERS["User-Agent"], url):
            raise RuntimeError(f"consumidor_gov: o robots.txt proíbe {url}; coleta abortada")


def listar(client: httpx.Client) -> dict[str, dict]:
    """`{AAAA-MM: {codigo, tamanho, nome}}` dos `MESES` meses mais recentes publicados (o código mais novo vale se o mês foi republicado)."""
    ultimo: Exception | None = None
    for tentativa in range(3):
        try:
            r = client.get(URL_LISTA, params={"indicadorTipoPublicacao": TIPO_PUBLICACAO})
            r.raise_for_status()
            itens = json.loads(r.content.decode("utf-8", errors="replace"))      # o servidor mistura codificações nos textos; só nome, código e tamanho importam
            break
        except (httpx.HTTPError, ValueError) as e:      # o servidor do Consumidor.gov.br responde 504 às vezes
            ultimo = e
            time.sleep(PAUSA_S * 5 * (tentativa + 1))
    else:
        raise RuntimeError(f"consumidor_gov: lista de publicações indisponível ({ultimo})")
    meses: dict[str, dict] = {}
    for it in itens:
        m = NOME.match(str(it.get("nomeArquivo", "")))
        if not m or it.get("indicadorExclusaoLogica"):
            continue
        mes = f"{m.group(1)}-{m.group(2)}"
        if mes not in meses or str(it["codigo"]) > meses[mes]["codigo"]:
            meses[mes] = {"codigo": str(it["codigo"]), "tamanho": it.get("tamanhoArquivo"), "nome": it["nomeArquivo"]}
    if not meses:
        raise RuntimeError("consumidor_gov: nenhum finalizadas_AAAA-MM.zip na lista de publicações; o leiaute mudou?")
    return {k: meses[k] for k in sorted(meses)[-MESES:]}


def baixar(client: httpx.Client, codigo: str, destino: Path) -> None:
    with client.stream("GET", URL_DOWNLOAD.format(codigo=codigo)) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for pedaco in r.iter_bytes(1 << 20):
                f.write(pedaco)


def processar_zip(zip_path: Path) -> tuple[dict | None, str | None]:
    """`(agregado, None)` ou `(None, motivo)` quando o zip não pode ser lido com a biblioteca padrão: em 2026-05 o zip trouxe um `.7z` e em 2026-06 usou compressão Deflate64. Ler esses formatos
    exigiria dependência nova; o mês fica registrado como indisponível e os totais da janela dizem de quantos meses vêm."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if len(csvs) != 1:
                return None, f"o zip de {zip_path.name} não traz exatamente um CSV (traz {z.namelist()})"
            with z.open(csvs[0]) as f:
                return consumidor.agregar_csv(f), None
    except (NotImplementedError, zipfile.BadZipFile) as e:
        return None, f"o zip de {zip_path.name} não é legível pela biblioteca padrão do Python ({e})"


def anterior(base: Path, date_str: str) -> dict:
    """O normalizado mais recente de uma data anterior (os meses já agregados), ou `{}`."""
    raiz = base / "normalized"
    if not raiz.is_dir():
        return {}
    for d in sorted((p.name for p in raiz.iterdir() if p.is_dir() and p.name < date_str), reverse=True):
        arq = raiz / d / "summary" / "consumidor_gov.json.gz"
        if arq.exists():
            return read_json_gz(arq)
    return {}


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, pausa: float = PAUSA_S) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=300), follow_redirects=True, headers=HEADERS)
    try:
        verificar_robots(client)
        lista = listar(client)
        antes = {**anterior(base, date_str).get("meses", {}), **(read_json_gz(p).get("meses", {}) if (p := normalized_path(base, date_str, "summary") / "consumidor_gov.json.gz").exists() else {})}
        bruto = raw_path(base, date_str, "summary") / "consumidor_gov"
        meses: dict[str, dict] = {}
        baixados = reaproveitados = 0
        for mes, info in lista.items():
            ant = antes.get(mes)
            if ant and ant.get("codigo") == info["codigo"]:
                meses[mes] = ant
                continue
            bruto.mkdir(parents=True, exist_ok=True)
            destino = bruto / f"finalizadas_{mes}.zip"
            tmp = destino.with_suffix(".zip.tmp")
            if destino.exists() and destino.stat().st_size == info["tamanho"]:       # reexecução da mesma data depois de uma falha: o bruto já está aqui
                reaproveitados += 1
            else:
                if baixados:
                    time.sleep(pausa)
                baixar(client, info["codigo"], tmp)
                tmp.replace(destino)
                baixados += 1
            agg, motivo = processar_zip(destino)
            if agg is None:
                log.warning("consumidor_gov mes indisponivel", mes=mes, motivo=motivo)
                meses[mes] = {"codigo": info["codigo"], "tamanho": info["tamanho"], "indisponivel": motivo}
                continue
            if agg["resumo"]["telecom"] < MINIMO_TELECOM_POR_MES:
                raise RuntimeError(f"consumidor_gov: {mes} só tem {agg['resumo']['telecom']} reclamações de telecom; arquivo truncado ou segmento renomeado ({agg['resumo']['segmentos']})")
            meses[mes] = {"codigo": info["codigo"], "tamanho": info["tamanho"], **agg}
            log.info("consumidor_gov mes", mes=mes, **{k: v for k, v in agg["resumo"].items() if not isinstance(v, list)})
    finally:
        if proprio:
            client.close()
    destino_n = normalized_path(base, date_str, "summary")
    destino_n.mkdir(parents=True, exist_ok=True)
    resumo = {"meses": len(meses), "mes_inicial": min(meses), "mes_final": max(meses), "baixados": baixados, "reclamacoes_telecom": sum(m["resumo"]["telecom"] for m in meses.values() if "resumo" in m),
              "meses_indisponiveis": sorted(k for k, m in meses.items() if "resumo" not in m)}
    write_json_gz(destino_n / "consumidor_gov.json.gz", {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Consumidor.gov.br (Senacon, Ministério da Justiça e Segurança Pública), dados abertos",
                                                         "url": URL_LISTA, "meses": meses, "resumo": resumo})
    log.info("consumidor_gov written", **resumo)
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Reclamações finalizadas do Consumidor.gov.br (operadoras de telecomunicações)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta já é incremental e idempotente")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de consumidor_gov")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
