# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Utilitários compartilhados por todos os módulos do pipeline.

Responsabilidades:
  - Resolução do diretório raiz de dados (DATA_DIR env ou settings.yaml)
  - Carregamento de configurações YAML (settings.yaml, ixps.yaml, peeringdb_ixps.yaml)
  - Configuração de logging estruturado (structlog) em formato JSON ou texto
  - Helpers de caminho: raw_path, normalized_path, published_path
  - Leitura e escrita de arquivos JSON gzip

Convenção de caminhos:
  raw/        {date}/{ixp ou 'summary'}/  — saídas brutas imutáveis das coletas
  normalized/ {date}/{ixp ou 'summary'}/  — JSON estruturado gerado pelo parser
  published/  {date}/                     — artefatos prontos para a API e frontend
"""

import gzip
import json
import logging
import functools
import os
import re
import signal
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import structlog
import yaml


def data_dir() -> Path:
    """Retorna o diretório raiz dos dados.

    Resolução em ordem de prioridade:
    1. Variável de ambiente DATA_DIR
    2. Chave pipeline.data_dir em config/settings.yaml
    3. ./data (padrão)
    """
    env = os.environ.get("DATA_DIR")
    if env:
        return Path(env)
    settings = load_settings()
    return Path(settings.get("pipeline", {}).get("data_dir", "./data"))


@functools.lru_cache(maxsize=1)
def app_version() -> str:
    """Versão do sistema: arquivo `VERSION` na raiz do repositório (fonte única).

    Usada por `/health`, MCP (`arandurape://overview`), rodapé do front e pela
    `pipeline_version` do manifesto. Sem o arquivo, cai em `ARANDU_VERSION` e, por fim,
    em "desconhecida" (nunca levanta).
    """
    try:
        text = (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
        if text:
            return text
    except OSError:
        pass
    return os.environ.get("ARANDU_VERSION", "").strip() or "desconhecida"


def load_settings() -> dict:
    """Carrega config/settings.yaml relativo à raiz do projeto.

    Retorna dict vazio se o arquivo não existir — módulos usam valores padrão.
    """
    root = Path(__file__).parent.parent
    path = root / "config" / "settings.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_ixps() -> list[dict]:
    """Carrega config/ixps.yaml e retorna a lista de IXPs do IX.br.

    Cada entrada contém pelo menos: code, name, city, uf, telnet_host, telnet_port, timeout.
    """
    root = Path(__file__).parent.parent
    path = root / "config" / "ixps.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return data["ixps"]


def load_peeringdb_ixps_config() -> dict:
    """Carrega config/peeringdb_ixps.yaml com a lista de IXPs externos e do IX.br.

    Retorna:
        {"external": [lista de IXPs externos], "ixbr": [lista dos 40 IXPs do IX.br]}

    Cada entrada contém: code, name, city, country, pdb_ix_id.
    Usado pelo `peeringdb_ixps` (peeringdb_ixps) para saber quais IXPs coletar.
    """
    root = Path(__file__).parent.parent
    path = root / "config" / "peeringdb_ixps.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return {"external": data.get("external", []), "ixbr": data.get("ixbr", [])}


def ignorar_sigpipe() -> None:
    """Devolve ao Python o tratamento padrão de SIGPIPE (ignorar → BrokenPipeError).

    O `mrtparse` restaura SIGPIPE para o padrão do sistema ao ser importado. Com isso, um `send()` num socket que o servidor já
    fechou ("Remote end closed connection") mata o processo em silêncio (saída -13) em vez de levantar um erro tratável
    (aborta o `fulltable_routeviews` no meio). Chame logo depois de importar o `mrtparse`."""
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)


def raw_existente(caminho: Path) -> Path:
    """Arquivo bruto de texto, comprimido ou não: `x.txt` se existir, senão `x.txt.gz`, senão o próprio `caminho`.

    O bruto novo é gravado em `.gz`; os snapshots antigos continuam em `.txt`."""
    caminho = Path(caminho)
    if caminho.exists():
        return caminho
    gz = caminho.with_name(caminho.name + ".gz")
    return gz if gz.exists() else caminho


def raw_bgp_ixp(rd: Path, afi: str, code: str, date_str: str) -> Path:
    """Bruto do Looking Glass de um PTT para o snapshot `date_str`.

    Com a coleta diária a fonte `lg_ixbr` pode ficar dentro da cadência semanal: o armazém restaura, em `raw/{date}/`,
    os arquivos da coleta anterior, que mantêm a data de origem no nome. Sem o arquivo da própria data, vale o mais recente
    com data anterior."""
    exato = raw_existente(Path(rd) / f"bgp-{afi}-{code}-{date_str}.txt")
    if exato.exists():
        return exato
    prefixo = f"bgp-{afi}-{code}-"
    achados = []
    for p in Path(rd).glob(prefixo + "*"):
        d = p.name[len(prefixo):len(prefixo) + 10]
        if d <= date_str and p.name[len(prefixo) + 10:] in (".txt", ".txt.gz"):
            achados.append((d, p))
    return max(achados)[1] if achados else exato


def ler_texto_bruto(caminho: Path, errors: str = "strict") -> str:
    """Lê um bruto de texto (`.txt` ou `.txt.gz`; ver `raw_existente`)."""
    c = raw_existente(caminho)
    if c.suffix == ".gz":
        with gzip.open(c, "rt", encoding="utf-8", errors=errors) as f:
            return f.read()
    return c.read_text(encoding="utf-8", errors=errors)


def gravar_texto_gz(caminho_gz: Path, texto: str) -> int:
    """Grava `texto` comprimido de forma atômica; devolve os bytes em disco."""
    caminho_gz = Path(caminho_gz)
    tmp = caminho_gz.with_name(caminho_gz.name + ".tmp")
    # mtime=0 e sem nome no cabeçalho: mesmo texto → mesmos bytes → mesmo hash no armazém de versões
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as f:
        f.write(texto.encode("utf-8"))
    tmp.replace(caminho_gz)
    return caminho_gz.stat().st_size


def configure_logging(level: str | None = None) -> structlog.BoundLogger:
    """Configura structlog com saída JSON (produção) ou texto colorido (desenvolvimento).

    Formato controlado pela variável de ambiente LOG_FORMAT:
      json  — padrão; uma linha JSON por evento (para parsing por ferramentas de log)
      text  — saída colorida com ConsoleRenderer (para desenvolvimento interativo)

    Nível de log controlado pelo parâmetro level ou LOG_LEVEL (padrão: INFO).
    """
    log_level = level or os.environ.get("LOG_LEVEL", "INFO")
    log_format = os.environ.get("LOG_FORMAT", "json")

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    processors: list = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "text":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    return structlog.get_logger()


def today_str() -> str:
    """Retorna a data atual em formato ISO (YYYY-MM-DD)."""
    return date.today().isoformat()


def now_iso() -> str:
    """Retorna o timestamp UTC atual em formato ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


