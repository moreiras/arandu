# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""OONI: medições do Brasil no bucket público de dados abertos `ooni-data-eu-fra`, agregadas por ASN × teste × dia **em fluxo**.

Por que o bucket e não a API: o `robots.txt` de `api.ooni.io` proíbe a agregação. O bucket S3 (Amazon Open Data) é o canal que o OONI indica a pesquisadores; o host é o da Amazon
(sem `robots.txt` aplicável) e a listagem anônima é por HTTPS. Uma requisição por vez, pausa de 1 s, `User-Agent` identificado.

Fluxo: lista `raw/AAAAMMDD/HH/BR/` das 24 horas do dia, baixa só `.jsonl.gz` dos testes escolhidos (`core.ooni`), descomprime e agrega **em memória** e **descarta o bruto**: nenhum byte
do OONI vai ao disco. Do que se lê fica `(ASN, teste, dia, contagens)`; `report_id`, `input`, IP da sonda, nome de rede e horário individual nunca são guardados.
  * Fase A (sempre): testes leves de mensageria e circumvention, todos os arquivos do dia (~45 MB/dia de `.jsonl.gz` no Brasil em 2026-11-01).
  * Fase B (`--web`, padrão ligada): `webconnectivity` por AMOSTRA (algumas horas fixas por dia, `HORAS_AMOSTRA`) e com teto de bytes por execução (`OONI_TETO_GB`, padrão 3). O volume
    completo é ~1,4 GB/dia. A amostra é rotulada como tal; nenhum domínio entra (só o veredito da sonda por ASN).
O "dia" é o da pasta do bucket (data de publicação do lote, UTC), não o da medição: o lote do dia fica completo e a contagem é reproduzível.
Incremental: a execução reaproveita os dias do normalizado anterior e baixa, no máximo, `DIAS_POR_EXECUCAO` dias novos (do mais recente para trás), mantendo `JANELA_DIAS`.

Normalizado: data/normalized/{date}/summary/ooni_bloqueios.json.gz
Licença dos dados: CC BY-NC-SA 4.0 (atribuição, uso não comercial, compartilhamento pela mesma licença): vai em `licenca`/`atribuicao` do arquivo e de tudo que o deriva.

Uso:
    python -m sources.ooni_bloqueios.collect --date 2026-11-08 [--sem-web] [--dias 7]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import zlib
from datetime import date as _date, timedelta
from pathlib import Path
from typing import Callable, Optional

import httpx

from core import ooni
from core.common import configure_logging, data_dir, normalized_path, now_iso, read_json_gz, today_str, write_json_gz
from core.site import USER_AGENT

BUCKET = "https://ooni-data-eu-fra.s3.amazonaws.com/"
HEADERS = {"User-Agent": USER_AGENT}
PAIS = "BR"
ESPERA_S = 1.0
JANELA_DIAS = 28
DIAS_POR_EXECUCAO = 7
HORAS_AMOSTRA = (2, 10, 18)              # UTC; três horas espalhadas ao longo do dia (23 h–15 h em Brasília), sem escolher medição nenhuma
TETO_GB_PADRAO = 3.0
MINIMO_HORAS_COM_ARQUIVO = 20            # dia com menos horas publicadas que isto está incompleto e não entra
_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


class Contador:
    """O que a execução custou: requisições, bytes baixados (comprimidos) e o que foi lido/descartado."""

    def __init__(self) -> None:
        self.requisicoes = 0
        self.bytes = 0
        self.bytes_web = 0                # tamanho listado dos arquivos da fase B já lidos (para o teto)
        self.arquivos = 0
        self.medicoes_lidas = 0
        self.medicoes_descartadas = 0


def _pausa(espera_s: float) -> None:
    if espera_s:
        time.sleep(espera_s)


def _com_repeticao(fn: Callable, tentativas: int = 3, espera_s: float = ESPERA_S):
    for t in range(1, tentativas + 1):
        try:
            return fn()
        except (httpx.HTTPError, zlib.error, ET.ParseError):
            if t == tentativas:
                raise
            time.sleep(espera_s * 5 * t)
    raise AssertionError("inalcançável")


