# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — linha de histórico do ASN e gravação determinística."""
import gzip
import json

from products.history import build
from products.history.linhas import hash_conjunto, linha_asn


def _doc(**kw):
    base = {"asn": 64500, "is_br": True, "apnic_users": 1000, "apnic_v6_users": 100,
            "global_prefixes_v4": ["198.18.0.0/24", "198.18.1.0/24"], "global_prefixes_v6": ["2001:db8::/32"],
            "global_prefixes_v4_count": 2, "global_prefixes_v6_count": 1,
            "ixps_direct": ["sp"], "ixp_member_codes": ["sp", "rj"],
            "roa_list": [{"asn": 64500}], "rpki_validation": {"a": "valid", "b": "invalid", "c": "not_found", "d": "valid"},
            "alerts": [{"id": "sem_aspa"}, {"id": "rpki_invalido"}]}
    base.update(kw)
    return base


def test_linha_conta_o_que_o_documento_diz():
    ln = linha_asn(_doc())
    assert (ln["asn"], ln["is_br"], ln["users"], ln["v6users"], ln["p4"], ln["p6"]) == (64500, True, 1000, 100, 2, 1)
    assert (ln["n_ixd"], ln["n_ixm"], ln["n_roa"], ln["n_alertas"]) == (1, 2, 1, 2)
    assert (ln["rpki_valid"], ln["rpki_invalid"], ln["rpki_not_found"]) == (2, 1, 1)


def test_sem_bloco_de_relacoes_n_provedores_fica_ausente():
    ln = linha_asn(_doc())
    assert "n_provedores" not in ln and "hash_relacoes" not in ln       # nunca zero inventado


def test_provedores_so_confirmado_ou_superior():
    prov = [{"asn": 1, "nivel": "declarado"}, {"asn": 2, "nivel": "confirmado"}, {"asn": 3, "nivel": "provavel"},
            {"asn": 4, "nivel": "possivel"}]
    ln = linha_asn(_doc(relacoes={"provedores": prov}))
    assert ln["n_provedores"] == 2
    assert ln["hash_relacoes"] == hash_conjunto([1, 2])


def test_asn_estrangeiro_sem_alertas_nem_usuarios():
    ln = linha_asn({"asn": 15169, "is_br": False, "global_prefixes_v4_count": 10})
    assert "n_alertas" not in ln and "users" not in ln and ln["p4"] == 10


def test_hash_do_conjunto_nao_depende_da_ordem():
    assert hash_conjunto(["b", "a"]) == hash_conjunto(["a", "b"])
    assert hash_conjunto([]) is None


def _publicar(base, date, docs, manifesto):
    pub = base / "published" / date
    (pub / "asns").mkdir(parents=True)
    for d in docs:
        (pub / "asns" / f"{d['asn']}.json").write_text(json.dumps(d), encoding="utf-8")
    (pub / "manifest.json").write_text(json.dumps(manifesto), encoding="utf-8")


class _Log:
    def info(self, *a, **k): pass


def test_construir_e_deterministico_e_idempotente(tmp_path):
    _publicar(tmp_path, "2026-09-20", [_doc(asn=64501), _doc(asn=64500)],
              {"coleta": "parcial", "coleta_ok": False, "ixps_collected": ["sp"], "ixps_failed": ["zc"], "rules_version": "rX"})
    e1 = build.construir(tmp_path, "2026-09-20", _Log())
    arq = tmp_path / "history" / "weekly" / "2026-09-20" / "asn.jsonl.gz"
    bytes1 = arq.read_bytes()
    linhas = [json.loads(x) for x in gzip.decompress(bytes1).decode().splitlines()]
    assert [x["asn"] for x in linhas] == [64500, 64501]                        # ordem numérica
    assert e1["coleta"] == "parcial" and e1["ptts_falhos"] == ["zc"] and e1["rules_version"] == "rX"
    assert build.construir(tmp_path, "2026-09-20", _Log())["pulado"] is True    # sem --force não refaz
    build.construir(tmp_path, "2026-09-20", _Log(), force=True)
    assert arq.read_bytes() == bytes1                                           # mesmos bytes
    idx = json.loads((tmp_path / "history" / "index.json").read_text(encoding="utf-8"))
    assert [s["date"] for s in idx["snapshots"]] == ["2026-09-20"]
    assert not list((tmp_path / "history").rglob("*.tmp"))


