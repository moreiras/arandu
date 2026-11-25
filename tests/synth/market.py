# SPDX-License-Identifier: AGPL-3.0-or-later
"""Camada de mercado/regulatória do dataset sintético: outorgas, SICI, sócios (cenários 2, 3, 4, 7)."""
from __future__ import annotations

import ipaddress

from tests.synth.world import AS, MUNICIPIOS, T0, World, make_cnpj

MUN = {m[0]: m for m in MUNICIPIOS}
MES_REF = {T0: "2026-07", "2026-09-20": "2026-08"}      # o SICI tem defasagem de um mês em relação ao snapshot


def _org(asn: AS) -> dict:
    m = MUN[asn.municipio_ibge]
    return {"cnpj": asn.cnpj, "razao_social": asn.name, "nome_fantasia": asn.name.split(" Telecom")[0],
            "municipio": m[1], "uf": m[2], "codigo_ibge": m[0], "lat": m[3], "lon": m[4]}


def operators(world: World) -> list[dict]:
    """Operadoras (CNPJ único): as dos ASNs BR (CNPJ compartilhado conta uma vez) + 8 sem ASN. O AS registrado em filial (cenário 10)
    não gera operadora: a outorga e o SICI são da matriz."""
    seen: dict[str, dict] = {}
    for a in sorted(world.ases.values(), key=lambda x: x.asn):
        if a.is_br and a.cnpj[8:12] != "0001":
            continue
        if a.is_br and a.cnpj not in seen:
            o = _org(a)
            o["asns"] = [a.asn]
            seen[a.cnpj] = o
        elif a.is_br:
            seen[a.cnpj]["asns"].append(a.asn)
    for k in range(8):
        m = MUNICIPIOS[(k + 3) % len(MUNICIPIOS)]
        c = make_cnpj(200 + k)
        seen[c] = {"cnpj": c, "razao_social": f"Provedor Sem ASN {k + 1} Ltda", "nome_fantasia": f"SemASN{k + 1}",
                   "municipio": m[1], "uf": m[2], "codigo_ibge": m[0], "lat": m[3], "lon": m[4], "asns": []}
    return list(seen.values())


def outorga_record(op: dict, i: int, servico: str) -> dict:
    return {"cnpj": op["cnpj"], "razao_social": op["razao_social"], "nome_fantasia": op["nome_fantasia"],
            "data_outorga": f"{10 + i % 18:02d}/0{1 + i % 9}/20{15 + i % 8}", "num_servico": servico,
            "cep": f"{99000000 + i:08d}", "logradouro": f"Rua do Exemplo {i + 1}", "numero": str(100 + i), "complemento": "",
            "bairro": "Centro", "municipio": op["municipio"], "uf": op["uf"], "codigo_ibge": op["codigo_ibge"],
            "telefone": f"(11) 9{i:04d}-0000", "email": f"contato{i}@example.org", "situacao": ""}


def outorgas(world: World) -> dict[str, list[dict]]:
    ops = operators(world)
    out = {"scm": [], "smp": [], "stfc": [], "seac": []}
    for i, op in enumerate(ops):
        out["scm"].append(outorga_record(op, i, "045 - Serviço de Comunicação Multimídia"))
    for i, op in enumerate(ops[-6:]):
        out["seac"].append(outorga_record(op, i, "750 - Serviço de Acesso Condicionado"))
    for i, op in enumerate(ops[:3]):
        out["stfc"].append(outorga_record(op, i, "171 - SERVICO TELEFONICO FIXO COMUTADO"))
    for i, op in enumerate(ops[34:37]):
        out["smp"].append(outorga_record(op, i, "010 - SERVIÇO MOVEL PESSOAL"))
    # credenciada de rede virtual sem outorga SMP própria (com ASN e SCM, sem SICI móvel): o registro que
    # `sources.anatel_smp.collect._apply_rede_virtual` acrescenta; não é outorga SMP (OPERADORA-E8/E9, OPERADORAS-E2)
    cred, host = ops[33], ops[34]
    out["smp"].append({**outorga_record(cred, 3, ""), "data_outorga": "", "num_servico": "",
                       "situacao": "Credenciada de Rede Virtual (sem outorga SMP própria)",
                       "rede_virtual": {"papel": "credenciada", "prestadora_origem_cnpj": host["cnpj"],
                                        "prestadora_origem_nome": host["razao_social"]}})
    return out


def with_geo(recs: list[dict]) -> list[dict]:
    out = []
    for r in recs:
        m = MUN[r["codigo_ibge"]]
        out.append({**r, "lat": m[3], "lon": m[4], "geo_confidence": "city_centroid", "geo_source": "nominatim"})
    return out