def listar(client: httpx.Client, prefixo: str, cont: Contador, espera_s: float = ESPERA_S) -> list[tuple[str, int]]:
    """`[(chave, tamanho)]` dos `.jsonl.gz` sob o prefixo (os `.tar.gz` "postcans" duplicam o conteúdo e são ignorados)."""
    saida: list[tuple[str, int]] = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefixo}
        if token:
            params["continuation-token"] = token

        def _get():
            r = client.get(BUCKET, params=params)
            r.raise_for_status()
            return r.content
        corpo = _com_repeticao(_get, espera_s=espera_s)
        cont.requisicoes += 1
        raiz = ET.fromstring(corpo)
        for c in raiz.findall(_NS + "Contents"):
            k = c.find(_NS + "Key").text
            if k.endswith(".jsonl.gz"):
                saida.append((k, int(c.find(_NS + "Size").text)))
        nt = raiz.find(_NS + "NextContinuationToken")
        _pausa(espera_s)
        if raiz.findtext(_NS + "IsTruncated") == "true" and nt is not None:
            token = nt.text
        else:
            return saida


def _linhas(client: httpx.Client, chave: str, cont: Contador):
    """Gera as linhas (bytes) do `.jsonl.gz` em fluxo: nada é gravado em disco."""
    d = zlib.decompressobj(31)
    resto = b""
    with client.stream("GET", BUCKET + chave) as r:
        r.raise_for_status()
        for pedaco in r.iter_raw(1 << 20):
            cont.bytes += len(pedaco)
            resto += d.decompress(pedaco)
            *linhas, resto = resto.split(b"\n")
            for ln in linhas:
                if ln.strip():
                    yield json.loads(ln)
    resto += d.flush()
    if resto.strip():
        yield json.loads(resto)


def agregar_arquivo(client: httpx.Client, chave: str, teste: str, cont: Contador) -> ooni.Agregador:
    """Agrega um arquivo inteiro num `Agregador` próprio (só se funde ao do dia quando o arquivo termina bem: arquivo que falha no meio não deixa meia contagem)."""
    ag = ooni.Agregador()
    for m in _linhas(client, chave, cont):
        ag.add(teste, m)
    cont.requisicoes += 1
    cont.arquivos += 1
    cont.medicoes_lidas += ag.lidas
    cont.medicoes_descartadas += ag.descartadas
    return ag


def _fundir(destino: dict, ag: ooni.Agregador) -> None:
    ooni.mesclar(destino, ag.dados)


def processar_dia(client: httpx.Client, dia: str, web: bool, cont: Contador, teto_bytes: int, log, espera_s: float = ESPERA_S) -> Optional[dict]:
    """Agrega um dia (AAAA-MM-DD). None se o dia está incompleto no bucket. `web=False` pula a fase B; o teto vale para os bytes da fase B."""
    d8 = dia.replace("-", "")
    testes: dict = {}
    web_dados: dict = {}
    horas_com_arquivo = 0
    plano_web: list[tuple[str, int]] = []
    for h in range(24):
        chaves = listar(client, f"raw/{d8}/{h:02d}/{PAIS}/", cont, espera_s)
        if chaves:
            horas_com_arquivo += 1
        for k, tam in chaves:
            t = k.split("/")[4]
            if t in ooni.TESTES_LEVES:
                _pausa(espera_s)
                _com_repeticao(lambda: _fundir(testes, agregar_arquivo(client, k, t, cont)), espera_s=espera_s)
            elif t == ooni.TESTE_WEB and h in HORAS_AMOSTRA:
                plano_web.append((k, tam))
    if horas_com_arquivo < MINIMO_HORAS_COM_ARQUIVO:
        log.warning("ooni dia incompleto no bucket", dia=dia, horas=horas_com_arquivo)
        return None
    amostra = None
    if web:
        usados = 0
        feitos = 0
        for k, tam in plano_web:
            if cont.bytes_web + tam > teto_bytes:
                continue
            _pausa(espera_s)
            ag = _com_repeticao(lambda: agregar_arquivo(client, k, ooni.TESTE_WEB, cont), espera_s=espera_s)
            _fundir(web_dados, ag)
            cont.bytes_web += tam
            usados += tam
            feitos += 1
        amostra = {"horas_utc": list(HORAS_AMOSTRA), "arquivos": feitos, "arquivos_da_amostra": len(plano_web), "bytes": usados, "completa": feitos == len(plano_web)}
    return {"testes": testes, "web": web_dados.get(ooni.TESTE_WEB) if web else None, "web_amostra": amostra}


