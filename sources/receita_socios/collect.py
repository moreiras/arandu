# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`receita_socios` — Sócios de empresas (dados abertos de CNPJ da Receita Federal), cruzados
com os CNPJs já cadastrados na base (outorgas SCM/SMP/STFC/SeAC da Anatel).

Fonte: compartilhamento público Nextcloud da Receita Federal/SERPRO, cujo link
fica em `collection.receita_federal.compartilhamento_url` de config/settings.yaml
(chegado a partir do link oficial em
https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/cadastros/cnpj).
O domínio antigo dadosabertos.rfb.gov.br/CNPJ/ ficou fora do ar (confirmado em
2026-09 a partir de três redes distintas) — se este link também parar de
funcionar, re-verificar a página oficial acima e trocar o link na configuração.

Estrutura: uma pasta por mês de referência (ex.: "2026-09/"), acessada via
WebDAV público do Nextcloud (autenticação HTTP Basic com o token do
compartilhamento como usuário e senha vazia). O mês mais recente é descoberto
dinamicamente (PROPFIND na raiz, maior nome "AAAA-MM"); dentro dele, os
arquivos de sócios (ex.: Socios0.zip..Socios9.zip — a quantidade de partes
varia por mês) também são listados dinamicamente, nunca supostos fixos.

Layout do CSV de sócios (";"-delimitado, latin-1, SEM cabeçalho — confirmado
em https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf):
  0  cnpj_basico                    8 primeiros dígitos do CNPJ
  1  identificador_socio            1=Pessoa Jurídica, 2=Pessoa Física, 3=Estrangeiro
  2  nome_socio                     nome (PF) ou razão social (PJ)
  3  cnpj_cpf_socio                 CPF (3 primeiros + 2 DV ocultos pela RFB) ou CNPJ completo
  4  qualificacao_socio             código
  5  data_entrada_sociedade
  6  pais                           código do país (só sócio estrangeiro)
  7  representante_legal            CPF do representante legal
  8  nome_representante
  9  qualificacao_representante
  10 faixa_etaria                   código (1=0-12 anos ... 9=80+, 0=não se aplica)

Diferente dos demais coletores, este módulo NÃO baixa nem guarda o dump
inteiro em raw/: são vários GB de âmbito nacional, e o objetivo aqui é só
cruzar os sócios das empresas já presentes na base (SCM/SMP/STFC/SeAC deste
mesmo snapshot) — o resto é descartado em streaming, arquivo .zip por vez,
sem carregar o CSV inteiro em memória.

Entrada: normalized/{date}/summary/anatel_{scm,smp,stfc,seac}.json.gz
         (`anatel_scm`, `anatel_smp`, `anatel_stfc`, `anatel_seac`) — usa a união das chaves `by_cnpj` como
         conjunto-alvo de CNPJs. Se nenhuma dessas fontes estiver disponível
         para a data, a execução falha (não há o que cruzar).
Saída:   normalized/{date}/summary/receita_socios.json.gz