def _agg(op: dict, acessos: int, instant_factor: float) -> dict:
    ac = int(acessos * instant_factor)
    pf = int(ac * 0.9)
    m = MUN[op["codigo_ibge"]]
    return {
        "empresa": op["razao_social"], "grupo": "OUTROS", "porte": "Pequeno Porte", "uf": op["uf"],
        "acessos": ac, "pf": pf, "pj": ac - pf, "acessos_internet": ac, "capacidade_mbps": round(ac * 120.0, 2),
        "capacidade_internet_mbps": round(ac * 120.0, 2), "por_tecnologia": {"FTTH": ac}, "por_meio": {"Fibra": ac},
        "por_faixa": {"> 34Mbps": ac}, "por_produto": {"INTERNET": ac},
        "por_municipio": {m[0]: {"uf": m[2], "nome": m[1], "acessos": ac, "pf": pf, "pj": ac - pf,
                                 "capacidade_mbps": round(ac * 120.0, 2),
                                 "fibra": ac * 8 // 10}},
        "velocidade_mediana_mbps": 120.0, "municipios": 1, "velocidade_media_mbps": 120.0,
        "tecnologia_predominante": "FTTH", "meio_predominante": "Fibra",
    }


def sici(world: World) -> dict:
    """SICI fixo. Cenário 2: o CNPJ do AS 64510 NÃO declara. Divergência plantada: 64504 (alto) e 64505 (baixo)."""
    f = 1.0 if world.instant != T0 else 0.96
    cn_asn = {a.cnpj: a for a in world.ases.values() if a.is_br}
    cnpjs = {}
    for op in operators(world):
        a = cn_asn.get(op["cnpj"])
        if a and a.asn == 64510:
            continue                                                        # cenário 2: outorga SCM sem SICI
        if a and a.users:
            ac = max(int(a.users / 3.5), 150)
            if a.asn == 64504:
                ac = 1000                                                   # 50 000 usuários / 1 000 acessos → apnic_alto
            if a.asn == 64505:
                ac = 5000                                                   # 500 usuários / 5 000 acessos → apnic_baixo
        else:
            ac = 600
        cnpjs[op["cnpj"]] = _agg(op, ac, f)
    mes = MES_REF[world.instant]
    prev = "2026-06" if mes == "2026-07" else "2026-07"
    serie = {c: [[prev, int(v["acessos"] * 0.97), int(v["pf"] * 0.97), int(v["pj"] * 0.97)], [mes, v["acessos"], v["pf"], v["pj"]]]
             for c, v in cnpjs.items()}
    return {"generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "mes_referencia": mes,
            "meses_disponiveis": [prev, mes], "total_acessos": sum(v["acessos"] for v in cnpjs.values()),
            "total_cnpjs": len(cnpjs), "cnpjs": cnpjs, "distrib_velocidade": {}, "serie_por_cnpj": serie,
            "serie_total": [{"mes": prev, "acessos": 0, "cnpjs": len(cnpjs)}, {"mes": mes, "acessos": 0, "cnpjs": len(cnpjs)}]}


def sici_movel(world: World) -> dict:
    ops = operators(world)[34:37]
    cnpjs = {}
    for i, op in enumerate(ops):
        ac = 5000 * (i + 1)
        m = MUN[op["codigo_ibge"]]
        cnpjs[op["cnpj"]] = {
            "empresa": op["razao_social"], "grupo": "OUTROS", "porte": "Pequeno Porte", "uf": op["uf"], "acessos": ac,
            "pf": ac, "pj": 0, "acessos_m2m": 0, "acessos_outros": 0, "por_geracao": {"4G": ac}, "por_modalidade": {"Pré-pago": ac},
            "por_produto": {"VOZ+DADOS": ac},
            "por_municipio": {m[0]: {"uf": m[2], "nome": m[1], "acessos": ac, "pf": ac, "pj": 0}}, "municipios": 1,
            "geracao_predominante": "4G"}
    mes = MES_REF[world.instant]
    return {"generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "mes_referencia": mes,
            "meses_disponiveis": [mes], "total_acessos": sum(v["acessos"] for v in cnpjs.values()), "total_cnpjs": len(cnpjs),
            "cnpjs": cnpjs, "distrib_modalidade": {}, "serie_por_cnpj": {c: [[mes, v["acessos"], v["pf"], v["pj"]]] for c, v in cnpjs.items()},
            "serie_total": [{"mes": mes, "acessos": sum(v["acessos"] for v in cnpjs.values()), "cnpjs": len(cnpjs)}]}


def _socio(ident, nome, doc, qual="49"):
    return {"identificador_socio": ident, "nome_socio": nome, "cnpj_cpf_socio": doc, "qualificacao_socio": qual,
            "data_entrada_sociedade": "20200101", "representante_legal": "***000000**", "nome_representante": "", "faixa_etaria": "4"}


def receita_socios(world: World) -> dict:
    """Quadro societário sintético. Cenário 4: quadro idêntico (64506/64507), holding comum externa (64508/64509),
    controle exclusivo (64511 → 65536). Cenário 11: diretor e presidente em comum sem participação (não ligam)."""
    by_basico: dict[str, list[dict]] = {}
    by_asn = {a.asn: a for a in world.ases.values() if a.is_br}

    def basico(asn: int) -> str:
        return by_asn[asn].cnpj[:8]

    for k, op in enumerate(operators(world)):
        by_basico[op["cnpj"][:8]] = [_socio("2", f"Socio Unico {k + 1:03d}", f"***{k:06d}**")]
    ident = [_socio("2", "Ana Exemplo da Silva", "***111111**"), _socio("2", "Bruno Exemplo Souza", "***222222**")]
    by_basico[basico(64506)] = [dict(s) for s in ident]
    by_basico[basico(64507)] = [dict(s) for s in ident]
    holding = "55500001"                                                        # PJ fora da base
    by_basico[basico(64508)] = [_socio("1", "HOLDING EXEMPLO PARTICIPACOES SA", holding), _socio("2", "Carla Exemplo Lima", "***333333**")]
    by_basico[basico(64509)] = [_socio("1", "HOLDING EXEMPLO PARTICIPACOES SA", holding), _socio("2", "Diego Exemplo Rocha", "***444444**")]
    by_basico[basico(65536)] = [_socio("1", by_asn[64511].name, basico(64511))]     # 64511 controla 65536 com exclusividade
    # cenário 11 (D5): as duas últimas operadoras sem ASN têm o mesmo diretor (10) e o mesmo presidente (16), sem participação: não formam grupo
    for op in operators(world)[-2:]:
        by_basico[op["cnpj"][:8]] += [_socio("2", "Diretor Exemplo Comum", "***555555**", "10"), _socio("2", "Presidente Exemplo Comum", "***666666**", "16")]
    return {"snapshot_date": world.instant, "generated_at": "2026-01-01T00:00:00+00:00", "dump_reference": "2026-09",
            "parts_processed": 1, "target_cnpj_basicos": len(by_basico), "matched_cnpj_basicos": len(by_basico),
            "by_cnpj_basico": by_basico}


def ibge(world: World) -> tuple[dict, dict]:
    """IBGE sintético: os municípios de Arandurápolis com população e domicílios determinísticos (domicílios sempre maiores que os acessos plantados
    do SICI em alguns municípios, e menores em outros) e a taxa de internet por UF. Um município (o último) fica sem domicílios, como a SIDRA ("...")."""
    muns, ufs = {}, {}
    for i, (ibge_, nome, uf, *_r) in enumerate(sorted(MUNICIPIOS)):
        pop = 20000 * (i + 1)
        m = {"nome": nome, "uf": uf, "populacao": pop, "populacao_estimada": pop + pop // 20, "area_km2": 100.0 + i}
        if i != len(MUNICIPIOS) - 1:
            m["domicilios"] = pop // 3
            m["moradores"] = pop - 100
        muns[ibge_] = m
        ufs[uf] = {"domicilios_mil": 500.0, "com_internet_mil": 450.0, "cv_domicilios_pct": 0.8, "taxa": 0.9,
                   "domicilios_mil_por_ano": {"2022": 460.0, "2025": 500.0}}
    return muns, ufs


def erbs(world: World, d: str) -> dict:
    """Estações do SMP licenciadas: 3 operadoras do SICI móvel nos municípios de Arandurápolis. A 1ª tem 2G/3G/4G, a 2ª 4G/5G (SA e NSA), a 3ª só 4G e vem **sem CNPJ**
    no arquivo (o produto o recupera pela razão social das outorgas). O último município fica sem estação e um código IBGE desconhecido testa o casamento."""
    ops = operators(world)[34:37]
    gers = [["2G", "3G", "4G"], ["4G", "5G"], ["4G"]]
    tecs = [["GSM", "LTE", "WCDMA"], ["LTE", "NR"], ["LTE"]]
    est = []
    muns = sorted(MUNICIPIOS)
    for i, (ibge_, _nome, uf, lat, lon, *_r) in enumerate(muns[:-1]):
        for j, op in enumerate(ops):
            for k in range((i + j) % 3 + (1 if j == 0 else 0)):
                est.append({"fistel": f"5000000{j}{i:03d}", "estacao": f"{i}{j}{k}", "marca": op["razao_social"].split()[0].upper(), "entidade": op["razao_social"],
                            "cnpj": None if j == 2 else op["cnpj"], "ibge": ibge_, "uf": uf, "lat": lat + 0.01 * k, "lon": lon, "posicao_variavel": False, "geracoes": gers[j],
                            "tecnologias": sorted(tecs[j]), "tipo_5g": ["SA"] if j == 1 and k == 0 else (["NSA"] if j == 1 else []), "faixas": ["1800"], "setores": 3, "combinacoes": 3,
                            "infra": "Rooftop", "primeira_licenca": 2015, "linhas": 9})
    est.append({"fistel": "50000009999", "estacao": "1", "marca": ops[0]["razao_social"].split()[0].upper(), "entidade": ops[0]["razao_social"], "cnpj": ops[0]["cnpj"], "ibge": "9999999",
                "uf": "ZZ", "lat": -10.0, "lon": -50.0, "posicao_variavel": False, "geracoes": ["4G"], "tecnologias": ["LTE"], "tipo_5g": [], "faixas": ["700"], "setores": 1,
                "combinacoes": 1, "infra": None, "primeira_licenca": 2020, "linhas": 3})
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Sun, 01 Nov 2026 10:52:35 GMT", "sha256": "0" * 64,
            "resumo": {"linhas": 9 * len(est), "estacoes": len(est)}, "estacoes": est}


def fust(world: World, d: str) -> dict:
    """Compromissos do FUST sintéticos: escolas e UBS nos municípios de Arandurápolis, em 3 situações e 2 malhas do IBGE, mais um compromisso em município fora do cadastro."""
    muns = sorted(MUNICIPIOS)
    itens = []
    for i, (ibge_, nome, uf, *_r) in enumerate(muns[:-1]):
        for k in range(i % 3 + 1):
            ubs = k == 2
            itens.append({"id": f"{i}{k}", "origem": "Edital nº 1/2026/SINTETICO" if k == 0 else "Projetos BNDES", "tipo": "Infra. Rede - UBSs" if ubs else "Infra. Rede - Escolas",
                          "programa": "2.6 - Conectividade significativa para Unidades Básicas de Saúde" if ubs else "1.1 - Conectividade para Escolas Públicas", "nivel": "Município",
                          "base_ibge": "IBGE_2010" if k == 1 else "IBGE_2022", "ibge": ibge_, "uf": uf, "municipio": nome, "status": ("Atendido", "A vencer", "Em apuração")[(i + k) % 3],
                          "prazo": "2027-06-01", "investimento": None if (i, k) == (0, 0) else 1000.0 * (k + 1)})
    itens.append({"id": "x", "origem": "Projetos BNDES", "tipo": "Infra. Rede", "programa": "2.2 - Rede de transporte de alta capacidade de fibra óptica", "nivel": "Localidade",
                  "base_ibge": "IBGE_2022", "ibge": "9999999", "uf": "ZZ", "municipio": "FORA", "status": "A vencer", "prazo": None, "investimento": 5000.0})
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Mon, 02 Nov 2026 10:30:15 GMT", "sha256": "0" * 64,
            "resumo": {"compromissos": len(itens)}, "compromissos": itens}


def multas(world: World, d: str) -> dict:
    """Multas da Anatel sintéticas: as 3 operadoras do SICI móvel com multas em SMP (a 1ª também em SCM) e um provedor só com SCM; os CNPJs são os das operadoras do mundo sintético."""
    ops = operators(world)[34:37]
    def emp(op, grupo, multas_, saldo, anos, sit):
        cnpj = op["cnpj"]
        return {"raiz": cnpj[:8], "grupo": grupo, "entidade": op["razao_social"], "cnpjs": [cnpj], "uf": "SP", "multas": multas_, "original": saldo * 2, "pago": saldo / 2, "saldo": saldo,
                "situacoes": sit, "anos": anos}
    empresas = [emp(ops[0], "SMP", 6, 9000.0, {"2012": 2, "2020": 4}, {"Quitado": 4, "Devedor": 2}), emp(ops[0], "SCM", 2, 1500.0, {"2021": 2}, {"Devedor": 2}),
                emp(ops[1], "SMP", 3, 0.0, {"2015": 3}, {"Quitado": 3}), emp(ops[2], "SMP", 1, 400.0, {"2019": 1}, {"Parcial": 1}),
                {"raiz": "99999999", "grupo": "SCM", "entidade": "SO MULTA TELECOM S.A.", "cnpjs": ["99999999000191"], "uf": "SP", "multas": 1, "original": 200.0, "pago": 0.0, "saldo": 100.0,
                 "situacoes": {"Devedor": 1}, "anos": {"2018": 1}}]      # CNPJ que só aparece nas multas: sem ASN, outorga nem SICI
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Mon, 02 Nov 2026 10:30:08 GMT", "sha256": "0" * 64,
            "resumo": {"linhas": 40, "pessoa_fisica": 10, "fora_do_escopo": 20, "sem_servico": 5, "situacao_desconhecida": 0, "empresas": len(empresas), "multas": sum(e["multas"] for e in empresas)},
            "empresas": empresas}