def _anterior(base: Path, date_str: str) -> dict:
    """Normalizado mais recente (de outra data) com o arquivo, para reaproveitar os dias já agregados."""
    achados = sorted(p for p in (base / "normalized").glob("*/summary/ooni_bloqueios.json.gz") if p.parent.parent.name != date_str)
    return read_json_gz(achados[-1]) if achados else {}


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, web: bool = True, dias_novos: int = DIAS_POR_EXECUCAO,
        espera_s: float = ESPERA_S, teto_gb: Optional[float] = None) -> dict:
    t0 = time.time()
    teto = int(float(teto_gb if teto_gb is not None else os.environ.get("OONI_TETO_GB", TETO_GB_PADRAO)) * 1e9)
    ontem = _date.fromisoformat(date_str) - timedelta(days=1)
    janela = [(ontem - timedelta(days=i)).isoformat() for i in range(JANELA_DIAS)]
    antes = (_anterior(base, date_str).get("dias") or {})
    dias = {d: v for d, v in antes.items() if d in janela}
    faltam = [d for d in janela if d not in dias][:dias_novos]
    cont = Contador()
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=300), follow_redirects=True, headers=HEADERS)
    try:
        for d in faltam:                                                  # do mais recente para trás: o teto da fase B poupa os dias mais antigos
            r = processar_dia(client, d, web, cont, teto, log, espera_s)
            if r is not None:
                dias[d] = r
    finally:
        if proprio:
            client.close()
    if not dias:
        raise RuntimeError(f"ooni_bloqueios: nenhum dia completo no bucket (tentados: {faltam})")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    medicao = {"dias_baixados": [d for d in faltam if d in dias], "requisicoes": cont.requisicoes, "bytes_baixados": cont.bytes, "arquivos": cont.arquivos,
               "medicoes_lidas": cont.medicoes_lidas, "medicoes_descartadas_sem_campo_valido": cont.medicoes_descartadas, "segundos": round(time.time() - t0, 1),
               "teto_bytes_web": teto}
    write_json_gz(destino / "ooni_bloqueios.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": BUCKET, "licenca": ooni.LICENCA, "licenca_url": ooni.LICENCA_URL, "atribuicao": ooni.ATRIBUICAO,
        "janela_dias": JANELA_DIAS, "horas_amostra_web": list(HORAS_AMOSTRA), "ultima_execucao": medicao,
        "dias": {d: dias[d] for d in sorted(dias)}})
    log.info("ooni_bloqueios written", dias=len(dias), **{k: v for k, v in medicao.items() if not isinstance(v, list)})
    return medicao


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OONI: medições do Brasil agregadas por ASN (bucket aberto ooni-data-eu-fra)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre incremental")
    p.add_argument("--sem-web", action="store_true", help="só a fase A (testes leves)")
    p.add_argument("--dias", type=int, default=DIAS_POR_EXECUCAO, help="dias novos a baixar nesta execução")
    p.add_argument("--teto-gb", type=float, default=None, help="teto de GB da fase B (padrão: OONI_TETO_GB ou 3)")
    a = p.parse_args(argv)
    log = configure_logging()
    if os.environ.get("OONI_ATIVO") == "0":
        # Interruptor de desligamento: o OONI é tratado como a TeleGeography (licença própria
        # declarada no catálogo, CC BY-NC-SA 4.0, atribuição em todas as saídas). A coleta vem ligada; OONI_ATIVO=0 a desliga sem rede.
        log.warning("ooni_bloqueios desligado por OONI_ATIVO=0; nenhuma requisição feita")
        return 0
    try:
        print(run(a.date, data_dir(), log, web=not a.sem_web, dias_novos=a.dias, teto_gb=a.teto_gb))
    except Exception:
        log.exception("falha na coleta de ooni_bloqueios")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
