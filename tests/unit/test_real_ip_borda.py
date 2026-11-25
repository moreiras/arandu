# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""IP real no nginx do frontend: `docker/entrypoint-real-ip-borda.sh` gera um `set_real_ip_from` por IP declarado em NGINX_REAL_IP_FROM e,
sem a variável, nenhum (o X-Forwarded-For deixa de valer para todos). O efeito no nginx é conferido por `tests/nginx/test_gate.sh`."""
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docker" / "entrypoint-real-ip-borda.sh"


def _gera(tmp_path, valor):
    saida = tmp_path / "real-ip-borda.inc"
    env = {k: v for k, v in os.environ.items() if k != "NGINX_REAL_IP_FROM"} | {"REAL_IP_BORDA_SAIDA": str(saida)}
    if valor is not None:
        env["NGINX_REAL_IP_FROM"] = valor
    r = subprocess.run(["sh", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=30)
    diretivas = [l for l in saida.read_text().splitlines() if l.startswith("set_real_ip_from")] if saida.exists() else None
    return r, diretivas


@pytest.mark.parametrize("valor", [None, "", "   ", " , "])
def test_sem_ip_declarado_nao_emite_set_real_ip_from(tmp_path, valor):
    r, diretivas = _gera(tmp_path, valor)
    assert r.returncode == 0 and diretivas == [], r.stderr


def test_lista_com_espaco_e_virgula_ipv6_e_ipv4(tmp_path):
    r, diretivas = _gera(tmp_path, "2001:db8:ffff::1, 192.0.2.1 198.51.100.0/24,fd00:1::/64")
    assert r.returncode == 0, r.stderr
    assert diretivas == ["set_real_ip_from 2001:db8:ffff::1;", "set_real_ip_from 192.0.2.1;", "set_real_ip_from 198.51.100.0/24;",
                         "set_real_ip_from fd00:1::/64;"]


@pytest.mark.parametrize("valor", ["0.0.0.0/0; allow all", "*", "borda.example.com", "10.0.0.1;"])
def test_valor_mal_formado_falha_a_subida_e_nao_cria_o_arquivo(tmp_path, valor):
    r, _ = _gera(tmp_path, valor)
    assert r.returncode != 0 and "inválido" in r.stderr
    assert not (tmp_path / "real-ip-borda.inc").exists()


def test_o_include_padrao_nao_confia_em_ninguem_e_o_frontend_inclui_o_gerado():
    padrao = (ROOT / "docker" / "nginx-real-ip.inc").read_text()
    assert "set_real_ip_from" not in "\n".join(l for l in padrao.splitlines() if not l.lstrip().startswith("#"))
    conf = (ROOT / "docker" / "nginx-frontend.conf").read_text()
    assert "include /tmp/real-ip-borda*.inc;" in conf
    assert os.access(SCRIPT, os.X_OK)
