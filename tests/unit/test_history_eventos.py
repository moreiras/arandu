# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — eventos do histórico e janela de confirmação, sobre árvores publicadas mínimas em tmp_path."""
import json

from products.history import build
from products.history import eventos as evs

D = ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"]


class _Log:
    def info(self, *a, **k): pass


def _doc(asn, **kw):
    base = {"asn": asn, "is_br": True, "cnpj": "11", "geo_org": {"uf": "SP"}, "apnic_users": 10,
            "global_prefixes_v4": [f"198.18.{asn % 200}.0/24"], "global_prefixes_v4_count": 1, "global_prefixes_v6_count": 0,
            "ixps_direct": [], "ixp_member_codes": [], "roa_list": [], "rpki_validation": {}, "alerts": []}
    base.update(kw)
    return base


def _snap(tmp, date, docs, manifesto=None, ptts=("sp", "rj"), outorgas=None):
    pub = tmp / "published" / date
    (pub / "asns").mkdir(parents=True, exist_ok=True)
    for d in docs:
        (pub / "asns" / f"{d['asn']}.json").write_text(json.dumps(d), encoding="utf-8")
    (pub / "manifest.json").write_text(json.dumps({"coleta": "completa", "rules_version": "r1", **(manifesto or {})}), encoding="utf-8")
    (pub / "ixps").mkdir(exist_ok=True)
    (pub / "ixps" / "index.json").write_text(json.dumps([{"code": c, "status": "ok"} for c in ptts]), encoding="utf-8")
    for sv, cnpjs in (outorgas or {}).items():
        import gzip
        with gzip.open(pub / f"{sv}.json.gz", "wt", encoding="utf-8") as f:
            json.dump({"by_cnpj": {c: [] for c in cnpjs}}, f)
    build.construir(tmp, date, _Log())


def _eventos(tmp, date):
    return build.ler_jsonl_gz(tmp / "history" / "events" / f"{date}.jsonl.gz")


def _por_tipo(tmp, date):
    return {(e["tipo"], e["chave"]): e for e in _eventos(tmp, date)}


def test_cadastral_confirma_na_hora_e_observado_precisa_de_dois_snapshots(tmp_path):
    _snap(tmp_path, D[0], [_doc(1, ixp_member_codes=["rj"], ixps_direct=["rj"])])
    _snap(tmp_path, D[1], [_doc(1, ixp_member_codes=["rj", "sp"], ixps_direct=["rj", "sp"])])
    e = _por_tipo(tmp_path, D[1])
    assert e[("ixp_entrada", "sp")]["estado"] == "confirmado" and e[("ixp_entrada", "sp")]["janela"] == 1
    assert e[("ixp_entrada_observada", "sp")]["estado"] == "pendente"
    _snap(tmp_path, D[2], [_doc(1, ixp_member_codes=["rj", "sp"], ixps_direct=["rj", "sp"])])
    assert _por_tipo(tmp_path, D[1])[("ixp_entrada_observada", "sp")]["confirmado_em"] == D[2]


def test_pendente_que_volta_atras_fica_revertido(tmp_path):
    _snap(tmp_path, D[0], [_doc(1, ixps_direct=["sp"])])
    _snap(tmp_path, D[1], [_doc(1, ixps_direct=[])])
    assert _por_tipo(tmp_path, D[1])[("ixp_saida_observada", "sp")]["estado"] == "pendente"
    _snap(tmp_path, D[2], [_doc(1, ixps_direct=["sp"])])
    e = _por_tipo(tmp_path, D[1])[("ixp_saida_observada", "sp")]
    assert e["estado"] == "revertido" and e["revertido_em"] == D[2] and e["confirmado"] is False