def pdff(world: World, d: str) -> dict:
    """Quadro de faixas sintético: 700 MHz, 2,4 GHz (Wi-Fi), 3,3-3,4 e 3,4-3,5 GHz e uma faixa de rádio fora do interesse."""
    def f(ini, fim, dest, atr):
        return {"ini_mhz": ini, "fim_mhz": fim, "destinacao": [{"servico": s, "carater": c} for s, c in dest], "atribuicao": [{"servico": s, "carater": c} for s, c in atr]}
    faixas = [f(88.0, 108.0, [("RADIODIFUSÃO SONORA", "Primário")], [("RADIODIFUSÃO", "Primário")]), f(698.0, 806.0, [("MÓVEL PESSOAL", "Primário")], [("MÓVEL", "Primário")]),
              f(2400.0, 2483.5, [("COMUNICAÇÃO MULTIMÍDIA", "Primário"), ("Radioamador", "Secundário")], [("MÓVEL", "Primário")]),
              f(3300.0, 3400.0, [("MÓVEL PESSOAL", "Primário"), ("COMUNICAÇÃO MULTIMÍDIA", "Primário")], [("FIXO", "Primário"), ("MÓVEL", "Primário")]),
              f(3400.0, 3500.0, [("MÓVEL PESSOAL", "Primário")], [("MÓVEL", "Primário")])]
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Mon, 02 Nov 2026 10:30:09 GMT", "sha256": "0" * 64,
            "resumo": {"faixas": len(faixas), "com_destinacao": len(faixas), "com_atribuicao": len(faixas)}, "faixas": faixas}