Uso:
    python -m sources.receita_socios.collect --date 2026-09-27
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from core.common import (
    configure_logging,
    data_dir,
    load_settings,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT



def _compartilhamento() -> tuple[str, str]:
    """Base do Nextcloud e token do compartilhamento, a partir do link público configurado.

    Guardamos o link como a Receita o publica (`https://host/index.php/s/<token>`), não o token solto: o link muda de tempos em
    tempos e trocá-lo não pode exigir mexer no código."""
    url = (load_settings().get("collection", {}).get("receita_federal", {}) or {}).get("compartilhamento_url", "")
    partes = urlsplit(url)
    segmentos = [s for s in partes.path.split("/") if s]
    if partes.scheme != "https" or not partes.netloc or len(segmentos) < 2 or segmentos[-2] != "s":
        raise RuntimeError("collection.receita_federal.compartilhamento_url ausente ou fora do formato https://host/…/s/<token> "
                           "em config/settings.yaml")
    return f"{partes.scheme}://{partes.netloc}", segmentos[-1]


NEXTCLOUD_BASE, SHARE_TOKEN = _compartilhamento()
WEBDAV_ROOT = f"{NEXTCLOUD_BASE}/public.php/webdav/"

_DAV_NS = {"d": "DAV:"}
_PROPFIND_BODY = (
    '<?xml version="1.0"?>'
    '<d:propfind xmlns:d="DAV:"><d:prop><d:displayname/><d:resourcetype/></d:prop></d:propfind>'
)

# Fontes já normalizadas cujo `by_cnpj` define o universo de interesse.
_BASE_SOURCES = ("anatel_scm.json.gz", "anatel_smp.json.gz",
                  "anatel_stfc.json.gz", "anatel_seac.json.gz")


def _webdav_auth_header() -> dict[str, str]:
    token_b64 = base64.b64encode(f"{SHARE_TOKEN}:".encode()).decode()
    return {"Authorization": f"Basic {token_b64}"}


def _load_target_cnpjs(base: Path, date_str: str, log) -> set[str]:
    """União dos CNPJs (14 dígitos) presentes nas outorgas já normalizadas."""
    cnpjs: set[str] = set()
    for name in _BASE_SOURCES:
        path = normalized_path(base, date_str, "summary", name)
        if not path.exists():
            log.info("fonte base ausente, ignorando", source=name)
            continue
        data = read_json_gz(path)
        by_cnpj = (data or {}).get("by_cnpj", {})
        cnpjs.update(by_cnpj.keys())
    return cnpjs


def _propfind_children(client: httpx.Client, url: str) -> list[dict]:
    """Lista o conteúdo (depth=1) de uma pasta WebDAV do Nextcloud.

    Retorna [{"name", "is_dir"}, ...], sem incluir a própria pasta consultada.
    """
    resp = client.request(
        "PROPFIND", url,
        headers={**_webdav_auth_header(), "Depth": "1", "Content-Type": "application/xml"},
        content=_PROPFIND_BODY, timeout=30,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    children: list[dict] = []
    for i, response in enumerate(root.findall("d:response", _DAV_NS)):
        if i == 0:
            continue  # primeira entrada é a própria pasta consultada
        name = ""
        is_dir = False
        for propstat in response.findall("d:propstat", _DAV_NS):
            status = propstat.findtext("d:status", default="", namespaces=_DAV_NS)
            if "200" not in status:
                continue
            prop = propstat.find("d:prop", _DAV_NS)
            if prop is None:
                continue
            name = prop.findtext("d:displayname", default="", namespaces=_DAV_NS) or name
            if prop.find("d:resourcetype/d:collection", _DAV_NS) is not None:
                is_dir = True
        children.append({"name": name, "is_dir": is_dir})
    return children


def _discover_latest_month(client: httpx.Client, log) -> str:
    """Retorna a pasta de mês (AAAA-MM) mais recente disponível na raiz do dump."""
    children = _propfind_children(client, WEBDAV_ROOT)
    months = sorted(c["name"] for c in children
                     if c["is_dir"] and re.fullmatch(r"\d{4}-\d{2}", c["name"]))
    if not months:
        raise RuntimeError(f"Nenhuma pasta de mês (AAAA-MM) encontrada em {WEBDAV_ROOT}")
    latest = months[-1]
    log.info("mês mais recente do dump identificado", mes=latest, total_meses=len(months))
    return latest


def _list_socios_files(client: httpx.Client, month: str, log) -> list[str]:
    """Lista os arquivos de sócios (.zip) dentro da pasta do mês."""
    month_url = WEBDAV_ROOT + month + "/"
    children = _propfind_children(client, month_url)
    files = sorted(c["name"] for c in children
                    if not c["is_dir"] and "ocios" in c["name"].lower()
                    and c["name"].lower().endswith(".zip"))
    log.info("arquivos de sócios listados", mes=month, total=len(files))
    return files


def _download_to_tempfile(client: httpx.Client, url: str, log) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp_path = Path(tmp.name)
    with client.stream("GET", url, headers=_webdav_auth_header(), timeout=600) as resp:
        resp.raise_for_status()
        total = 0
        with tmp as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                total += len(chunk)
    log.info("parte baixada", url=url, size_mb=round(total / 1_048_576, 1))
    return tmp_path


def _process_part(zip_path: Path, target_basicos: set[str],
                   by_cnpj_basico: dict[str, list[dict]], log) -> int:
    """Extrai em streaming as linhas cujo cnpj_basico está no conjunto-alvo.

    Retorna o número de linhas casadas nesta parte.
    """
    matched = 0
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if not member.lower().endswith((".csv", ".txt", "")):
                continue
            with zf.open(member) as raw, \
                 io.TextIOWrapper(raw, encoding="latin-1", newline="") as text:
                reader = csv.reader(text, delimiter=";")
                for row in reader:
                    if len(row) < 11:
                        continue
                    cnpj_basico = row[0].strip()
                    if cnpj_basico not in target_basicos:
                        continue
                    by_cnpj_basico.setdefault(cnpj_basico, []).append({
                        "identificador_socio": row[1].strip(),
                        "nome_socio": row[2].strip(),
                        "cnpj_cpf_socio": row[3].strip(),
                        "qualificacao_socio": row[4].strip(),
                        "data_entrada_sociedade": row[5].strip(),
                        "representante_legal": row[7].strip(),
                        "nome_representante": row[8].strip(),
                        "faixa_etaria": row[10].strip(),
                    })
                    matched += 1
    return matched


def run(date_str: str, base: Path, log) -> dict:
    target_cnpjs = _load_target_cnpjs(base, date_str, log)
    if not target_cnpjs:
        raise RuntimeError(
            "Nenhum CNPJ base encontrado (SCM/SMP/STFC/SeAC). "
            "Rode anatel_scm, anatel_smp, anatel_stfc e anatel_seac para esta data antes de receita_socios."
        )
    target_basicos = {cnpj[:8] for cnpj in target_cnpjs if len(cnpj) == 14}
    log.info("CNPJs-alvo carregados", total_cnpjs=len(target_cnpjs),
             total_cnpj_basicos=len(target_basicos))

    by_cnpj_basico: dict[str, list[dict]] = {}

    with httpx.Client(follow_redirects=True,
                       headers={"User-Agent": USER_AGENT}) as client:
        month = _discover_latest_month(client, log)
        file_names = _list_socios_files(client, month, log)
        if not file_names:
            raise RuntimeError(
                f"Nenhum arquivo de sócios encontrado em {WEBDAV_ROOT}{month}/. "
                "A estrutura do compartilhamento pode ter mudado — verifique manualmente."
            )

        for name in file_names:
            url = WEBDAV_ROOT + month + "/" + name
            log.info("processando parte", part=name)
            tmp_path = _download_to_tempfile(client, url, log)
            try:
                matched = _process_part(tmp_path, target_basicos, by_cnpj_basico, log)
                log.info("parte processada", part=name, linhas_casadas=matched)
            finally:
                tmp_path.unlink(missing_ok=True)

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source_index": WEBDAV_ROOT,
        "dump_reference": month,
        "parts_processed": len(file_names),
        "target_cnpj_basicos": len(target_basicos),
        "matched_cnpj_basicos": len(by_cnpj_basico),
        "by_cnpj_basico": by_cnpj_basico,
    }

    dst = normalized_path(base, date_str, "summary", "receita_socios.json.gz")
    write_json_gz(dst, output)
    log.info("receita_socios saved", path=str(dst),
             matched_cnpj_basicos=len(by_cnpj_basico))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`receita_socios` — sócios (Receita Federal) das empresas já na base")
    parser.add_argument("--date", default=today_str())
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
