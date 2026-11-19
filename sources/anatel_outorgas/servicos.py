# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Outorgas da Anatel por serviço: um CSV, um parser, uma configuração por serviço.

SCM (045), SMP (010), STFC (171) e SeAC (750) vêm do mesmo arquivo (`prestadoras_servicos_telecomunicacoes.zip`, baixado uma vez
por data: `download.py`). Um parser só para os quatro; cada
`Servico` diz só o que muda: o código do serviço, como reconhecer o nome por extenso e o nome da lista no JSON.
Um quinto serviço = um arquivo de configuração + uma entrada no catálogo (ver `anatel_outorgas.yaml` e `scripts/novo_servico_outorga.py`).

Saída (inalterada): normalized/{date}/summary/anatel_<sigla>.json.gz com
  snapshot_date, generated_at, total, unique_cnpjs, <chave>: [registros], by_cnpj: {cnpj: [registros]}
"""
from __future__ import annotations

import csv
import io
import re
import importlib
from pathlib import Path

from core.common import normalized_path, now_iso, write_json_gz
from core.outorgas import SERVICOS, Servico  # noqa: F401 — o registro dos serviços
from sources.anatel_outorgas.download import ANATEL_URL, obter_csv


# Mapeamento tolerante de nomes de coluna → campo normalizado.
# Inclui tanto as formas abreviadas históricas quanto os nomes longos do CSV atual da Anatel.
# Chaves são a saída de _norm_key(col): sem acentos, sem não-alfanumérico, minúsculo.
_COL_MAP: dict[str, str] = {
    # CNPJ — formas históricas e forma atual "CNPJ ou CPF"
    "numcpfcnpj": "cnpj", "numcnpj": "cnpj", "cpfcnpj": "cnpj", "cnpj": "cnpj",
    "cnpjoucpf": "cnpj",
    # Razão social
    "nomrazaosocial": "razao_social", "razaosocial": "razao_social",
    "razao_social": "razao_social",
    "nomeentidadeprestadoradeservio": "razao_social",   # "Nome Entidade Prestadora de Serviço"
    "nomeentidadeprestadoradeservico": "razao_social",
    # Nome fantasia
    "nomfantasia": "nome_fantasia", "nomefantasia": "nome_fantasia",
    "nome_fantasia": "nome_fantasia",
    # Data de outorga
    "datoutorga": "data_outorga", "datainiciooutorga": "data_outorga",
    "data_outorga": "data_outorga", "data_inicio_outorga": "data_outorga",
    "datiniciooutorga": "data_outorga",
    "datainclusodaoutorga": "data_outorga",             # "Data Inclusão da Outorga"
    "datainclusaodaoutorga": "data_outorga",
    # Serviço (coluna usada para filtragem SCM)
    "numservico": "num_servico", "nomservico": "nom_servico",
    "nrservico": "num_servico", "nomeservico": "nom_servico",
    "numcod": "num_servico", "codservico": "num_servico",
    "cdigoenomedoserviodanotificao": "num_servico",     # "Código e Nome do Serviço da Notificação"
    "codigoenomeservicodanotificacao": "num_servico",
    # CEP
    "numcep": "cep", "cep": "cep",
    "cepdoendereosede": "cep",                          # "CEP do Endereço Sede"
    "cepdoenderecosede": "cep",
    # Logradouro
    "nomlogradouro": "logradouro", "logradouro": "logradouro",
    "logradourodoendereosede": "logradouro",            # "Logradouro do Endereço Sede"
    "logradourodoenderecosede": "logradouro",
    # Número
    "numlogradouro": "numero", "numero": "numero", "nrlogradouro": "numero",
    "nmerodoendereosede": "numero",                     # "Número do Endereço Sede"
    "numerodoenderecosede": "numero",
    # Complemento
    "nomcomplemento": "complemento", "complemento": "complemento",
    "complementodoendereosede": "complemento",          # "Complemento do Endereço Sede"
    "complementodoenderecosede": "complemento",
    # Bairro
    "nombairro": "bairro", "bairro": "bairro",
    "bairrodoendereosede": "bairro",                    # "Bairro do Endereço Sede"
    "bairrodoenderecosede": "bairro",
    # Município
    "nommunicipio": "municipio", "municipio": "municipio",
    "nomedomuncipiodoendereosede": "municipio",         # "Nome do Munícipio do Endereço Sede"
    "nomedomunicicipiodoenderecosede": "municipio",
    "nomedomunicpiodoendereosede": "municipio",
    # UF
    "siguf": "uf", "uf": "uf",
    "ufdoendereosede": "uf",                            # "UF do Endereço Sede"
    "ufdoenderecosede": "uf",
    # Código IBGE
    "codibge": "codigo_ibge", "codigomunicipio": "codigo_ibge",
    "cod_municipio_ibge": "codigo_ibge", "codigo_ibge": "codigo_ibge",
    "codmunicipioibge": "codigo_ibge",
    "cdigoibgedomuncipiodoendereosede": "codigo_ibge",  # "Código IBGE do Munícipio do Endereço Sede"
    "codigoibgedomunicipioenderecosede": "codigo_ibge",
    # Contato
    "numtelefone": "telefone", "telefone": "telefone", "nr_telefone": "telefone",
    "nrtelefone": "telefone",
    "telefoneprincipal": "telefone",                    # "Telefone Principal"
    "endemail": "email", "email": "email",
    "endereoeletrnico": "email",                        # "Endereço Eletrônico"
    "enderecoeletronico": "email",
    # Situação
    "sigsituacaooutorga": "situacao", "situacao": "situacao",
    "situacaooutorga": "situacao", "sigSituacao": "situacao",
}


def _norm_key(col: str) -> str:
    """Remove não-alfanuméricos e converte para lowercase."""
    return re.sub(r"[^a-z0-9]", "", col.lower())


def _clean_cnpj(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    return digits if len(digits) == 14 else ""


def _clean_cep(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    return digits if len(digits) == 8 else ""


def _build_col_index(header: list[str]) -> dict[int, str]:
    """Mapeia índice → campo normalizado. Não sobrescreve mapeamento já encontrado."""
    index: dict[int, str] = {}
    seen: set[str] = set()
    for i, col in enumerate(header):
        key = _norm_key(col)
        if key in _COL_MAP:
            target = _COL_MAP[key]
            if target not in seen:
                index[i] = target
                seen.add(target)
    return index


def _detect_service_col(header: list[str]) -> int | None:
    """Encontra índice da coluna de código/nome de serviço.

    Prefere colunas com 'cdigo' + 'servio' (ex.: 'Código e Nome do Serviço da Notificação')
    porque contêm o número do serviço (010, 045, 171, 750, ...) que usamos para filtrar o serviço.
    Fallback: qualquer coluna cujo nome normalizado contenha 'servio' ou 'servico'.
    """
    for i, col in enumerate(header):
        k = _norm_key(col)
        # "Código e Nome do Serviço..." → normalizado contém "cdigo" e "servio"
        if ("cdigo" in k or "codigo" in k) and ("servio" in k or "servico" in k):
            return i
    # Fallback: coluna com "servico" / "servio" / "service" no nome
    for i, col in enumerate(header):
        k = _norm_key(col)
        if "servio" in k or "servico" in k or "service" in k:
            return i
    return None


def _extract_row(row: list[str], col_index: dict[int, str]) -> dict:
    out: dict = {}
    for i, field in col_index.items():
        out[field] = row[i].strip() if i < len(row) else ""
    if "cnpj" in out:
        out["cnpj"] = _clean_cnpj(out["cnpj"])
    if "cep" in out:
        out["cep"] = _clean_cep(out["cep"])
    return out


def parse_csv(content: bytes, servico: Servico) -> list[dict]:
    # Tenta UTF-8 primeiro, depois latin-1
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content.decode("latin-1", errors="replace")

    # Detecta delimitador (CSV pode usar ";" ou ",")
    sample = text[:4096]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return []

    header = rows[0]
    col_index = _build_col_index(header)
    svc_col = _detect_service_col(header)

    registros: list[dict] = []
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue
        if svc_col is not None:
            valor = row[svc_col].strip() if svc_col < len(row) else ""
            if not servico.pertence(valor):
                continue
        rec = _extract_row(row, col_index)
        if rec.get("cnpj"):
            registros.append(rec)
    return registros


def rodar(servico: Servico, date_str: str, base: Path, log) -> dict:
    """Obtém o CSV da data (download único), filtra o serviço e grava o normalizado."""
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    csv_content = obter_csv(date_str, base, log, ANATEL_URL)

    records = parse_csv(csv_content, servico)
    log.info(f"{servico.sigla} records parsed", total=len(records))
    if servico.depois_ref:
        modulo, _, funcao = servico.depois_ref.partition(":")
        records = getattr(importlib.import_module(modulo), funcao)(records, log)

    # Indexa por CNPJ (pode haver múltiplas outorgas por CNPJ)
    by_cnpj: dict[str, list[dict]] = {}
    for rec in records:
        by_cnpj.setdefault(rec["cnpj"], []).append(rec)

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "total": len(records),
        "unique_cnpjs": len(by_cnpj),
        servico.chave: records,
        "by_cnpj": by_cnpj,
    }
    norm_file = norm_dir / f"anatel_{servico.sigla}.json.gz"
    write_json_gz(norm_file, output)
    log.info(f"anatel_{servico.sigla} saved", path=str(norm_file), total=len(records), unique_cnpjs=len(by_cnpj))
    return output