def satelites(world: World, d: str) -> dict:
    """Satélites sintéticos: dois direitos de um mesmo satélite estrangeiro, um nacional vencido, um NGEO pendente, 1 constelação com CNPJ e 2 em operação."""
    def dr(op, sat, cod, pos, banda, tipo, status, lanc, val, pror):
        return {"operadora": op, "satelite": sat, "codigo": cod, "posicao": pos, "banda": banda, "tipo": tipo, "status": status, "lancamento": lanc, "validade": val, "prorrogado": pror}
    direitos = [dr("OPERADORA SAT ALFA LTD", "ALFA-1", "-3KuC", "3ºO", "C", "Estrangeiro", "operação comercial", "2015-01-03", "2030-12-24", True),
                dr("OPERADORA SAT ALFA LTD", "ALFA-1", "-3KuC", "3ºO", "Ku", "Estrangeiro", "operação comercial", "2015-01-03", "2030-12-24", True),
                dr("SATELITE BRASILEIRO SA", "BR-SAT 2", "-65KaB", "65ºO", "Ka", "Brasileiro", "operação comercial", "2020-05-10", "2026-01-31", False),
                dr("CONSTELACAO NOVA INC", "Sistema Novo", "SMB-X", "NGEO", "Q/V", "Estrangeiro", "pendente licença", None, None, False)]
    ngeo = [{"cnpj": "04399863000134", "prestadora": "IRIDIUM SERVIÇOS DE SATÉLITES S.A", "lancamento": "2017-01-14", "estacao": "IRD", "objeto": "Iridium", "status": "OPERAÇÃO COMERCIAL",
             "orbita": "BAIXA (LEO)", "planos": 6, "constelacao": 66, "agenda_ano": 2026, "nu_estacao": "900001"}]
    # REGULATORIO-E1: um sistema com um registro por ano de agenda (satélites declarados crescendo) e uma cópia exata da origem
    for ano, qt in ((2024, 120), (2025, 480), (2026, 960), (2026, 960)):
        ngeo.append({"cnpj": None, "prestadora": "CONSTELACAO NOVA INC", "lancamento": "2024-02-01", "estacao": "CNV", "objeto": "Sistema Novo LEO",
                     "status": "OPERAÇÃO COMERCIAL", "orbita": "BAIXA (LEO)", "planos": 12, "constelacao": qt, "agenda_ano": ano, "nu_estacao": "900002"})
    operando = [{"satelite": "ALFA-1", "posicao": "3ºO", "bandas": "C, Ku", "tipo": "Estrangeiro", "operadora": "OPERADORA SAT ALFA LTD"},
                {"satelite": "BR-SAT 2", "posicao": "65ºO", "bandas": "Ka", "tipo": "Brasileiro", "operadora": "SATELITE BRASILEIRO SA"}]
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Mon, 02 Nov 2026 10:30:10 GMT", "sha256": "0" * 64,
            "resumo": {"direitos": len(direitos), "ngeo": len(ngeo), "operando": len(operando)}, "direitos": direitos, "ngeo": ngeo, "operando": operando}