def test_snapshot_parcial_nao_gera_evento_negativo_nem_decide_pendente(tmp_path):
    _snap(tmp_path, D[0], [_doc(1, ixp_member_codes=["sp"], ixps_direct=["sp"]), _doc(2)])
    _snap(tmp_path, D[1], [_doc(1, ixp_member_codes=["sp"], ixps_direct=[])])               # ASN 2 some, saída observada pendente
    assert {"asn_sumido", "ixp_saida_observada"} <= {e["tipo"] for e in _eventos(tmp_path, D[1])}
    _snap(tmp_path, D[2], [_doc(1, ixp_member_codes=[], ixps_direct=["sp"])], {"coleta": "parcial", "coleta_ok": False})
    negativos = {e["tipo"] for e in _eventos(tmp_path, D[2])} & {t for t, (_, neg) in evs.TIPOS.items() if neg}
    assert negativos == set()                                                                   # a saída cadastral de 1 não vira evento
    # o parcial também não desmente o pendente negativo (a saída observada do D[1] segue pendente, não revertida)
    assert _por_tipo(tmp_path, D[1])[("ixp_saida_observada", "sp")]["estado"] == "pendente"
    assert _por_tipo(tmp_path, D[1])[("asn_sumido", "")]["estado"] == "pendente"


def test_ptt_nao_coletado_nao_gera_evento_observado(tmp_path):
    _snap(tmp_path, D[0], [_doc(1, ixps_direct=["sp"])], ptts=("rj",))
    _snap(tmp_path, D[1], [_doc(1, ixps_direct=[])], ptts=("rj",))
    assert [e for e in _eventos(tmp_path, D[1]) if e["tipo"].startswith("ixp_")] == []


def test_origem_so_quando_unica_e_destaca_rpki_invalido(tmp_path):
    p = "198.18.77.0/24"
    _snap(tmp_path, D[0], [_doc(1, global_prefixes_v4=[p]), _doc(2, global_prefixes_v4=[]), _doc(3, global_prefixes_v4=[]),
                           _doc(4, global_prefixes_v4=["198.18.88.0/24"]), _doc(5, global_prefixes_v4=[])])
    _snap(tmp_path, D[1], [_doc(1, global_prefixes_v4=[]), _doc(2, global_prefixes_v4=[p], rpki_validation={p: "invalid"}),
                           _doc(3, global_prefixes_v4=[]),
                           _doc(4, global_prefixes_v4=[]), _doc(5, global_prefixes_v4=["198.18.88.0/24"])])
    e = _por_tipo(tmp_path, D[1])
    mov = e[("mudanca_origem", "2")]
    assert (mov["de"], mov["para"], mov["entidade"], mov["destaque"]) == (1, 2, f"prefixo:{p}", True)
    assert e[("mudanca_origem", "5")]["de"] == 4 and "destaque" not in e[("mudanca_origem", "5")]


def test_origem_com_outro_detentor_e_moas_e_nao_vira_evento(tmp_path):
    p = "198.18.99.0/24"
    _snap(tmp_path, D[0], [_doc(1, global_prefixes_v4=[p]), _doc(2, global_prefixes_v4=[]), _doc(3, global_prefixes_v4=[p])])
    _snap(tmp_path, D[1], [_doc(1, global_prefixes_v4=[]), _doc(2, global_prefixes_v4=[p]), _doc(3, global_prefixes_v4=[p])])
    assert [e for e in _eventos(tmp_path, D[1]) if e["tipo"] == "mudanca_origem"] == []


def test_origem_entre_estrangeiros_fica_fora_do_recorte(tmp_path):
    p = "203.0.113.0/24"
    _snap(tmp_path, D[0], [_doc(1, is_br=False, global_prefixes_v4=[p]), _doc(2, is_br=False, global_prefixes_v4=[])])
    _snap(tmp_path, D[1], [_doc(1, is_br=False, global_prefixes_v4=[]), _doc(2, is_br=False, global_prefixes_v4=[p])])
    assert [e for e in _eventos(tmp_path, D[1]) if e["tipo"] == "mudanca_origem"] == []


def test_roa_aspa_e_rpki_invalido(tmp_path):
    _snap(tmp_path, D[0], [_doc(1)])
    _snap(tmp_path, D[1], [_doc(1, roa_list=[{"asn": 1}], aspa_providers=[{"asn": 9}], rpki_validation={"x": "invalid"})])
    assert {e["tipo"] for e in _eventos(tmp_path, D[1])} == {"roa_ganho", "aspa_ganho", "rpki_invalido_novo"}