def test_snapshot_inexistente_falha_alto(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        build.construir(tmp_path, "2000-01-01", _Log())


# --- séries agregadas -------------------------------------------------------------------------------------------------------------
from products.history import agregados as ag


def _br(asn, cnpj, uf, users, **kw):
    return {"asn": asn, "is_br": True, "cnpj": cnpj, "uf": uf, "users": users, "v6users": users // 2, "p4": 1, **kw}


def test_operadora_soma_asns_do_mesmo_cnpj_e_ignora_estrangeiros():
    linhas = [_br(1, "11", "SP", 100), _br(2, "11", "SP", 50), _br(3, "22", "RJ", 10),
              {"asn": 15169, "is_br": False, "users": 999}]
    ops = ag.agregar_operadoras(linhas, {"11": "g1"})
    assert ops["11"]["n_asns"] == 2 and ops["11"]["users"] == 150 and ops["11"]["grupo_id"] == "g1"
    assert set(ops) == {"11", "22"} and "grupo_id" not in ops["22"]


def test_uf_conta_cnpjs_distintos():
    ufs = ag.agregar_ufs([_br(1, "11", "SP", 100), _br(2, "11", "SP", 50), _br(3, "22", "SP", 10), _br(4, "33", "RJ", 5)])
    assert ufs["SP"]["n_asns"] == 3 and ufs["SP"]["n_cnpjs"] == 2 and ufs["SP"]["users"] == 160 and ufs["RJ"]["n_cnpjs"] == 1
    assert ag.linhas_uf(ufs)[0]["uf"] == "RJ"


def test_media_movel_so_usa_datas_anteriores_na_janela():
    assert ag.dentro_da_janela("2026-10-31", "2026-10-11") and not ag.dentro_da_janela("2026-10-31", "2026-10-03")
    assert not ag.dentro_da_janela("2026-10-11", "2026-10-11") and not ag.dentro_da_janela("2026-10-11", "2026-10-20")
    atual = {"11": {"users": 300}, "22": {"users": 10}}
    r = ag.com_media_movel(atual, [{"11": {"users": 100}}, {"11": {"users": 200}}])
    assert r["11"]["users_ma4"] == 200.0 and r["11"]["n_ma4"] == 3
    assert r["22"]["users_ma4"] == 10.0 and r["22"]["n_ma4"] == 1


def test_linhas_ixp_do_indice_publicado():
    ln = ag.linhas_ixp([{"code": "sp", "status": "ok", "asn_direct_union_count": 10, "ixbr_members_count": 12,
                          "v4": {"total_routes": 5, "unique_prefixes": 4}, "v6": {}}])
    assert ln == [{"ixp": "sp", "status": "ok", "n_direct": 10, "n_membros": 12, "v4_rotas": 5, "v4_prefixos": 4}]


def test_construir_grava_as_series_e_a_media_acumula_entre_datas(tmp_path):
    for d, users in (("2026-09-13", 100), ("2026-09-20", 300)):
        doc = _doc(asn=64500, cnpj="11", geo_org={"uf": "SP"}, apnic_users=users)
        _publicar(tmp_path, d, [doc], {"ixps_collected": ["sp"]})
        (tmp_path / "published" / d / "ixps").mkdir()
        (tmp_path / "published" / d / "ixps" / "index.json").write_text(json.dumps([{"code": "sp", "status": "ok"}]), encoding="utf-8")
        build.construir(tmp_path, d, _Log())
    ops = build.ler_jsonl_gz(tmp_path / "history" / "weekly" / "2026-09-20" / "operadora.jsonl.gz")
    assert ops[0]["cnpj"] == "11" and ops[0]["users"] == 300 and ops[0]["users_ma4"] == 200.0 and ops[0]["n_ma4"] == 2
    assert build.ler_jsonl_gz(tmp_path / "history" / "weekly" / "2026-09-20" / "uf.jsonl.gz")[0]["uf"] == "SP"
    assert build.ler_jsonl_gz(tmp_path / "history" / "weekly" / "2026-09-20" / "ixp.jsonl.gz")[0]["ixp"] == "sp"