def ipv4(world: World, d: str) -> tuple[dict, dict, dict[str, list[dict]]]:
    """Mercado de IPv4 sintético: listas normalizadas, a última foto do `delegated` (só o que o produto lê) e eventos por mês. Plantados: um lote de 2 blocos entre dois provedores
    (1 operação), pessoa física na origem (nome mascarado), saída para o exterior (também no log do LACNIC: uma operação, 2 fontes), uma operação só do LACNIC com destino no Brasil,
    bloco em recuperação (reserved no delegated) e eventos de titularidade e recuperação."""
    br = sorted((a for a in world.ases.values() if a.is_br and a.role == "access"), key=lambda a: a.asn)[:4]
    p1, p2, p3, p4 = br
    reg = lambda t, i: {"id": f"rb{i}", "data": t[0], "origem": t[1], "rir_origem": "NICBR", "pais_origem": "BR", "destino": t[2], "rir_destino": t[3], "pais_destino": t[4], "blocos": [t[5]],       # noqa: E731
                        "enderecos": 256, "blocos_originais": [t[5]], "data_registro_original": "2012-05-01", "primeira_vez_visto": t[6], "anterior_a_coleta": t[6] == "2026-06-28"}
    trs = [reg(("2026-03-01", p1.name, p2.name, "NICBR", "BR", p2.v4[0], "2026-06-28"), 1), reg(("2026-03-01", p1.name, p2.name, "NICBR", "BR", p2.v4[1], "2026-06-28"), 2),
           reg(("2026-08-20", "JOAO DA SILVA SANTOS", p3.name, "NICBR", "BR", p3.v4[0], d), 3), reg(("2026-09-10", p4.name, "DELTA CORP", "LACNIC", "AR", p4.v4[0], d), 4)]
    lac = lambda t, i: {"id": f"lc{i}", "data": t[0], "origem": t[1], "pais_origem": t[2], "rir_origem": t[3], "destino": t[4], "pais_destino": t[5], "rir_destino": t[6], "blocos": [t[7]], "blocos_originais": [t[7]],   # noqa: E731
                        "enderecos": 256, "asns": [], "ipv6": False, "data_registro_original": "2010-01-01", "tipo_log": "RESOURCE_TRANSFER", "primeira_vez_visto": t[8], "anterior_a_coleta": t[8] == "2026-06-28"}
    lcs = [lac(("2026-09-10", p4.name, "BR", "NICBR", "DELTA CORP", "AR", "LACNIC", p4.v4[0], d), 1), lac(("2026-07-15", "SIGMA LTDA", "CL", "LACNIC", p2.name, "BR", "NICBR", p2.v4[0], "2026-06-28"), 2),
           lac(("2026-02-01", "OMEGA SA", "MX", "LACNIC", "PSI SA", "AR", "LACNIC", "203.0.113.0/24", "2026-06-28"), 3)]
    recup_bloco = p4.v4_idle[0] if p4.v4_idle else "198.18.10.0/24"
    doc = {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "resumo": {}, "transferencias_registrobr": trs, "transferencias_lacnic": lcs,
           "recuperacao": [{"tipo": "bloco", "recurso": recup_bloco, "inicio": "2026-09-01", "fim": "2026-11-30", "primeira_vez_visto": "2026-06-28", "anterior_a_coleta": True},
                           {"tipo": "asn", "recurso": "64999", "inicio": "2026-09-01", "fim": "2026-11-30", "primeira_vez_visto": d, "anterior_a_coleta": False}],
           "recuperados": [{"tipo": "bloco", "recurso": "198.19.5.0/24", "primeira_vez_visto": "2026-06-28", "anterior_a_coleta": True}, {"tipo": "asn", "recurso": "65001", "primeira_vez_visto": "2026-06-28", "anterior_a_coleta": True}]}
    blocos = {}
    for a in sorted((a for a in world.ases.values() if a.is_br), key=lambda a: a.asn):
        for b in a.v4 + a.v4_idle:
            n = ipaddress.ip_network(b)
            if b == recup_bloco:
                blocos[f"{n.network_address}/{n.num_addresses}"] = {"cc": None, "status": "reserved", "data": None, "opaque": None, "inicio": str(n.network_address), "quantidade": n.num_addresses}
            else:
                blocos[f"{n.network_address}/{n.num_addresses}"] = {"cc": "BR", "status": "allocated", "data": "20120501", "opaque": f"org-{a.asn}", "inicio": str(n.network_address), "quantidade": n.num_addresses}
    estado = {"dia": d, "blocos": blocos}
    n2 = ipaddress.ip_network(p2.v4[0])
    ev = {"2026-03": [{"id": "e1", "data": "2026-03-02", "tipo": "titularidade", "inicio": str(n2.network_address), "quantidade": n2.num_addresses, "blocos": [p2.v4[0]],
                       "de": {"cc": "BR", "status": "allocated", "opaque": f"org-{p1.asn}"}, "para": {"cc": "BR", "status": "allocated", "opaque": f"org-{p2.asn}"}}],
          "2026-09": [{"id": "e2", "data": "2026-09-05", "tipo": "recuperacao", "inicio": recup_bloco.split("/")[0], "quantidade": 256, "blocos": [recup_bloco],
                       "de": {"cc": "BR", "status": "allocated", "opaque": f"org-{p4.asn}"}, "para": {"cc": None, "status": "reserved", "opaque": None}}]}
    return doc, estado, ev


def seguranca(world: World) -> tuple[dict, dict, dict, dict]:
    """Fontes de segurança sintéticas: ROV/DNSSEC do APNIC, AS Rank do CAIDA e bogons. Plantados: 64503 valida ROV (97%); 64505 tem 55% mas só
    40 amostras (fica fora dos agregados); 64500 origina um prefixo dentro de um bogon do Team Cymru e 64501 um dentro do espaço reservado da IANA."""
    br = sorted(a for a, x in world.ases.items() if x.is_br)
    irov = {}
    for a in br:
        irov[str(a)] = {"validates_pct": 0.4, "amostras": 900 + a % 7}
    irov["64503"] = {"validates_pct": 97.0, "amostras": 5000}
    irov["64505"] = {"validates_pct": 55.0, "amostras": 40}
    dnssec = {str(a): {"validates_pct": 90.0 - (i * 7) % 60, "parcial_pct": 3.0, "amostras": 400 + i} for i, a in enumerate(br[:6])}
    asrank = {str(a): {"rank": 1000 + i, "fonte_rir": "LACNIC", "clique": False, "org_id": f"org{a}", "cone": {"asns": 1 + i, "prefixos": 2 + i, "enderecos": 256 * (i + 1)},
                       "grau": {"total": 2 + i, "cliente": i, "par": 1, "provedor": 1}} for i, a in enumerate(br)}
    cymru = [world.ases[64500].v4[0]]
    iana = [world.ases[64501].v4[0]]
    wrap = lambda d, extra: {"snapshot_date": "2026-01-01", "generated_at": "2026-01-01T00:00:00+00:00", **extra}
    return (
        wrap(irov, {"as_of": "2026-09-19", "janela_dias": 7, "copyright": "sintético", "asns": irov, "total": len(irov), "asns_sem_medicao": 0}),
        wrap(dnssec, {"as_of": "2026-09-18", "janela_dias": 1, "copyright": "sintético", "asns": dnssec, "total": len(dnssec), "asns_sem_medicao": 0}),
        wrap(asrank, {"fetched_at": "2026-01-01T00:00:00+00:00", "total_global": 100, "copyright": "sintético", "total": len(asrank), "asns": asrank}),
        wrap({}, {"iana": {"v4": [{"bloco": b, "nome": "Teste", "rfc": "[RFC 0]"} for b in iana], "v6": [],
                           "asns": [{"inicio": 64496, "fim": 64511, "motivo": "For documentation and sample code; reserved by [RFC 5398]"}]},
                  "cymru": {"as_of": "2026-09-19", "v4": cymru, "v6": []}}),
    )