def raw_path(base: Path, date_str: str, *parts: str) -> Path:
    """Constrói caminho em raw/{date_str}/{parts}."""
    return base / "raw" / date_str / Path(*parts)


def normalized_path(base: Path, date_str: str, *parts: str) -> Path:
    """Constrói caminho em normalized/{date_str}/{parts}."""
    return base / "normalized" / date_str / Path(*parts)


_CODIGO_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def codigo_valido(code: object) -> bool:
    """Código de PTT/IXP usado como nome de arquivo (`ixps/{code}.json`): minúsculas, dígitos e hífen. Barra, ponto, `..`, NUL e caminho absoluto não passam."""
    return isinstance(code, str) and _CODIGO_RE.fullmatch(code) is not None


def published_path(base: Path, date_str: str, *parts: str) -> Path:
    """Constrói caminho em published/{date_str}/{parts}."""
    return base / "published" / date_str / Path(*parts)


def build_path(base: Path, date_str: str, *parts: str) -> Path:
    """Área de montagem de uma data: build/{date_str}/{parts} (fragmentos dos produtos; não é publicada)."""
    return base / "build" / date_str / Path(*parts)


def write_json_gz(path: Path, data: dict | list) -> None:
    """Serializa data como JSON e salva comprimido em gzip.

    Cria os diretórios pai se não existirem.
    Não usa indent para minimizar o tamanho do arquivo.
    ensure_ascii=False para preservar caracteres UTF-8 (nomes de organizações BR).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=None)


def read_json_gz(path: Path) -> dict | list:
    """Lê e desserializa um arquivo JSON gzip."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