def test_outorga_nova_na_hora_e_baixa_em_dois_snapshots(tmp_path):
    _snap(tmp_path, D[0], [_doc(1)], outorgas={"scm": ["10", "20"]})
    _snap(tmp_path, D[1], [_doc(1)], outorgas={"scm": ["10", "30"]})
    e = _por_tipo(tmp_path, D[1])
    assert e[("outorga_nova", "scm")]["entidade"] == "cnpj:30" and e[("outorga_nova", "scm")]["estado"] == "confirmado"
    assert e[("outorga_baixa", "scm")]["entidade"] == "cnpj:20" and e[("outorga_baixa", "scm")]["estado"] == "pendente"
    _snap(tmp_path, D[2], [_doc(1)], outorgas={"scm": ["10", "30"]})
    assert _por_tipo(tmp_path, D[1])[("outorga_baixa", "scm")]["estado"] == "confirmado"


def test_alertas_so_se_comparam_com_a_mesma_versao_de_regras(tmp_path):
    _snap(tmp_path, D[0], [_doc(1)], {"rules_version": "r1"})
    _snap(tmp_path, D[1], [_doc(1, alerts=[{"id": "sem_aspa"}])], {"rules_version": "r2"})
    assert [e for e in _eventos(tmp_path, D[1]) if e["tipo"].startswith("alerta")] == []
    _snap(tmp_path, D[2], [_doc(1, alerts=[])], {"rules_version": "r2"})
    assert {e["tipo"] for e in _eventos(tmp_path, D[2])} == {"alerta_resolvido"}


def test_provedor_precisa_de_tres_snapshots(tmp_path):
    rel = {"provedores": [{"asn": 9, "nivel": "confirmado"}, {"asn": 8, "nivel": "provavel"}]}
    _snap(tmp_path, D[0], [_doc(1, relacoes={"provedores": []})])
    for d in D[1:3]:
        _snap(tmp_path, d, [_doc(1, relacoes=rel)])
    ev = _por_tipo(tmp_path, D[1])[("provedor_novo", "9")]
    assert ev["estado"] == "pendente" and ("provedor_novo", "8") not in _por_tipo(tmp_path, D[1])      # provável não conta
    _snap(tmp_path, D[3], [_doc(1, relacoes=rel)])
    assert _por_tipo(tmp_path, D[1])[("provedor_novo", "9")]["confirmado_em"] == D[3]


def test_primeiro_snapshot_nao_tem_eventos_e_reconstruir_e_idempotente(tmp_path):
    _snap(tmp_path, D[0], [_doc(1)])
    assert _eventos(tmp_path, D[0]) == []
    _snap(tmp_path, D[1], [_doc(1), _doc(2)])
    antes = (tmp_path / "history" / "events" / f"{D[1]}.jsonl.gz").read_bytes()
    build.construir(tmp_path, D[1], _Log(), force=True)
    assert (tmp_path / "history" / "events" / f"{D[1]}.jsonl.gz").read_bytes() == antes
    assert [e["tipo"] for e in _eventos(tmp_path, D[1])] == ["asn_novo"]


# --- campo-fonte ausente não vira zero (TRANSV-E8, D7) ------------------------------------------------------------------------------

def _estrangeiro(asn, **kw):
    """ASN estrangeiro como sai hoje: sem o enriquecimento RPKI/ASPA (só ASN BR passa pela etapa de saúde)."""
    return {"asn": asn, "is_br": False, "global_prefixes_v4": ["203.0.113.0/24"], "global_prefixes_v4_count": 1, **kw}