def ooni_bloqueios(world: World) -> dict:
    """OONI sintético: dois dias agregados. O primeiro ASN do Brasil tem WhatsApp com 30 medições e 6 anomalias (a sonda declarou web bloqueado) e Tor com 12; o segundo só 4 medições
    (abaixo do mínimo, não publicado); webconnectivity por amostra no primeiro. Um ASN estrangeiro (64999) com muitas medições não entra no produto."""
    br = sorted(a for a, x in world.ases.items() if x.is_br)
    a1, a2 = str(br[0]), str(br[1])

    def dia(k):
        return {"testes": {"whatsapp": {a1: {"n": 15, "anom": 3 * k, "partes": {"web": 3 * k}}, a2: {"n": 2, "anom": 0}, "64999": {"n": 40, "anom": 0}},
                           "tor": {a1: {"n": 6, "anom": 0, "alvos": {"dir_port": [60, 58], "obfs4": [84, 20]}}}},
                "web": {a1: {"n": 50, "anom": 5, "partes": {"dns": 4, "tcp_ip": 1}, "sem_veredito": 2, "inacessivel": 7}},
                "web_amostra": {"horas_utc": [2, 10, 18], "arquivos": 3, "arquivos_da_amostra": 3, "bytes": 1000, "completa": True}}
    return {"snapshot_date": "2026-01-01", "fetched_at": "2026-01-01T00:00:00+00:00", "fonte": "https://ooni-data-eu-fra.s3.amazonaws.com/", "licenca": "CC BY-NC-SA 4.0",
            "licenca_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/", "atribuicao": "sintético (OONI, CC BY-NC-SA 4.0)", "janela_dias": 28, "horas_amostra_web": [2, 10, 18],
            "ultima_execucao": {}, "dias": {"2025-12-30": dia(1), "2025-12-31": dia(1)}}


def as2org_abusech(world: World) -> tuple[dict, dict]:
    """CAIDA as2org e abuse.ch sintéticos: os dois primeiros ASNs do Brasil são irmãos (mesma organização, que também tem um ASN no exterior); o resto tem organização própria.
    O Feodo traz um C2 online num ASN do Brasil e outro num ASN estrangeiro (que não entra no produto)."""
    br = sorted(a for a, x in world.ases.items() if x.is_br)
    asns = {}
    for i, a in enumerate(br):
        irmao = i < 2
        asns[str(a)] = {"org_id": "orgsint0" if irmao else f"orgsint{a}", "org_nome": "Organização Sintética Ltda" if irmao else f"Provedor Sintético {a}", "org_pais": "BR",
                        "membros_total": 3 if irmao else 1}
    as2org = {"snapshot_date": "2026-01-01", "fetched_at": "2026-01-01T00:00:00+00:00", "fonte": "https://api.asrank.caida.org/v2/graphql", "citacao": "sintético",
              "consultados": len(br), "requisicoes": 1, "asns": asns}
    feodo = {"total": 2, "online": 2, "asns": {str(br[2]): {"c2_total": 1, "c2_online": 1, "malware": {"Emotet": 1}}, "64999": {"c2_total": 1, "c2_online": 1, "malware": {"QakBot": 1}}}}
    abusech = {"snapshot_date": "2026-01-01", "fetched_at": "2026-01-01T00:00:00+00:00", "fonte": "https://feodotracker.abuse.ch/downloads/ipblocklist.json", "licenca": "CC0 (sintético)",
               "feodo": feodo, "urlhaus": {"estado": "indisponivel", "motivo": "exige Auth-Key (cadastro); não coletado (I-008)"}}
    return as2org, abusech


def spoofer_irr(world: World, d: str) -> tuple[dict, dict]:
    """Spoofer e IRR sintéticos: 64500 com testes suficientes e 100% bloqueado, 64501 suficiente e só 40%, 64502 com poucas sessões conclusivas (sem pontuação); 64500 tem todos os prefixos no TC
    e 64501 só o primeiro no RADB (o resto sem objeto)."""
    asn = lambda **k: {"sessoes": 12, "sessoes_v4": 12, "sessoes_v6": 0, "pct_nat_v4": 10.0, "ultima_sessao": "2026-09-01", "conclusivas_v6": 0, **k}
    spoofer = {"snapshot_date": d, "fetched_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "citacao": "The CAIDA UCSD Spoofer Project (sintético)", "novas_sessoes": 0,
               "resumo": {"sessoes_na_janela": 30, "asns": 3, "asns_suficientes": 2, "minimo_conclusivas": 5, "janela": {"inicio": "2025-11-02", "fim": d, "dias": 365}},
               "asns": {"64500": asn(conclusivas=8, conclusivas_v4=8, suficiente=True, pct_bloqueado=100.0, pct_recebido_privado=0.0, pct_recebido_roteado=0.0),
                        "64501": asn(conclusivas=10, conclusivas_v4=10, suficiente=True, pct_bloqueado=40.0, pct_recebido_privado=20.0, pct_recebido_roteado=60.0),
                        "64502": asn(sessoes=3, conclusivas=2, conclusivas_v4=2, suficiente=False, pct_bloqueado=100.0, pct_recebido_privado=0.0, pct_recebido_roteado=0.0)}}
    irr = {"snapshot_date": d, "fetched_at": "2026-01-01T00:00:00+00:00", "citacao": "TC IRR e RADb (sintético)", "asns_br_consultados": 3,
           "fontes": {"TC": {"serial": "1", "asns_br_com_route": 1}, "RADB": {"serial": "2", "asns_br_com_route": 1}},
           "rotas": {"TC": {"64500": sorted(world.ases[64500].v4)}, "RADB": {"64501": sorted(world.ases[64501].v4)[:1]}}, "aut_num": {"TC": [64500], "RADB": [64501]}}
    return spoofer, irr


def manrs(world: World, d: str) -> dict:
    """Lista de participantes do MANRS sintética: seis organizações com 2 ASNs brasileiros cada (os 12 primeiros do Brasil), uma mista (1 ASN BR e 1 fora) e uma estrangeira.
    Os nomes são marcadores (`MANRS-ORG-*`) que os testes de não vazamento procuram nos artefatos publicados."""
    br = sorted(a.asn for a in world.ases.values() if a.is_br)
    acao = {"marca": True, "pct": None}
    orgs = [{"org": f"MANRS-ORG-{i}", "aprovado": "2026-01-01", "areas": ["BR"], "asns": br[2 * i:2 * i + 2],
             "acoes": {"filtragem": acao, "anti_spoofing": {"marca": None, "pct": 100.0}, "coordenacao": acao, "roteamento": {"irr": 100.0, "rpki": 90.0, "marca": None}}} for i in range(6)]
    orgs.append({"org": "MANRS-ORG-MISTA", "aprovado": "2026-01-01", "areas": ["BR", "US"], "asns": [br[12], 15169], "acoes": orgs[0]["acoes"]})
    orgs.append({"org": "MANRS-ORG-EXTERIOR", "aprovado": "2026-01-01", "areas": ["US"], "asns": [3356], "acoes": orgs[0]["acoes"]})
    return {"snapshot_date": d, "fetched_at": "2026-01-01T00:00:00+00:00", "url": "https://manrs.org/netops/participants/", "medido_em": "2025-12-01",
            "atribuicao": "Provided by the MANRS with support from the Global Cyber Alliance", "sha256": "0" * 64, "participantes": orgs}


