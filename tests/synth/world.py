# SPDX-License-Identifier: AGPL-3.0-or-later
"""Arandurápolis — o "mini-Brasil" fictício dos testes de produto (T2).

Regras: dados SIMPLES e determinísticos; **nenhum dado real**.
- ASNs reservados: 64496–64511 e 65536–65551 (documentação, RFC 5398), 4200000000+ (privados, RFC 6996);
- prefixos IPv4 do bloco de testes 198.18.0.0/15 (RFC 2544) e 100.64.0.0/10; IPv6 em 2001:db8::/32 (RFC 3849);
- CNPJs fictícios com dígito verificador válido; nomes inventados; coordenadas dos municípios fictícios são
  deslocamentos de centros de capitais, sem relação com endereços reais.

O mundo tem DOIS instantes: T0 (semana anterior) e T1, com diferenças plantadas (ver `CENARIOS`).
"""
from __future__ import annotations

import ipaddress
import random
from dataclasses import dataclass, field

T0 = "2026-09-13"
T1 = "2026-09-20"

# (código, nome, UF) — não coincidem com os códigos reais do config/ixps.yaml
PTTS = [("za", "Arandurápolis", "SP"), ("zb", "Tupãnópolis", "RJ"), ("zc", "Guaraniópolis", "PR")]

MUNICIPIOS = [  # ibge fictício (7 dígitos começando em 99), nome, UF, lat, lon
    ("9900001", "Arandurápolis", "SP", -23.60, -46.70), ("9900002", "Tupãnópolis", "RJ", -22.95, -43.25),
    ("9900003", "Guaraniópolis", "PR", -25.45, -49.30), ("9900004", "Itapuãzinho", "SP", -22.90, -47.10),
    ("9900005", "Curumim do Sul", "RS", -30.05, -51.20), ("9900006", "Ybyrapé", "MG", -19.90, -43.95),
    ("9900007", "Mbaracayú Novo", "PR", -24.95, -53.45), ("9900008", "Tabajara do Norte", "AM", -3.15, -60.00),
    ("9900009", "Potiguara", "RN", -5.80, -35.20), ("9900010", "Caeté Velho", "BA", -12.95, -38.50),
    ("9900011", "Jaguarão de Cima", "RS", -32.55, -53.35), ("9900012", "Pindorama Alta", "GO", -16.70, -49.25),
]

CENARIOS = {
    1: "AS multihomed com MOAS e ROA inválido (64496/64497 e o prefixo 198.18.0.0/24)",
    2: "Operadora com outorga SCM sem SICI mas com usuários APNIC (64510)",
    3: "CNPJ com dois ASNs: soma de acessos não duplica (64500 e 64501 — acessos_compartilhados)",
    4: "Dois grupos econômicos com sócio comum: mesmo_grupo × relacionadas_parcial",
    5: "PTT cuja coleta v6 falhou: status parcial (zc)",
    6: "Prefixo cuja origem muda entre T0 e T1 (198.18.24.0/21: 64502 → 64503)",
    7: "Contatos PeeringDB e telefone de outorga não aparecem em rotas públicas",
    8: "Município sem PTT a menos de 100 km: lacuna (Tabajara do Norte)",
    9: "Membro estrangeiro que só anuncia IPv6 no za: originadores do PTT são a união IPv6 ∪ IPv4, maior que o maior dos dois",
    10: "Vínculo ASN ↔ CNPJ (D5): AS registrado em filial de operadora sem ASN no próprio CNPJ (4200000201 na raiz de SemASN6), operadora "
        "sem ASN ligada pela marca curada DELTA (SemASN4) e operadora com AS estrangeiro (SemASN5, EPSILON → 4200000100)",
}

#: Cenário 10: o AS registrado no Registro.br com o CNPJ de uma filial (0002) da operadora "Provedor Sem ASN 6", que declara ao SICI pela
#: matriz sem ASN no próprio CNPJ (como a Hughes: SICI na matriz, AS28613 na filial)
AS_FILIAL = 4200000201
SEM_ASN_FILIAL = 205                  # `make_cnpj(205)`: a matriz (6ª operadora sem ASN de `market.operators`)