def test_campo_presente_so_num_snapshot_nao_gera_evento(tmp_path):
    """Cenário da V1: em 2026-06-28 os estrangeiros tinham `roa_list`, `aspa_providers` e `rpki_validation`; a partir de 2026-07-05 não.
    A regra antiga lia a ausência como zero e gerou 50.127 `roa_perdido` (AS9997: 11 ROAs e depois "0", prefixos iguais)."""
    roas = [{"prefix": f"203.0.113.0/{24 + i}", "asn": 9997} for i in range(3)]
    _snap(tmp_path, D[0], [_estrangeiro(9997, roa_list=roas, aspa_providers=[{"asn": 1}], rpki_validation={"203.0.113.0/24": "invalid"})])
    _snap(tmp_path, D[1], [_estrangeiro(9997)])
    _snap(tmp_path, D[2], [_estrangeiro(9997)])
    assert {e["tipo"] for e in _eventos(tmp_path, D[1])} == set()
    assert {e["tipo"] for e in _eventos(tmp_path, D[2])} == set()
    ln = build.ler_jsonl_gz(tmp_path / "history" / "weekly" / D[1] / "asn.jsonl.gz")[0]
    assert "n_roa" not in ln and "n_aspa" not in ln and "rpki_invalid" not in ln            # ausência fica ausência, não zero
    assert ln["tem_roa_list"] is False and ln["tem_saude"] is False
    l0 = build.ler_jsonl_gz(tmp_path / "history" / "weekly" / D[0] / "asn.jsonl.gz")[0]
    assert l0["n_roa"] == 3 and l0["tem_roa_list"] is True


def test_campo_presente_nos_dois_continua_gerando_evento(tmp_path):
    """Estrangeiro com o campo nos dois snapshots que de fato remove os ROAs (a lista fica vazia) continua gerando `roa_perdido`."""
    _snap(tmp_path, D[0], [_estrangeiro(9997, roa_list=[{"prefix": "203.0.113.0/24"}], rpki_validation={"203.0.113.0/24": "invalid"})])
    _snap(tmp_path, D[1], [_estrangeiro(9997, roa_list=[], rpki_validation={"203.0.113.0/24": "not_found"})])
    assert {e["tipo"] for e in _eventos(tmp_path, D[1])} == {"roa_perdido", "rpki_invalido_resolvido"}


def test_aspa_removido_por_asn_br_com_saude_nos_dois_gera_evento(tmp_path):
    """`aspa_providers` só existe quando há ASPA: num documento que passou pela etapa de saúde (tem `alerts`), a ausência é zero de fato."""
    _snap(tmp_path, D[0], [_doc(1, aspa_providers=[{"asn": 9}])])
    _snap(tmp_path, D[1], [_doc(1)])
    assert {e["tipo"] for e in _eventos(tmp_path, D[1])} == {"aspa_perdido"}


def test_asn_br_sem_saude_num_snapshot_nao_gera_evento(tmp_path):
    doc = _doc(1, roa_list=[{"prefix": "198.18.1.0/24"}], aspa_providers=[{"asn": 9}], rpki_validation={"198.18.1.0/24": "invalid"})
    sem = {k: v for k, v in _doc(1).items() if k not in ("roa_list", "rpki_validation", "alerts")}
    _snap(tmp_path, D[0], [doc])
    _snap(tmp_path, D[1], [sem])
    assert _eventos(tmp_path, D[1]) == []
    _snap(tmp_path, D[2], [doc])                            # a cobertura volta: o que já existia não vira "ganho"
    assert _eventos(tmp_path, D[2]) == []


def test_linha_antiga_sem_marcador_e_completada_antes_de_comparar(tmp_path):
    """Histórico gravado pela regra 1 (sem `tem_*`): o snapshot anterior é completado lendo o publicado antes da comparação."""
    import gzip as gz

    _snap(tmp_path, D[0], [_estrangeiro(9997, roa_list=[{"prefix": "203.0.113.0/24"}])])
    arq = tmp_path / "history" / "weekly" / D[0] / "asn.jsonl.gz"
    velhas = [{k: v for k, v in ln.items() if not k.startswith("tem_")} | {"n_roa": ln.get("n_roa", 0)} for ln in build.ler_jsonl_gz(arq)]
    arq.write_bytes(gz.compress("".join(json.dumps(x) + "\n" for x in velhas).encode()))
    _snap(tmp_path, D[1], [_estrangeiro(9997)])
    assert _eventos(tmp_path, D[1]) == []
    assert build.ler_jsonl_gz(arq)[0]["tem_roa_list"] is True


