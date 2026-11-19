# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — regras de alerta: cada regra tem um cenário plantado que a dispara e um que não dispara; o conjunto cobre 100%."""
import ipaddress

import pytest

from products.alerts import registro
from products.alerts.base import Contexto

ASN = 64500


class FakeStore:
    """Só o que as regras pedem à `Store`."""

    def __init__(self, origem=None, ra=None, coords=None, pix=None, ixps=None, rs=None):
        self.origem = origem or {"v4": {}, "v6": {}}
        self.rs = rs
        self.ra, self.coords, self.pix, self.ixps = ra, coords, pix or {}, ixps or []

    def origin_by_prefix(self, d, afi): return self.origem[afi]

    def announced_starts(self, d, afi):
        return sorted(int(ipaddress.ip_network(p).network_address) for p in self.origem[afi])

    def routing_analysis(self, d): return self.ra
    def asn_coords(self, d, asn): return self.coords
    def _load_pix_config(self): return self.pix
    def ixp_index(self, d): return self.ixps
    def route_servers_asns_doc(self, d): return self.rs


def _ids(doc, store=None):
    return [a["id"] for a in registro.calcular_alertas(store or FakeStore(), "2026-10-23", ASN, doc)]


def _doc(**kw):
    base = {"asn": ASN, "rir_prefixes_v4": ["203.0.113.0/24"], "rir_prefixes_v6": ["2001:db8::/32"],
            "global_prefixes_v4": ["203.0.113.0/24"], "global_prefixes_v6": ["2001:db8::/32"]}
    base.update(kw)
    return base


def _rs(**ixp):
    return {"coletado_em": "2026-11-01T00:59:00+00:00", "dias_down": 7, "uso_limite": 0.8, "asns": {str(ASN): {"ixps": {"sp": {"membro_down": False, "perto_do_limite": False, **ixp}}}}}


RA = {
    "aggregation_by_asn": [{"asn": ASN, "afi": "v4", "savings_path_pct": 95, "current": 20, "by_origin": 1}],
    "too_specific": {"v4": [{"origin_as": ASN, "prefix": "203.0.113.0/28"}], "v6": []},
    "as_path_stats": {"top_prependers": [{"asn": ASN, "afi": "v4", "avg_excess": 3.5, "routes_with_prepend": 9}],
                      "hygiene_issues": [{"origin_as": ASN, "issue": "as_loop", "prefix": "203.0.113.0/24"}]},
}
PIX = {"sp": [{"lat": -23.55, "lon": -46.63}]}

