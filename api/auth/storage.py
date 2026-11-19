# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Armazenamento de tokens de autenticação pendentes (magic links).

Usa um CSV com fcntl advisory lock para evitar condições de corrida em
ambientes single-host. Não é um banco de dados — entradas expiram por TTL
e são limpas na próxima leitura.
"""
from __future__ import annotations

import csv
import fcntl
import gzip
import io
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


_AUTH_DIR = "auth"
_EMAIL_FILE = "emails.csv"
_EMAIL_FIELDS = ["email", "nome", "provedor", "primeiro_acesso", "ultimo_acesso"]


def _auth_dir(data_path: Path) -> Path:
    d = data_path / _AUTH_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def upsert_user(data_path: Path, email: str, name: str, provider: str) -> None:
    """Insere ou atualiza usuário no CSV de emails. Escrita atômica com lock."""
    path = _auth_dir(data_path) / _EMAIL_FILE
    lock_path = path.with_suffix(".lock")
    now = datetime.now(timezone.utc).isoformat()

    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            rows: dict[str, dict] = {}
            if path.exists():
                with open(path, newline="") as f:
                    for row in csv.DictReader(f):
                        rows[row["email"]] = row

            if email in rows:
                rows[email]["ultimo_acesso"] = now
                rows[email]["nome"] = name
            else:
                rows[email] = {
                    "email": email,
                    "nome": name,
                    "provedor": provider,
                    "primeiro_acesso": now,
                    "ultimo_acesso": now,
                }

            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_EMAIL_FIELDS)
                writer.writeheader()
                writer.writerows(rows.values())
            tmp.rename(path)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def remover_usuario(data_path: Path, email: str) -> bool:
    """Tira o e-mail do cadastro em CSV (exclusão efetiva da conta). Escrita atômica com o mesmo lock."""
    path = _auth_dir(data_path) / _EMAIL_FILE
    if not path.exists():
        return False
    with open(path.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(path, newline="") as f:
                rows = [r for r in csv.DictReader(f)]
            mantidas = [r for r in rows if (r["email"] or "").strip().lower() != (email or "").strip().lower()]     # sem distinção de maiúsculas
            if len(mantidas) == len(rows):
                return False
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=_EMAIL_FIELDS)
                w.writeheader()
                w.writerows(mantidas)
            tmp.rename(path)
            return True
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


# a identidade no log é o
# `conta_id` (nunca o e-mail nem o IP), os meses mais velhos que RETENCAO_LOG_MESES são apagados pela manutenção diária e a exclusão de conta tira as
# linhas dela (inclusive as gravadas com e-mail, se houver).
RETENCAO_LOG_MESES = 3


def log_access(data_path: Path, ip: str, identity: str, path_accessed: str) -> None:
    """Acrescenta uma linha ao log do mês corrente e compacta meses antigos. `identity` é o `conta_id` da sessão (nunca o e-mail)."""
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    log_path = _auth_dir(data_path) / f"access_{month}.log"
    line = f"{now.isoformat()} | {ip} | {identity} | {path_accessed}\n"
    with open(log_path, "a") as f:
        f.write(line)
    _rotate_old_logs(_auth_dir(data_path))


def _rotate_old_logs(d: Path) -> None:
    """Compacta logs mais antigos que o mês anterior."""
    today = date.today()
    keep = {
        today.strftime("%Y-%m"),
        (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m"),
    }
    for f in d.glob("access_*.log"):
        month = f.stem.replace("access_", "")
        if month not in keep:
            gz = f.with_suffix(".log.gz")
            if not gz.exists():
                with open(f, "rb") as src, gzip.open(gz, "wb") as dst:
                    dst.write(src.read())
                f.unlink()


def _mes_do_log(f: Path) -> str:
    return f.name.split("access_", 1)[1].split(".", 1)[0]          # access_AAAA-MM.log[.gz] → AAAA-MM


def retencao_log_acesso(data_path: Path, hoje: date | None = None, meses: int = RETENCAO_LOG_MESES) -> int:
    """Apaga os logs de acesso de meses mais velhos que `meses` (o corrente conta como o primeiro). Devolve quantos arquivos apagou."""
    hoje = hoje or date.today()
    ano, mes = hoje.year, hoje.month - (meses - 1)
    while mes < 1:
        ano, mes = ano - 1, mes + 12
    limite = f"{ano:04d}-{mes:02d}"
    apagados = 0
    for f in list(_auth_dir(data_path).glob("access_*.log*")):
        if _mes_do_log(f) < limite:
            f.unlink(missing_ok=True)
            apagados += 1
    return apagados


def apagar_do_log_de_acesso(data_path: Path, identidades: set[str]) -> int:
    """Remove as linhas cujo 3º campo (`conta_id`, ou o e-mail nas linhas antigas) está em `identidades`. Devolve quantas linhas saíram."""
    ids = {i for i in identidades if i}
    if not ids:
        return 0
    removidas = 0
    for f in _auth_dir(data_path).glob("access_*.log*"):
        gz = f.suffix == ".gz"
        abrir = (lambda p, m: gzip.open(p, m + "t", encoding="utf-8")) if gz else (lambda p, m: open(p, m, encoding="utf-8"))
        with abrir(f, "r") as src:
            linhas = src.readlines()
        ficam = [ln for ln in linhas if (ln.split(" | ") + ["", "", ""])[2].strip() not in ids]
        if len(ficam) == len(linhas):
            continue
        removidas += len(linhas) - len(ficam)
        tmp = f.with_name(f.name + ".tmp")
        with abrir(tmp, "w") as dst:
            dst.writelines(ficam)
        tmp.replace(f)                                   # escrita atômica
    return removidas
