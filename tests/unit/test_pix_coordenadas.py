# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — `config/pix.yaml`: todo PIX de PTT ativo tem coordenada (MAPA-E1). PIX sem coordenada some do mapa e da distância municipal
(`api/services/geolocalizacao.py` descarta a entrada), e um PTT sem nenhum PIX georreferenciado some por inteiro: em 2026-11-22, cxj, igu
e laj, com Foz do Iguaçu a 114 km "do PTT mais próximo". Coordenada só entra com fonte primária conferível (`coord_fonte` e
`coord_data`); o que ainda não tem fonte fica na lista de pendências abaixo, com o motivo, e o teste falha se a pendência for resolvida
sem sair da lista ou se um PIX novo entrar sem coordenada."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]

# (código do PTT, nome do PIX) → por que ainda não tem coordenada de fonte primária conferível.
# Consulta de 2026-11-24 às facilities do PeeringDB ligadas aos PTTs (api/ixfac, api/fac) e à página de adesão do IX.br.
_SEM_LATLON = "a facility correspondente no PeeringDB não tem latitude/longitude"
_SEM_FACILITY = "nenhuma facility do PeeringDB ligada ao PTT corresponde a este PIX, e a página do IX.br não traz coordenada"
_DIVERGE = "a facility do PeeringDB do mesmo operador tem outro endereço; sem fonte que confirme o local do PIX"
PENDENTES: dict[tuple[str, str], str] = {
    ("ba", "[PIX UFBA]"): _SEM_FACILITY,
    ("bel", "[PIX PRONTONET]"): _DIVERGE + " (PeeringDB: Rod. Mário Covas, 9, Belém; IX.br: Rua Belo Horizonte, 8, Ananindeua)",
    ("cas", "[PIX ASCENTY-VIN]"): _SEM_LATLON + " (Ascenty VIN01, fac 7589)",
    ("cau", "[PIX BR.Digital]"): _DIVERGE + " (PeeringDB: Av. Bom Pastor, 246; IX.br: Rua Nazaré da Mata, 246)",
    ("ce", "[PIX RNP]"): _SEM_FACILITY,
    ("fec", "[PIX CORE3]"): _SEM_LATLON + " (PIX-Core3, fac 15494)",
    ("fec", "[PIX BR.Digital]"): _SEM_LATLON + " (BR.Digital Feira de Santana, fac 15496)",
    ("gyn", "[PIX SAMM - Serra Dourada]"): _SEM_LATLON + " (PIX-Samm Serra Dourada, fac 16753, e com outro endereço)",
    ("igu", "[PIX BR.Digital]"): _SEM_LATLON + " (BR.Digital Foz do Iguaçu, fac 15218)",
    ("mao", "[PIX RNP]"): _SEM_FACILITY,
    ("nat", "[PIX / RNP]"): _SEM_FACILITY,
    ("rj", "[PIX EQUINIX-RJ3]"): _SEM_LATLON + " (Equinix RJ3, fac 15048)",
    ("ro", "[PIX SETIC]"): _SEM_LATLON + " (PIX-Setic, fac 15422)",
    ("ro", "[PIX NBS TELECOM]"): _SEM_LATLON + " (PIX-NBS Telecom, fac 15424)",
    ("sp", "[PIX BR.Digital]"): _DIVERGE + " (PeeringDB: Rua Flórida, 1738; IX.br: Rua Cenno Sbrighi, 27)",
    ("sp", "[PIX ASCENTY VIN]"): _SEM_LATLON + " (Ascenty VIN01, fac 7589)",
}


def _pix() -> dict:
    return yaml.safe_load((RAIZ / "config" / "pix.yaml").read_text(encoding="utf-8"))["pix"]


def _ativos() -> set[str]:
    return {i["code"] for i in yaml.safe_load((RAIZ / "config" / "ixps.yaml").read_text(encoding="utf-8"))["ixps"]}


def test_todo_pix_de_ptt_ativo_tem_coordenada_ou_pendencia_explicada():
    pix = _pix()
    sem = {(code, p["name"]) for code in _ativos() for p in pix.get(code) or [] if p.get("lat") is None or p.get("lon") is None}
    assert sem - set(PENDENTES) == set(), f"PIX sem coordenada e sem pendência registrada: {sorted(sem - set(PENDENTES))}"
    assert set(PENDENTES) - sem == set(), f"pendência resolvida que continua na lista: {sorted(set(PENDENTES) - sem)}"
    assert all(m.strip() for m in PENDENTES.values())


def test_todo_ptt_ativo_tem_ao_menos_um_pix_no_mapa():
    pix = _pix()
    sem_nenhum = sorted(c for c in _ativos() if not any(p.get("lat") is not None for p in pix.get(c) or []))
    assert sem_nenhum == [], f"PTT ativo fora do mapa: {sem_nenhum}"


def test_coordenada_nova_cita_fonte_e_data_e_fica_no_brasil():
    for code, lista in _pix().items():
        for p in lista or []:
            if p.get("lat") is None:
                continue
            assert -34.0 < p["lat"] < 5.5 and -74.5 < p["lon"] < -28.5, (code, p["name"])
            if "coord_fonte" in p or "coord_data" in p:
                assert str(p.get("coord_fonte", "")).startswith("https://") and len(str(p.get("coord_data", ""))) == 10, (code, p["name"])


def test_cep_do_pix_bate_com_a_uf_do_ptt():
    """O PIX de Lajeado/RS tinha CEP 37147040 (faixa de MG)."""
    faixa = {"RS": ("90", "99"), "PR": ("80", "87"), "SC": ("88", "89")}
    uf = {i["code"]: i["uf"] for i in yaml.safe_load((RAIZ / "config" / "ixps.yaml").read_text(encoding="utf-8"))["ixps"]}
    for code, lista in _pix().items():
        if uf.get(code) not in faixa:
            continue
        de, ate = faixa[uf[code]]
        for p in lista or []:
            cep = str(p.get("cep") or "")
            if cep:
                assert de <= cep[:2] <= ate, (code, p["name"], cep)
