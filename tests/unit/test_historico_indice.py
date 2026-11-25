# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Caminhos quentes da API memoizados (teste de carga de 2026-11-23): eventos do histórico com índice por entidade, índice de
operadoras e outorgas sem contato montados uma vez por data, diag leve sem o `_debugmallocstats`. A saída tem de ser a de antes."""
import gzip
import json
import os
import random
import time
from pathlib import Path

from api.repos.historico import HistoricoRepo
from api.services import historico as svc

DATAS = ["2026-11-01", "2026-11-08", "2026-11-15", "2026-11-22"]
TIPOS = ["asn_novo", "asn_sumido", "ixp_entrada", "ixp_saida", "ixp_entrada_observada", "mudanca_origem", "roa_ganho", "alerta_rpki",
         "provedor_novo"]


def _gz(p: Path, linhas: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        for ln in linhas:
            f.write(json.dumps(ln, separators=(",", ":")) + "\n")


def _historico(base: Path, semente: int = 7) -> None:
    rnd = random.Random(semente)
    raiz = base / "history"
    raiz.mkdir(parents=True)
    (raiz / "index.json").write_text(json.dumps({"snapshots": [{"date": d, "asn_sha256": f"h{d}"} for d in DATAS]}))
    for d in DATAS:
        _gz(raiz / "weekly" / d / "asn.jsonl.gz", [{"asn": a, "is_br": True, "cnpj": "11111111000111" if a < 64505 else "22222222000122",
                                                    "n_prefixos": rnd.randint(1, 9)} for a in range(64500, 64510)])
        _gz(raiz / "weekly" / d / "ixp.jsonl.gz", [{"ixp": x, "n_membros": rnd.randint(1, 9)} for x in ("sp", "rj", "ce")])
        _gz(raiz / "weekly" / d / "operadora.jsonl.gz", [{"cnpj": c, "acessos": rnd.randint(1, 99)} for c in ("11111111000111", "22222222000122")])
        _gz(raiz / "weekly" / d / "uf.jsonl.gz", [{"uf": u, "n_asns": rnd.randint(1, 9)} for u in ("SP", "RJ", "CE")])
        eventos = []
        for i in range(300):
            tipo = rnd.choice(TIPOS)
            asn = rnd.choice([64500 + k for k in range(10)] + [None])
            ent = rnd.choice([f"asn:{asn}" if asn else "pfx:198.18.0.0/24", "cnpj:11111111000111", "cnpj:22222222000122"])
            e = {"data": d, "tipo": tipo, "entidade": ent, "chave": rnd.choice(["sp", "rj", "ce", f"k{i % 7}"]),
                 "estado": rnd.choice(["confirmado", "pendente", "revertido"]), "destaque": rnd.random() < .2}
            if asn is not None:
                e["asn"] = asn
            if rnd.random() < .6:
                e["uf"] = rnd.choice(["SP", "RJ", "CE"])
            eventos.append(e)
        _gz(raiz / "events" / f"{d}.jsonl.gz", eventos)


def _perfil_antigo(repo: HistoricoRepo, escopo: str, chave: str, completo: bool, recentes: list[str]):
    """O algoritmo de antes (varre e ordena tudo a cada pedido), como referência."""
    datas = [d for d in repo.datas() if completo or d in recentes]
    todos_ord = [e for d in repo.datas() for e in repo.eventos(d)]
    todos_ord.sort(key=lambda e: (e["data"], e["tipo"], e["entidade"], e["chave"]), reverse=True)
    if escopo == "operadora":
        asns = set(repo.asns_do_cnpj(datas[-1], chave))
        casa = lambda e: e.get("asn") in asns or e["entidade"] == f"cnpj:{chave}"      # noqa: E731
    elif escopo == "asn":
        casa = lambda e: e.get("asn") == int(chave)                                     # noqa: E731
    elif escopo == "ixp":
        casa = lambda e: e["tipo"].startswith("ixp_") and e["chave"] == chave           # noqa: E731
    else:
        casa = lambda e: e.get("uf") == chave and not e["tipo"].startswith("alerta_")   # noqa: E731
    todos = [e for e in todos_ord if e["data"] in datas and e["estado"] != "revertido" and e["tipo"] not in svc._INFERIDOS and casa(e)]
    return [{k: e[k] for k in ("data", "tipo", "entidade", "chave", "de", "para", "estado", "destaque") if k in e}
            for e in todos[:svc.LIMITE_EVENTOS_PERFIL]], len(todos)


import pytest  # noqa: E402


@pytest.mark.parametrize("semente", [1, 2, 3, 7, 42])
def test_perfil_pelo_indice_e_igual_ao_de_antes(tmp_path, semente):
    _historico(tmp_path, semente)
    repo = HistoricoRepo(tmp_path)
    casos = [("asn", str(a)) for a in range(64500, 64510)] + [("ixp", x) for x in ("sp", "rj", "ce", "xx")] + \
            [("uf", u) for u in ("SP", "RJ", "CE")] + [("operadora", c) for c in ("11111111000111", "22222222000122")]
    for escopo, chave in casos:
        for completo in (True, False):
            novo = svc.perfil(repo, escopo, chave, completo, DATAS[-2:])
            if novo is None:
                continue
            eventos, total = _perfil_antigo(repo, escopo, chave, completo, DATAS[-2:])
            assert novo["eventos"] == eventos and novo["eventos_total"] == total, (escopo, chave, completo)


def test_eventos_montados_uma_vez_e_refeitos_quando_o_arquivo_muda(tmp_path, monkeypatch):
    _historico(tmp_path)
    repo = HistoricoRepo(tmp_path)
    primeira = repo.todos_eventos()
    assert repo.todos_eventos() is primeira                                          # nada de juntar e ordenar de novo
    assert repo.eventos_de("asn", 64503) == [e for e in primeira if e.get("asn") == 64503]
    arq = tmp_path / "history" / "events" / f"{DATAS[-1]}.jsonl.gz"
    _gz(arq, [{"data": DATAS[-1], "tipo": "asn_novo", "entidade": "asn:64999", "chave": "k", "estado": "confirmado", "asn": 64999}])
    os.utime(arq, (time.time() + 5, time.time() + 5))                                # o pendente decidido regrava o arquivo
    depois = repo.todos_eventos()
    assert depois is not primeira and [e["asn"] for e in repo.eventos_de("asn", 64999)] == [64999]


def test_indice_de_operadoras_e_outorgas_memoizados(monkeypatch):
    from api.outorgas_store import OutorgasPublicadas
    from api.services.operadoras import OperadorasService

    class Fachada:
        scm = {"by_cnpj": {"11111111000111": [{"razao_social": "A", "uf": "SP", "asns": [64500], "email": "x@y"}]}}
        sici = {"cnpjs": {"11111111000111": {"acessos": 10, "asns": [64500]}}, "mes_referencia": "2026-08"}

        def _load_scm(self, d):
            return self.scm

        def _load_sici(self, d):
            return self.sici

        def _load_geo_orgs(self, d):                                                  # vínculo ASN ↔ CNPJ (D5) da linha
            return {64500: {"cnpj": "11111111000111"}}

    f = Fachada()
    s = OperadorasService(f)
    a = s.operadora_index("2026-11-22")
    assert s.operadora_index("2026-11-22") is a and a[0]["acessos"] == 10
    f.sici = {"cnpjs": {"11111111000111": {"acessos": 20, "asns": [64500]}}}          # outro documento carregado: refaz
    assert s.operadora_index("2026-11-22")[0]["acessos"] == 20

    doc = {"outorgas": [{"cnpj": "1", "email": "x@y", "telefone": "1"}]}
    rep = OutorgasPublicadas.__new__(OutorgasPublicadas)
    rep.chave, rep._index_cache = "outorgas", {}
    rep.load = lambda d: doc
    linhas = rep.index("2026-11-22")
    assert rep.index("2026-11-22") is linhas and "email" not in linhas[0] and "email" in doc["outorgas"][0]


def test_diag_leve_nao_percorre_as_arenas(monkeypatch):
    from api import diag

    chamadas = []
    monkeypatch.setattr(diag, "pymalloc_stats", lambda: chamadas.append(1) or {"bytes_em_blocos_vivos": 1})
    vazio = type("StoreVazio", (), {})()
    assert diag.collect(vazio, None, deep=False)["pymalloc"] is None and chamadas == []
    assert diag.collect(vazio, None, deep=True)["pymalloc"] == {"bytes_em_blocos_vivos": 1}
