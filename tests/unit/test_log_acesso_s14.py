# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""o log de acesso não guarda e-mail, tem prazo e sai junto com a conta."""
import gzip
from datetime import date

from api.auth import storage


def _escreve(d, nome, linhas, gz=False):
    p = d / "auth" / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    if gz:
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.writelines(linhas)
    else:
        p.write_text("".join(linhas), encoding="utf-8")
    return p


def test_retencao_apaga_meses_mais_velhos_que_o_prazo(tmp_path):
    for m in ("2026-07", "2026-08", "2026-09", "2026-10", "2026-11"):
        _escreve(tmp_path, f"access_{m}.log" if m >= "2026-10" else f"access_{m}.log.gz", ["x\n"], gz=m < "2026-10")
    assert storage.retencao_log_acesso(tmp_path, date(2026, 11, 15)) == 2               # 3 meses: set, out, nov ficam
    assert sorted(f.name for f in (tmp_path / "auth").iterdir()) == ["access_2026-09.log.gz", "access_2026-10.log", "access_2026-11.log"]
    assert storage.retencao_log_acesso(tmp_path, date(2027, 1, 2)) == 2                 # virada de ano: nov, dez, jan
    assert [f.name for f in (tmp_path / "auth").iterdir()] == ["access_2026-11.log"]


def test_exclusao_tira_as_linhas_da_conta_por_conta_id_e_por_email_antigo(tmp_path):
    a = _escreve(tmp_path, "access_2026-11.log", ["t | 1.2.3.4 | cid-1 | /a\n", "t | 5.6.7.8 | cid-2 | /b\n"])
    b = _escreve(tmp_path, "access_2026-09.log.gz", ["t | 1.2.3.4 | fulano@exemplo.org | /c\n", "t | 9.9.9.9 | cid-2 | /d\n"], gz=True)
    assert storage.apagar_do_log_de_acesso(tmp_path, {"cid-1", "fulano@exemplo.org"}) == 2
    assert a.read_text() == "t | 5.6.7.8 | cid-2 | /b\n"
    assert gzip.open(b, "rt").read() == "t | 9.9.9.9 | cid-2 | /d\n"
    assert storage.apagar_do_log_de_acesso(tmp_path, set()) == 0