def _dicionario_alice() -> dict:
    """Dicionário de communities do Alice (forma do `/api/v1/config`), reduzido: motivos de rejeição, não exportar, informativas e blackhole."""
    return {"reject_reasons": {"26162": {"100": {"0": "Invalid on Registro.br"}, "190": {"0": "Invalid prefix length", "1": "Bogon prefix", "2": "Bogon ASN", "3": "Transit free", "4": "Never via route server",
                                                                                      "5": "IX.br prefixes"}, "300": {"0": "Invalid on RPKI"}, "400": {"0": "Invalid on RIRs"}, "616": {"666": "Confirmed blackhole"}},
                               "65535": {"616": {"666": "Blackhole"}}},
            "noexport": {"load_on_demand": True},
            "noexport_reasons": {"65000": {"0": {"*": "No export to AS$2"}}, "65001": {"0": {"*": "Only export to AS$2"}}, "65002": {"0": {"5": "No export to Brasil ASNs"}},
                                 "65003": {"0": {"5": "Only export to Brasil ASNs"}}, "65004": {"0": {"65021": "No export to IX.br Rio de Janeiro/RJ"}}},
            "reject_candidates": {}, "rpki": {"enabled": True, "valid": [["26162", "300", "1"]], "unknown": [["26162", "300", "2"]], "not_checked": [["26162", "300", "3"]],
                                              "invalid": [["26162", "300", "0"]]},
            "bgp_communities": {"26162": {"*": "Prefix being announced by AS$1", "0": {"*": "Prefix being announced by AS$2"}, "100": {"0": "Invalid on Registro.br", "1": "Valid on Registro.br"},
                                          "300": {"0": "Invalid on RPKI", "1": "Valid on RPKI", "2": "Unknown on RPKI"}}},
            "bgp_blackhole_communities": {"standard": [[[65535, 65535], [666, 666]]], "extended": [], "large": []}}


def rs_rotas(world: World, rs_doc: dict) -> tuple[dict, dict]:
    """Rotas rejeitadas (nível 2) e communities das rotas recebidas (nível 3) do Alice, sintéticas, sobre as sessões de `route_servers`. Plantados:
    PTT 0: o 2º membro com 40 rotas rejeitadas (25 RPKI inválido, 10 bogon, 5 nunca via RS) e política restritiva (só exporta para um ASN em 100% das rotas); o 3º com
    blackhole confirmado (3 rotas rejeitadas) e política seletiva (não exporta para 3 ASNs em 30% das rotas, nas formas grande e padrão, e 2 rotas com blackhole 65535:666); o 4º aberto.
    PTT 1: 1º membro com 6 rotas com RPKI inválido e política seletiva por estendida (rt:65000:N) e por PTT (65004:0:65021)."""
    gerado = "2026-01-01T06:00:00+00:00"
    por_ptt: dict[str, list[dict]] = {}
    for s in rs_doc["sessoes"]:
        if s["estado"] == "up" and s["rs"].endswith("rs1-v4"):
            por_ptt.setdefault(s["ixp"], []).append(s)
    codigos = sorted(por_ptt)
    filt, rec = [], []

    def viz(s, **kw):
        return {"rs": s["rs"], "ixp": s["ixp"], "afi": s["afi"], "asn": s["asn"], "ip": s["neighbor_ip"], "coletado_em": "2025-12-31T23:50:00Z", **kw}

    def pref(i, k):
        return f"198.18.{k}.{i}/32"
    for k, code in enumerate(codigos[:2]):
        ss = sorted(por_ptt[code], key=lambda x: x["asn"])
        if k == 0 and len(ss) >= 4:
            a, b, c = ss[1], ss[2], ss[3]
            filt.append(viz(a, total=40, sessao_filtradas=40, contagem="exata", motivos={"26162:300:0": 25, "26162:190:1": 10, "26162:190:4": 5}, sem_motivo=0,
                            amostra=[{"p": pref(i, k), "o": a["asn"], "m": ["26162:300:0"]} for i in range(7)] + [{"p": pref(10 + i, k), "o": a["asn"], "m": ["26162:190:1"]} for i in range(2)]))
            filt.append(viz(b, total=3, sessao_filtradas=3, contagem="exata", motivos={"26162:616:666": 3}, sem_motivo=0, amostra=[{"p": pref(50 + i, k), "o": b["asn"], "m": ["26162:616:666"]} for i in range(3)]))
            rec.append(viz(a, total=100, sessao_recebidas=100, contagem="exata", comunidades={f"65001:0:{c['asn']}": 100, f"26162:{a['asn']}": 100, "26162:300:1": 90, "26162:300:2": 10}))
            rec.append(viz(b, total=100, sessao_recebidas=100, contagem="exata", comunidades={"65000:0:64510": 30, "65000:0:64511": 30, "65000:0:64512": 30, "65000:64510": 30, "65000:64511": 30,
                                                                                         "65535:666": 2, "26162:300:1": 100}))
            rec.append(viz(c, total=50, sessao_recebidas=50, contagem="exata", comunidades={"26162:300:1": 50, f"26162:{c['asn']}": 50}))
        if k == 1 and ss:
            a = ss[0]
            filt.append(viz(a, total=6, sessao_filtradas=6, contagem="exata", motivos={"26162:300:0": 6}, sem_motivo=0, amostra=[{"p": pref(i, k), "o": a["asn"], "m": ["26162:300:0"]} for i in range(6)]))
            rec.append(viz(a, total=40, sessao_recebidas=40, contagem="exata", comunidades={"rt:65000:262704": 20, "65004:0:65021": 12, "26162:300:2": 40}))
    cob = {code: {"elegiveis": len(por_ptt[code]), "coletados": sum(1 for v in filt if v["ixp"] == code), "herdados": 0} for code in codigos}
    cob3 = {code: {"elegiveis": len(por_ptt[code]), "coletados": sum(1 for v in rec if v["ixp"] == code), "herdados": 0} for code in codigos}
    cab = {"snapshot_date": "2026-01-01", "generated_at": gerado, "fonte": "sintético", "versao_alice": "6.1.0", "page_size": 250, "requisicoes_da_rodada": len(filt) + len(rec), "orcamento": 4000}
    return {**cab, "nivel": 2, "cobertura": cob, "vizinhos": filt}, {**cab, "nivel": 3, "ptts": codigos, "cobertura": cob3, "vizinhos": rec}


