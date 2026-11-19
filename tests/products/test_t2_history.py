# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2/T3 — histórico sobre o dataset sintético: T0 → T1 com as diferenças plantadas (cenários 5 e 6 e o novo membro de
`zb`), mais o contrato dos artefatos (esquemas em tests/contracts/schemas/history_*.schema.json).

A confirmação em 2 e 3 snapshots, a saída confirmada, o snapshot parcial e o ROA ganho têm cenário próprio em
tests/unit/test_history_eventos.py (o dataset sintético só tem dois instantes)."""
import gzip
import json
import re
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from core.common import configure_logging
from products.history import build
from tests.synth.world import T0, T1

SCHEMAS = Path(__file__).resolve().parents[1] / "contracts" / "schemas"


@pytest.fixture(scope="module")
def hist(pipeline, tmp_path_factory):
    base0, _ = pipeline
    base = tmp_path_factory.mktemp("hist") / "data"
    shutil.copytree(base0, base)                                       # o publicado do pipeline é compartilhado: escreve numa cópia
    log = configure_logging()
    shutil.rmtree(base / "history")                                    # o pipeline já a construiu; aqui se refaz do zero
    for d in (T0, T1):
        build.construir(base, d, log)
    return base


def _eventos(base, d):
    return build.ler_jsonl_gz(base / "history" / "events" / f"{d}.jsonl.gz")


def _achar(eventos, tipo, **campos):
    return [e for e in eventos if e["tipo"] == tipo and all(e.get(k) == v for k, v in campos.items())]


def test_primeiro_snapshot_nao_tem_eventos(hist):
    assert _eventos(hist, T0) == []


def test_novo_membro_do_ptt_zb_e_cadastral_confirmado_e_observado_pendente(hist):
    ev = _eventos(hist, T1)
    cad = _achar(ev, "ixp_entrada", chave="zb")
    obs = _achar(ev, "ixp_entrada_observada", chave="zb")
    assert len(cad) == 1 and cad[0]["estado"] == "confirmado"
    assert len(obs) == 1 and obs[0]["estado"] == "pendente" and obs[0]["asn"] == cad[0]["asn"]


def test_cenario6_origem_do_prefixo_muda_e_vira_rpki_invalido(hist):
    ev = _eventos(hist, T1)
    (mov,) = _achar(ev, "mudanca_origem", entidade="prefixo:198.18.24.0/21")
    assert (mov["de"], mov["para"], mov["asn"]) == (64502, 64503, 64503)
    assert mov["destaque"] is True and mov["detalhe"]["rpki"] == "invalid" and mov["estado"] == "pendente"
    assert _achar(ev, "rpki_invalido_novo", asn=64503)
    assert _achar(ev, "alerta_novo", asn=64503, chave="rpki_invalido")


def test_cenario5_ptt_com_coleta_parcial_nao_gera_evento_observado(hist):
    ixp = {ln["ixp"]: ln for ln in build.ler_jsonl_gz(hist / "history" / "weekly" / T1 / "ixp.jsonl.gz")}
    assert ixp["zc"]["status"] == "partial"
    assert not [e for e in _eventos(hist, T1) if e["tipo"].endswith("_observada") and e["chave"] == "zc"]


def test_cenario3_um_cnpj_dois_asns_somam_uma_operadora(hist):
    ops = {o["cnpj"]: o for o in build.ler_jsonl_gz(hist / "history" / "weekly" / T1 / "operadora.jsonl.gz")}
    asns = {a["asn"]: a for a in build.ler_jsonl_gz(hist / "history" / "weekly" / T1 / "asn.jsonl.gz")}
    cnpj = asns[64500]["cnpj"]
    assert cnpj == asns[64501]["cnpj"]
    assert ops[cnpj]["n_asns"] >= 2 and ops[cnpj]["users"] >= asns[64500].get("users", 0) + asns[64501].get("users", 0)
    assert ops[cnpj]["n_ma4"] == 2                                      # T0 está a 7 dias de T1: duas amostras na janela


def test_reconstruir_da_os_mesmos_bytes(hist):
    antes = {p.name: p.read_bytes() for p in (hist / "history" / "weekly" / T1).iterdir()}
    build.construir(hist, T1, configure_logging(), force=True)
    assert {p.name: p.read_bytes() for p in (hist / "history" / "weekly" / T1).iterdir()} == antes


def test_historico_nao_tem_contato_nem_dado_de_pessoa(hist):
    """Privacidade: nada de e-mail, telefone, nome de sócio ou documento de pessoa física na camada de histórico."""
    proibido = re.compile(r"@|telefone|ddd_|\bsocios?\b|\*\*\*|\bcpf\b", re.I)
    for p in (hist / "history").rglob("*"):
        if p.is_file():
            texto = gzip.decompress(p.read_bytes()).decode() if p.suffix == ".gz" else p.read_text(encoding="utf-8")
            assert not proibido.search(texto), p


# --- T3: contrato dos artefatos --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arquivo,esquema", [("asn", "history_asn"), ("ixp", "history_ixp"), ("operadora", "history_operadora"),
                                              ("uf", "history_uf")])
def test_t3_linhas_seguem_o_esquema(hist, arquivo, esquema):
    s = json.loads((SCHEMAS / f"{esquema}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(s)
    v = Draft202012Validator(s)
    for d in (T0, T1):
        linhas = build.ler_jsonl_gz(hist / "history" / "weekly" / d / f"{arquivo}.jsonl.gz")
        assert linhas
        erros = [e.message[:120] for ln in linhas for e in v.iter_errors(ln)][:5]
        assert not erros, erros


def test_t3_eventos_e_indice_seguem_o_esquema(hist):
    for nome, docs in (("history_evento", _eventos(hist, T1)),
                       ("history_index", [json.loads((hist / "history" / "index.json").read_text(encoding="utf-8"))])):
        v = Draft202012Validator(json.loads((SCHEMAS / f"{nome}.schema.json").read_text(encoding="utf-8")))
        erros = [e.message[:120] for d in docs for e in v.iter_errors(d)][:5]
        assert docs and not erros, erros