RS_DOWN = FakeStore(rs=_rs(membro_down=True, max_dias_down=12))
RS_PERTO = FakeStore(rs=_rs(perto_do_limite=True, max_uso_limite=0.9))
# regra -> (documento/loja que DISPARA, ids esperados dessa regra, documento/loja que NÃO dispara)
CENARIOS = {
    "sessao_rs_down": (dict(doc=_doc(), store=RS_DOWN), ["sessao_rs_down"], dict(doc=_doc(), store=FakeStore(rs=_rs(max_dias_down=3)))),
    "import_limit_proximo": (dict(doc=_doc(), store=RS_PERTO), ["import_limit_proximo"], dict(doc=_doc(), store=FakeStore(rs=_rs(max_uso_limite=0.5)))),
    "sem_ipv6": (dict(doc=_doc(rir_prefixes_v6=[], global_prefixes_v6=[])), ["sem_ipv6"], dict(doc=_doc())),
    "prefixo_inalcancavel": (dict(doc=_doc(), store=FakeStore(origem={"v4": {"198.51.100.0/24": 1}, "v6": {"2001:db8:ffff::/48": 1}})),
                             ["prefixo_inalcancavel"], dict(doc=_doc(), store=FakeStore(origem={"v4": {"203.0.113.0/24": ASN}, "v6": {"2001:db8::/32": ASN}}))),
    "anuncio_por_outro_as": (dict(doc=_doc(), store=FakeStore(origem={"v4": {"203.0.113.0/24": 64999}, "v6": {"2001:db8::/32": ASN}})),
                             ["anuncio_por_outro_as"], dict(doc=_doc(), store=FakeStore(origem={"v4": {"203.0.113.0/24": ASN}, "v6": {"2001:db8::/32": ASN}}))),
    "desagregacao": (dict(doc=_doc(global_prefixes_v4_count=40, global_prefixes_v6_count=3)), ["desagregacao_ipv4"], dict(doc=_doc(global_prefixes_v4_count=5))),
    "prefixo_fora_alocacao": (dict(doc=_doc(global_prefixes_v4=["203.0.113.0/24", "192.0.2.0/24"])), ["prefixo_fora_alocacao"], dict(doc=_doc())),
    "sem_rpki": (dict(doc=_doc(roa_list=[])), ["sem_rpki"], dict(doc=_doc())),                      # sem roa_list = validação não avaliada
    "rpki_invalido": (dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}], rpki_validation={"203.0.113.0/24": "invalid"})),
                      ["rpki_invalido"], dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}], rpki_validation={"203.0.113.0/24": "valid"}))),
    "rpki_cobertura_parcial": (dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}])), ["rpki_cobertura_parcial"],
                               dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}, {"prefix": "2001:db8::/32", "maxLength": 32}]))),
    "roa_maxlength_folgado": (dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 32}, {"prefix": "2001:db8::/32", "maxLength": 32}])),
                              ["roa_maxlength_folgado"], dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}, {"prefix": "2001:db8::/32", "maxLength": 32}]))),
    "sem_aspa": (dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}, {"prefix": "2001:db8::/32", "maxLength": 32}])), ["sem_aspa"],
                 dict(doc=_doc(roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}, {"prefix": "2001:db8::/32", "maxLength": 32}], aspa_providers=[1]))),
    "politica_v4v6_divergente": (dict(doc=_doc(ixp_presence={"sp": {"v4": {"direct": True}, "v6": {"direct": False}}})), ["politica_v4v6_divergente"],
                                 dict(doc=_doc(ixp_presence={"sp": {"v4": {"direct": True}, "v6": {"direct": True}}}))),
    "sem_peeringdb": (dict(doc=_doc(ixp_member_codes=["sp"], pdb_registered=False)), ["sem_peeringdb"], dict(doc=_doc(ixp_member_codes=["sp"], pdb_registered=True, pdb={"irr_as_set": "AS-X"}))),
    "sem_irr_as_set": (dict(doc=_doc(pdb_registered=True, pdb={})), ["sem_irr_as_set"], dict(doc=_doc(pdb_registered=True, pdb={"irr_as_set": "AS-X"}))),
    "membro_sem_peering": (dict(doc=_doc(ixp_member_codes=["sp"], pdb_registered=True, pdb={"irr_as_set": "AS-X"}, ixp_presence={})), ["membro_sem_peering"],
                           dict(doc=_doc(ixp_member_codes=["sp"], pdb_registered=True, pdb={"irr_as_set": "AS-X"}, ixp_presence={"sp": {"v4": {"direct": True}, "v6": {"direct": True}}}))),
    "single_homed": (dict(doc=_doc(single_upstream_v4=64496)), ["single_homed"], dict(doc=_doc())),
    "pdb_prefixos_divergente": (dict(doc=_doc(pdb_registered=True, pdb={"irr_as_set": "AS-X", "info_prefixes4": 10}, global_prefixes_v4_count=25)),
                                ["pdb_prefixos_divergente_ipv4"], dict(doc=_doc(pdb_registered=True, pdb={"irr_as_set": "AS-X", "info_prefixes4": 10}, global_prefixes_v4_count=15))),
    "ptt_proximo_sem_participar": (dict(doc=_doc(), store=FakeStore(coords=(-23.6, -46.7), pix=PIX, ixps=[{"code": "sp", "name": "São Paulo"}])),
                                   ["ptt_proximo_sem_participar"], dict(doc=_doc(ixp_member_codes=["sp"]), store=FakeStore(coords=(-23.6, -46.7), pix=PIX))),
    "agregacao_elevada": (dict(doc=_doc(), store=FakeStore(ra=RA)), ["agregacao_elevada_v4"], dict(doc=_doc(), store=FakeStore(ra={"aggregation_by_asn": [{"asn": ASN, "afi": "v4", "savings_path_pct": 50}]}))),
    "prefixos_filtraveis": (dict(doc=_doc(), store=FakeStore(ra=RA)), ["prefixos_filtraveis"], dict(doc=_doc(), store=FakeStore(ra={"too_specific": {"v4": [{"origin_as": ASN, "prefix": "203.0.113.1/32"}]}}))),
    "prepend_excessivo": (dict(doc=_doc(), store=FakeStore(ra=RA)), ["prepend_excessivo_v4"], dict(doc=_doc(), store=FakeStore(ra={"as_path_stats": {"top_prependers": [{"asn": ASN, "afi": "v4", "avg_excess": 1.0}]}}))),
    "as_loop_detectado": (dict(doc=_doc(), store=FakeStore(ra=RA)), ["as_loop_detectado"], dict(doc=_doc(), store=FakeStore(ra={"as_path_stats": {"hygiene_issues": [{"origin_as": 1, "issue": "as_loop", "prefix": "x"}]}}))),
}


def _alertas_da_regra(regra_id, cenario):
    ctx = Contexto(store=cenario.get("store") or FakeStore(), date_str="2026-10-23", asn=ASN, doc=cenario["doc"])
    mod = next(m for m in registro.MODULOS if m.REGRA.id == regra_id)
    return [a["id"] or regra_id for a in mod.avaliar(ctx)]