def route_servers(world: World) -> tuple[dict, dict]:
    """Sessões dos route servers sintéticas: rs1 IPv4 por PTT com uma sessão por membro. Plantados: no 1º PTT o 1º membro tem a sessão down há 12 dias
    (down, mesmo com o cache de ROTAS do RS em BUSY: o estado das rotas não diz nada das sessões) e o 2º está com 90% do limite de importação; no 2º PTT o 1º membro está
    cadastrado e sem sessão; no 3º PTT há uma sessão de ASN não cadastrado e um 2º route server com o cache de vizinhos de 2 dias (a sessão down dele é incerta)."""
    gerado = "2026-01-01T06:00:00+00:00"
    rs, sessoes = [], []
    codigos = sorted(world.members)
    for k, code in enumerate(codigos):
        membros = sorted(world.members[code])
        if k == 1 and membros:
            membros = membros[1:]                              # cadastrado sem sessão
        extras = [4200000100] if k == 2 else []                # sessão sem cadastro
        linhas = []
        for i, asn in enumerate(membros + extras):
            down = k == 0 and i == 0
            recebidas = 90 if (k == 0 and i == 1) else 10 + i
            linhas.append({"rs": f"{code.upper()}-rs1-v4", "ixp": code, "afi": "v4", "neighbor_ip": f"198.19.{k}.{10 + i}", "asn": asn, "descricao": f"membro {asn}",
                           "estado": "down" if down else "up", "bgp_state": "Passive" if down else "Established",
                           "state_changed": "2025-12-19 10:00:00" if down else "2025-12-30 09:00:00",
                           "last_error": "BGP Error: Hold timer expired" if down else "",
                           "rotas": {"recebidas": 0 if down else recebidas, "aceitas": 0 if down else recebidas, "filtradas": 0, "exportadas": 100},
                           "import_limit": 100, "receive_limit": 100, "route_changes_import": {}})
        rs.append({"rs": f"{code.upper()}-rs1-v4", "ixp": code, "numero": "rs1", "afi": "v4", "nome": f"rs1.{code}.ix.br (IPv4)", "grupo": f"IX.br {code}",
                   "estado_rotas": "BUSY" if k == 0 else "READY", "rotas_atualizadas_em": gerado, "vizinhos_em": "2026-01-01T05:55:00+00:00", "rotas_importadas": 100 * len(linhas), "consultado": True, "erro": None,
                   "sessoes": len(linhas), "sessoes_up": sum(1 for x in linhas if x["estado"] == "up")})
        sessoes.extend(linhas)
        if k == 2:                                             # 2º route server do PTT com o cache de vizinhos velho (2 dias): a sessão down dele é incerta
            velha = {**linhas[0], "rs": f"{code.upper()}-rs2-v4", "neighbor_ip": f"198.19.{k}.99", "asn": 4200000101, "estado": "down", "state_changed": "2025-12-01 10:00:00",
                     "rotas": {"recebidas": 0, "aceitas": 0, "filtradas": 0, "exportadas": 0}}
            sessoes.append(velha)
            rs.append({"rs": f"{code.upper()}-rs2-v4", "ixp": code, "numero": "rs2", "afi": "v4", "nome": f"rs2.{code}.ix.br (IPv4)", "grupo": f"IX.br {code}", "estado_rotas": "READY",
                       "rotas_atualizadas_em": gerado, "vizinhos_em": "2025-12-30T06:00:00+00:00", "rotas_importadas": 0, "consultado": True, "erro": None, "sessoes": 1, "sessoes_up": 0})
    doc = {"snapshot_date": "2026-01-01", "generated_at": gerado, "fonte": "sintético", "versao_alice": "6.1.0", "total_rs": len(rs), "rs": rs, "sessoes": sessoes}
    comm = {"snapshot_date": "2026-01-01", "generated_at": gerado, "versao_alice": "6.1.0", **_dicionario_alice()}
    return doc, comm


def cetic(d: str) -> dict[str, dict]:
    """Tabelas do Cetic.br para o dataset sintético: os arquivos REAIS de `tests/fixtures/raw/cetic/` passados pelo normalizador de produção
    (são agregados públicos, CC BY 4.0, sem dado pessoal)."""
    from pathlib import Path

    from core import cetic as c
    raiz = Path(__file__).resolve().parents[1] / "fixtures" / "raw" / "cetic"
    out = {}
    for nome, arquivo, rotulo, ano, minimo in (("cetic_tic_domicilios", "tic_domicilios_2025_domicilios_tabelas_xlsx_v1.0.zip", "TIC Domicílios", 2025, 10),
                                               ("cetic_tic_provedores", "tic_provedores_2024_tabela_xlsx_v1.0.zip", "TIC Provedores", 2024, 30)):
        tabelas, linhas = c.normalizar((raiz / arquivo).read_bytes(), minimo)
        out[nome] = {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "pesquisa": rotulo, "edicao": ano, "fonte": f"Cetic.br|NIC.br, {rotulo} {ano} (tabelas)",
                     "licenca": c.LICENCA, "pagina": c.PAGINA.format(pesquisa=nome.split("_")[-1]), "url": "https://cetic.br/media/microdados/0/" + arquivo, "arquivo": arquivo,
                     "sha256": "0" * 64, "total_tabelas": len(tabelas), "total_linhas": len(linhas), "tabelas": tabelas, "linhas": linhas}
    import gzip

    from core import cetic_microdados as md
    grupos, lidas = md.estimar(gzip.decompress((raiz / "tic_domicilios_microdados_sintetico.csv.gz").read_bytes()))
    out["cetic_tic_domicilios_uf"] = {
        "snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "natureza": "estimativa_arandurape", "pesquisa": "TIC Domicílios", "edicao": 2025,
        "fonte": "Estimativa do Arandurapé a partir dos microdados da TIC Domicílios 2025 (Cetic.br|NIC.br)", "licenca": c.LICENCA, "pagina": c.PAGINA.format(pesquisa="domicilios"),
        "url": "https://cetic.br/media/microdados/0/base.csv", "arquivo": "base.csv", "sha256": "0" * 64, "domicilios_entrevistados": lidas,
        "metodo": {"replicas": md.REPLICAS, "variancia": "média dos quadrados dos desvios das réplicas", "margem": "1,96 × erro-padrão (95%)",
                   "supressao_n_minimo": md.N_MINIMO, "precisao_baixa_cv": md.CV_BAIXO},
        "indicadores": {i: {"rotulo": r, "definicao": df} for i, (_, _, r, df) in md.INDICADORES.items()}, "grupos": grupos}
    return out