def cnpj_dv(base12: str) -> str:
    def dig(s, w):
        t = sum(int(c) * k for c, k in zip(s, w))
        r = t % 11
        return "0" if r < 2 else str(11 - r)

    d1 = dig(base12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = dig(base12 + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return d1 + d2


def make_cnpj(n: int, filial: int = 1) -> str:
    base = f"{90000000 + n:08d}{filial:04d}"
    return base + cnpj_dv(base)


@dataclass
class AS:
    asn: int
    name: str
    cc: str                       # BR | US | DE | AR
    role: str                     # access | transit | foreign
    uf: str = ""
    municipio_ibge: str = ""
    cnpj: str = ""
    v4: list[str] = field(default_factory=list)          # anunciados
    v4_idle: list[str] = field(default_factory=list)     # alocados mas NÃO anunciados (cobertura < 100%)
    v6: list[str] = field(default_factory=list)
    users: int = 0
    v6_users: int = 0

    @property
    def is_br(self) -> bool:
        return self.cc == "BR"


class _Pool:
    def __init__(self, cidr: str):
        self.net = ipaddress.ip_network(cidr)
        self.cur = int(self.net.network_address)

    def take(self, prefixlen: int) -> str:
        size = 1 << ((32 if self.net.version == 4 else 128) - prefixlen)
        self.cur = (self.cur + size - 1) // size * size
        n = ipaddress.ip_network((self.cur, prefixlen))
        self.cur += size
        assert n.subnet_of(self.net)
        return str(n)


@dataclass
class World:
    instant: str
    ases: dict[int, AS]
    members: dict[str, list[int]]                        # PTT → ASNs com sessão no RS
    routes: dict[str, list[tuple[str, list[int]]]]       # PTT → [(prefixo, as_path)] (v4 e v6)
    transit_of: dict[int, int]                           # acesso → trânsito
    rpki: list[dict]                                     # VRPs
    aspa: list[dict]
    failed: dict[str, list[str]]                         # PTT → AFIs com coleta falha
    full_table: dict[str, int]                           # prefixo → origem (visão global)


def build_world(instant: str = T1, seed: int = 1, extra_asns: int = 0) -> World:
    """`extra_asns` > 0 acrescenta ASNs de acesso BR genéricos (escala para E2E/CI noturno: listas > 100 linhas);
    com 0 o mundo é idêntico ao dos arquivos de ouro."""
    rng = random.Random(seed)
    v4 = _Pool("198.18.0.0/15")
    v6 = _Pool("2001:db8::/32")
    ases: dict[int, AS] = {}
    mun = [m[0] for m in MUNICIPIOS]

    access_asns = list(range(64496, 64512)) + list(range(65536, 65552))
    transit_asns = list(range(4200000000, 4200000004))
    foreign_asns = list(range(4200000100, 4200000124))

    def v4_blocks(lens: list[int]) -> list[str]:
        return [v4.take(n) for n in lens]

    sizes = [[24], [24, 24], [23], [24, 23], [22], [24, 24, 24], [21, 24], [22, 23]]
    for j, asn in enumerate(access_asns):
        lens = sizes[j % len(sizes)]
        a = AS(asn, f"Provedor {j + 1:02d} Telecom Ltda", "BR", "access", uf=MUNICIPIOS[j % len(MUNICIPIOS)][2],
               municipio_ibge=mun[j % len(mun)], cnpj=make_cnpj(j + 1),
               v4=v4_blocks(lens), users=(j + 1) * 3000 + rng.randrange(0, 500))
        a.v4_idle = [v4.take(24)] if j % 3 == 0 else []                   # parte do alocado não é anunciada
        if j % 5 != 4:                                                    # 80% têm IPv6
            a.v6 = [v6.take(48) for _ in range(1 + j % 2)]
            a.v6_users = int(a.users * (0.2 + (j % 7) / 10))
        ases[asn] = a
    for k, asn in enumerate(transit_asns):
        ases[asn] = AS(asn, f"Trânsito Nacional {k + 1} S.A.", "BR", "transit", uf=PTTS[k % 3][2],
                       municipio_ibge=mun[k % 3], cnpj=make_cnpj(100 + k), v4=v4_blocks([22, 23]), v6=[v6.take(48)],
                       users=0)
    fpool = _Pool("100.64.0.0/10")
    f6 = _Pool("2001:db8:8000::/33")
    for k, asn in enumerate(foreign_asns):
        ases[asn] = AS(asn, f"Foreign Net {k + 1} Inc", ["US", "DE", "AR"][k % 3], "foreign",
                       v4=[fpool.take(24) for _ in range(1 + k % 3)], v6=[f6.take(48)] if k % 2 == 0 else [])

    extra = list(range(4200001000, 4200001000 + extra_asns))
    if extra:
        xr = random.Random(seed + 7919)                           # fluxo próprio: não perturba o do mundo-base
        xpool = _Pool("100.112.0.0/12")                           # 4096 /24 (o 198.18/15 só tem 512)
        for k, asn in enumerate(extra):
            ases[asn] = AS(asn, f"Escala {k + 1:04d} Telecom Ltda", "BR", "access",
                           uf=MUNICIPIOS[k % len(MUNICIPIOS)][2], municipio_ibge=mun[k % len(mun)],
                           cnpj=make_cnpj(1000 + k), v4=[xpool.take(24)], users=500 + xr.randrange(0, 200))
            if k % 3:
                ases[asn].v6 = [v6.take(48)]

    # divergência APNIC × Anatel plantada (o SICI correspondente sai de market.sici):
    ases[64504].users, ases[64504].v6_users = 50000, 10000      # 50 mil usuários observados para ~1 mil acessos → "apnic_alto"
    ases[64505].users, ases[64505].v6_users = 500, 100          # 500 usuários para 5 mil acessos → "apnic_baixo"

    # 3) um CNPJ com dois ASNs: 64501 usa o CNPJ de 64500 (acessos_compartilhados)
    ases[64501].cnpj = ases[64500].cnpj

    # 10) AS registrado em filial: a operadora (matriz) declara ao SICI e tem outorga; o AS da filial só aparece no Registro.br (como o
    # AS28613 da Hughes). Fora dos PTTs e com blocos fora dos pools (o fim do 198.18.0.0/15 e um /48 antes do pool estrangeiro).
    sede = MUNICIPIOS[(SEM_ASN_FILIAL - 200 + 3) % len(MUNICIPIOS)]          # a mesma sede da operadora em `market.operators`
    ases[AS_FILIAL] = AS(AS_FILIAL, "Provedor Sem ASN 6 Ltda (filial)", "BR", "access", uf=sede[2], municipio_ibge=sede[0],
                         cnpj=make_cnpj(SEM_ASN_FILIAL, filial=2), v4=["198.19.255.0/24"], v6=["2001:db8:7fff::/48"], users=12000, v6_users=6000)

    # Cenários plantados que mexem no mapa de prefixos
    # 6) origem do 198.18.8.0/24 muda de 64502 para 64503 entre T0 e T1
    shared = "198.18.0.0/24"                                              # 1) MOAS: 64496 e 64497 anunciam o mesmo prefixo
    ases[64497].v4 = ases[64497].v4 + [shared] if shared not in ases[64497].v4 else ases[64497].v4

    transit_of = {asn: transit_asns[j % len(transit_asns)] for j, asn in enumerate(access_asns + extra)}

    # Participação nos PTTs (determinística)
    members = {
        "za": access_asns[:24] + transit_asns[:2] + foreign_asns[:6],
        "zb": access_asns[8:24] + transit_asns[1:3] + foreign_asns[4:8],
        "zc": access_asns[16:24] + transit_asns[3:4] + foreign_asns[6:8],
    }
    if instant == T1:
        members["zb"] = list(dict.fromkeys(members["zb"] + [access_asns[2]]))     # entra um novo membro no PTT zb
    for k, asn in enumerate(extra):
        members[("za", "zb", "zc")[k % 3]].append(asn)

    # Rotas vistas pelo route server de cada PTT
    # (6) prefixo que muda de origem:
    moving = ases[64502].v4[0]
    routes: dict[str, list[tuple[str, list[int]]]] = {}
    for ptt, mem in members.items():
        rs: list[tuple[str, list[int]]] = []
        for asn in mem:
            a = ases[asn]
            for p in a.v4 + a.v6:
                origin = asn
                if instant == T1 and p == moving and asn == 64502:
                    continue                                              # 64502 deixa de originar
                if ptt == "za" and asn == foreign_asns[0] and ":" not in p:
                    continue                                              # 9) só IPv6 no za: originadores IPv6 ∪ IPv4 > max(IPv6, IPv4)
                rs.append((p, [origin]))
            if a.role == "transit":                                       # trânsitos anunciam clientes (caminho [trânsito, cliente])
                clientes = [c for c, t in transit_of.items() if t == asn][:3]
                for c in clientes:
                    for p in ases[c].v4[:1] + ases[c].v6[:1]:
                        rs.append((p, [asn, c]))
        if instant == T1 and 64503 in mem and ptt == "za":
            rs.append((moving, [64503]))                                  # 6) nova origem em T1
        routes[ptt] = sorted(set((p, tuple(path)) for p, path in rs), key=lambda x: (":" in x[0], x[0], x[1]))
        routes[ptt] = [(p, list(path)) for p, path in routes[ptt]]

    # Tabela global: cada prefixo anunciado → origem (quem o originou por último em qualquer PTT; MOAS fica com a menor ASN)
    full: dict[str, int] = {}
    for a in ases.values():
        for p in a.v4 + a.v6:
            full.setdefault(p, a.asn)
    if instant == T1:
        full[moving] = 64503
    # ROA/VRP: 70% dos prefixos BR; o MOAS (1) tem ROA só para 64496 → anúncio de 64497 é inválido
    rpki: list[dict] = []
    for a in ases.values():
        if not a.is_br:
            continue
        for i, p in enumerate(a.v4 + a.v6):
            if (a.asn + i) % 10 < 7:
                n = ipaddress.ip_network(p)
                rpki.append({"asn": a.asn, "prefix": p, "maxLength": n.prefixlen, "ta": "lacnic"})
    rpki = [r for r in rpki if not (r["prefix"] == shared and r["asn"] == 64497)]
    if not any(r["prefix"] == shared and r["asn"] == 64496 for r in rpki):
        rpki.append({"asn": 64496, "prefix": shared, "maxLength": 24, "ta": "lacnic"})
    aspa = [{"customer": 64496, "providers": [transit_of[64496]], "tal": "lacnic"}]
    failed = {"zc": ["v6"]}                                               # 5) coleta v6 do zc falhou
    return World(instant, ases, members, routes, transit_of, sorted(rpki, key=lambda r: (r["asn"], r["prefix"])), aspa, failed, full)