@pytest.mark.parametrize("regra_id", sorted(CENARIOS))
def test_cenario_plantado_dispara_e_o_negativo_nao(regra_id):
    dispara, esperado, nao = CENARIOS[regra_id]
    assert _alertas_da_regra(regra_id, dispara) == esperado
    assert _alertas_da_regra(regra_id, nao) == []


def test_todas_as_regras_tem_cenario_e_sao_bem_formadas():
    assert {r.id for r in registro.REGRAS} == set(CENARIOS), "regra sem teste de cenário plantado (ou teste de regra inexistente)"
    ids = [r.id for r in registro.REGRAS]
    assert len(ids) == len(set(ids)) == 23
    for r in registro.REGRAS:
        assert r.severidade in ("critico", "aviso", "info") and r.categoria in ("roteamento", "rpki", "v4v6", "presenca", "geo")
        assert isinstance(r.versao, int) and r.versao >= 1 and r.descricao


def test_formato_do_alerta_e_ordenacao_por_severidade_e_categoria():
    doc = _doc(rir_prefixes_v6=[], global_prefixes_v6=[], roa_list=[{"prefix": "203.0.113.0/24", "maxLength": 24}],
               rpki_validation={"203.0.113.0/24": "invalid"}, single_upstream_v4=1)
    alertas = registro.calcular_alertas(FakeStore(), "2026-10-23", ASN, doc)
    assert list(alertas[0]) == ["id", "category", "severity", "title", "detail", "refs", "desde_versao"]
    assert all(isinstance(a["desde_versao"], int) and a["desde_versao"] >= 1 for a in alertas)
    assert alertas[0]["severity"] == "critico" and alertas[0]["id"] == "rpki_invalido"
    sev = [{"critico": 0, "aviso": 1, "info": 2}[a["severity"]] for a in alertas]
    assert sev == sorted(sev)


def test_regra_que_falha_nao_derruba_as_outras(monkeypatch):
    mod = next(m for m in registro.MODULOS if m.REGRA.id == "sem_ipv6")
    monkeypatch.setattr(registro.MODULOS[1], "avaliar", lambda ctx: 1 / 0)          # prefixo_inalcancavel quebra
    assert "sem_ipv6" in _ids(_doc(rir_prefixes_v6=[], global_prefixes_v6=[]))


def test_rules_version_muda_com_o_conjunto_e_define_comparabilidade(monkeypatch):
    v = registro.rules_version()
    assert v.startswith("r") and len(v) == 9 and v == registro.rules_version()              # estável
    assert registro.regras_publicadas() == dict(sorted(registro.regras_publicadas().items()))
    # subir a versão de uma regra muda o conjunto
    from dataclasses import replace
    alvo = registro.MODULOS[0]
    monkeypatch.setattr(alvo, "REGRA", replace(alvo.REGRA, versao=alvo.REGRA.versao + 1))
    monkeypatch.setattr(registro, "REGRAS", tuple(m.REGRA for m in registro.MODULOS))
    assert registro.rules_version() != v
    assert registro.comparavel(v, v) and not registro.comparavel(v, registro.rules_version())
    assert not registro.comparavel(None, None) and not registro.comparavel(v, None)         # snapshot sem versão nunca é comparável



def test_single_homed_com_relacoes_usa_provedor_inferido_e_visibilidade():
    """Com o fragmento `relacoes`, o alerta só dispara quando o ARC afirmou single-homed (visibilidade suficiente)."""
    rel = {"provedores": [{"asn": 64496, "p": 0.97, "nivel": "confirmado", "afi": ["v4"]}],
           "single_homed": {"v4": True, "v6": None}, "multihomed": {"v4": False, "v6": None},
           "visibilidade": {"v4": {"vps": 5, "ptts": 3, "coletores": True}, "v6": {"vps": 0, "ptts": 0, "coletores": True}}}
    a = _alertas_da_regra("single_homed", dict(doc=_doc(relacoes=rel, single_upstream_v4=64496)))
    assert a == ["single_homed"]
    ctx = Contexto(store=FakeStore(), date_str="2026-10-23", asn=ASN, doc=_doc(relacoes=rel))
    mod = next(m for m in registro.MODULOS if m.REGRA.id == "single_homed")
    achado = mod.avaliar(ctx)[0]
    assert "AS64496" in achado["detail"] and "confirmado" in achado["detail"] and "IPv4" in achado["detail"]
    # indeterminado (pouca visibilidade) ou multihomed: não alerta, mesmo com o legado dizendo single
    for sh in ({"v4": None, "v6": None}, {"v4": False, "v6": False}):
        assert _alertas_da_regra("single_homed", dict(doc=_doc(relacoes={**rel, "single_homed": sh}, single_upstream_v4=64496))) == []