def test_documento_de_snapshot_compactado_e_lido_do_zip(tmp_path):
    """Snapshot antigo passa ao formato 2 (`asns.zip`): o gerador de eventos tem de ler os documentos de lá."""
    import shutil
    import zipfile

    _snap(tmp_path, D[0], [_doc(1, ixp_member_codes=["rj"])])
    pub = tmp_path / "published" / D[0]
    with zipfile.ZipFile(pub / "asns.zip", "w") as z:
        for p in (pub / "asns").iterdir():
            z.write(p, p.name)
    shutil.rmtree(pub / "asns")
    from products.history.snapshot import Snap
    assert Snap(tmp_path, D[0]).doc(1)["ixp_member_codes"] == ["rj"]
    _snap(tmp_path, D[1], [_doc(1, ixp_member_codes=["rj", "sp"])])
    assert {(e["tipo"], e["chave"]) for e in _eventos(tmp_path, D[1])} == {("ixp_entrada", "sp")}


def test_regenerar_eventos_aplica_a_regra_nova_e_relata_antes_e_depois(tmp_path):
    """A regeneração (D7) completa os marcadores das linhas, refaz os eventos de todas as datas e devolve a contagem por tipo antes e depois."""
    import gzip as gz
    from products.history import regenerar_eventos as reg

    _snap(tmp_path, D[0], [_estrangeiro(9997, roa_list=[{"prefix": "203.0.113.0/24"}]), _doc(1)])
    _snap(tmp_path, D[1], [_estrangeiro(9997), _doc(1, ixp_member_codes=["sp"])])
    # simula o histórico gravado pela regra 1: linhas sem marcador e o artefato `roa_perdido` em D[1]
    for d in D[:2]:
        arq = tmp_path / "history" / "weekly" / d / "asn.jsonl.gz"
        velhas = [{k: v for k, v in ln.items() if not k.startswith("tem_")} for ln in build.ler_jsonl_gz(arq)]
        arq.write_bytes(gz.compress("".join(json.dumps(x) + "\n" for x in velhas).encode()))
    ev = tmp_path / "history" / "events" / f"{D[1]}.jsonl.gz"
    artefato = {"id": "x", "data": D[1], "tipo": "roa_perdido", "entidade": "asn:9997", "chave": "", "de": 1, "para": 0, "janela": 1,
                "estado": "confirmado", "asn": 9997, "confirmado": True, "confirmado_em": D[1]}
    ev.write_bytes(gz.compress("".join(json.dumps(x) + "\n" for x in [artefato, *build.ler_jsonl_gz(ev)]).encode()))
    rel = reg.regenerar(tmp_path, _Log())
    assert rel["regra"] == evs.REGRA_VERSAO
    assert rel["datas"][D[1]]["roa_perdido"] == {"antes": 1, "depois": 0}
    assert rel["datas"][D[1]]["ixp_entrada"] == {"antes": 1, "depois": 1}
    assert {e["tipo"] for e in _eventos(tmp_path, D[1])} == {"ixp_entrada"}
    idx = json.loads((tmp_path / "history" / "index.json").read_text(encoding="utf-8"))
    assert {s["date"]: s["eventos_regra"] for s in idx["snapshots"]} == {D[0]: evs.REGRA_VERSAO, D[1]: evs.REGRA_VERSAO}
    assert all("tem_roa_list" in ln for ln in build.ler_jsonl_gz(tmp_path / "history" / "weekly" / D[0] / "asn.jsonl.gz"))
    assert reg.regenerar(tmp_path, _Log())["datas"][D[1]]["ixp_entrada"] == {"antes": 1, "depois": 1}     # idempotente
    assert not list((tmp_path / "history").rglob("*.tmp"))
