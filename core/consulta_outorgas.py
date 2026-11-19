# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consulta às outorgas declaradas: o que a REST e o MCP geradas compartilham, sem FastAPI nem MCP.

Filtros, ordenação, paginação e estatísticas de uma lista de outorgas (`scm_index`, `stfc_index`…), conforme a declaração em
`serve/capabilities/<entidade>.yaml`. Quem chama cuida do transporte (HTTP 404/400 ou `ValueError` do MCP).
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from core.capacidades import Capacidade, Filtro, Operacao
from core.outorgas import SERVICOS as _SERVICOS

_NAO_DIGITO = re.compile(r"\D")


def limpar_cnpj(bruto: str) -> str:
    return _NAO_DIGITO.sub("", bruto)


def chave_data_br(s: dict) -> tuple:
    """\"DD/MM/YYYY\" → (ano, mês, dia); inválidos = (0, 0, 0), os mais antigos."""
    partes = (s.get("data_outorga") or "").split("/")
    if len(partes) == 3:
        try:
            return (int(partes[2]), int(partes[1]), int(partes[0]))
        except ValueError:
            pass
    return (0, 0, 0)


def chave_de_ordenacao(campo: str) -> Callable[[dict], object]:
    if campo.startswith("sici_"):
        return lambda s: s.get(campo) or 0
    if campo == "data_outorga":
        return chave_data_br
    if campo == "asns":
        def por_asns(s: dict):
            asns = s.get("asns") or []
            return (len(asns), asns[0] if asns else 0)        # sem ASN conta como 0 (vai ao fim no desc)
        return por_asns
    return lambda s: (s.get(campo) or "").lower()


def um_por_cnpj(registros: list[dict]) -> list[dict]:
    """Uma linha por CNPJ: entre as outorgas de um mesmo CNPJ, mantém a geolocalizada e, em empate, a de outorga mais recente."""
    melhor: dict[str, dict] = {}
    for s in registros:
        atual = melhor.get(s.get("cnpj"))
        if atual is None or (s.get("lat") is not None, chave_data_br(s)) > (atual.get("lat") is not None, chave_data_br(atual)):
            melhor[s.get("cnpj")] = s
    return list(melhor.values())


def aplicar(f: Filtro, valor, registros: list[dict], tri_estado: bool = False) -> list[dict]:
    """Aplica um filtro da declaração. `tri_estado`: `tem_asn` com False = só os SEM ASN (MCP); sem ele, False não filtra (REST)."""
    t, campo = f.tipo, f.campo
    if t == "igual":
        if not valor:
            return registros
        v = valor.upper()
        return [s for s in registros if (s.get(campo) or "").upper() == v]
    if t == "substring":
        if not valor:
            return registros
        v = valor.lower()
        return [s for s in registros if v in (s.get(campo) or "").lower()]
    if t == "busca":
        if not valor:
            return registros
        v, digitos = valor.lower(), limpar_cnpj(valor)

        def casa(s: dict) -> bool:
            return (v in (s.get("razao_social") or "").lower() or v in (s.get("nome_fantasia") or "").lower()
                    or bool(digitos and digitos in (s.get("cnpj") or "")))
        return [s for s in registros if casa(s)]
    if t == "tem_asn":
        if tri_estado and valor is not None:
            return [s for s in registros if bool(s.get("asns")) is valor]
        return [s for s in registros if s.get("asns")] if valor else registros
    if t == "ativo":
        return registros if valor is None else [s for s in registros if bool(s.get(campo)) is valor]
    if t == "minimo":
        return registros if valor is None else [s for s in registros if (s.get(campo) or 0) >= valor]
    raise AssertionError(t)


def paginar(registros: list[dict], page: int, limit: int) -> tuple[int, int, list[dict]]:
    """(total, páginas, itens da página)."""
    total = len(registros)
    ini = (page - 1) * limit
    return total, ((total + limit - 1) // limit if total > 0 else 0), registros[ini: ini + limit]


def consultar(op: Operacao, registros: list[dict], valores: dict, *, sort_by: Optional[str] = None, sort_desc: bool = False,
              tri_estado: bool = False, deduplicar: Optional[bool] = None) -> list[dict]:
    """Filtros (na ordem da declaração), um por CNPJ se pedido e ordenação (só por campo declarado)."""
    for f in op.filtros:
        if f.nome in valores:
            registros = aplicar(f, valores[f.nome], registros, tri_estado)
    if op.deduplicar_por_cnpj if deduplicar is None else deduplicar:
        registros = um_por_cnpj(registros)
    if sort_by and sort_by in op.ordena_por:
        registros = sorted(registros, key=chave_de_ordenacao(sort_by), reverse=sort_desc)
    return registros


def contar_por_uf(registros: list[dict]) -> tuple[dict, list]:
    com: dict[str, int] = {}
    sem: dict[str, int] = {}
    for s in registros:
        uf = s.get("uf") or "??"
        alvo = com if s.get("asns") else sem
        alvo[uf] = alvo.get(uf, 0) + 1
    por_uf = {uf: com.get(uf, 0) + sem.get(uf, 0) for uf in set(com) | set(sem)}
    detalhe = [{"uf": uf, "with_asn": com.get(uf, 0), "without_asn": sem.get(uf, 0)} for uf in sorted(por_uf, key=lambda u: -por_uf[u])]
    return por_uf, detalhe


def estatisticas(cap: Capacidade, op: Operacao, store, data_snapshot: str, dados: dict) -> dict:
    """Corpo de `/<servico>s/stats`: totais do snapshot, cobertura por UF e os blocos pedidos pela declaração."""
    sigla = cap.servico
    registros = dados.get(_SERVICOS[sigla].chave, [])
    por_uf, detalhe = contar_por_uf(registros)
    licenciados, cnpj_asns = dados.get("by_cnpj", {}), dados.get("cnpj_to_asns", {})
    saida = {
        "snapshot_date": data_snapshot, "total": dados.get("total", 0), "unique_cnpjs": dados.get("unique_cnpjs", 0),
        "geolocated": sum(1 for s in registros if s.get("lat") is not None), "matched_asns": dados.get("matched_asns", 0),
        "cnpjs_with_asn": sum(1 for c in licenciados if c in cnpj_asns),
    }
    if "cobertura_asn" in op.blocos:
        # cobertura regulatória dos ASes BR (licença × autonomia no BGP)
        asns_br = {a["asn"] for a in store.asn_index(data_snapshot) if a.get("is_br")}
        com_outorga = len(asns_br & getattr(store, f"{sigla}_asn_set")(data_snapshot))
        saida |= {"total_asns_br": len(asns_br), f"as_with_{sigla}": com_outorga, f"as_without_{sigla}": len(asns_br) - com_outorga}
    saida |= {"by_uf": dict(sorted(por_uf.items(), key=lambda kv: -kv[1])), "uf_breakdown": detalhe}
    if "top_municipios" in op.blocos:
        munis: dict[tuple[str, str], int] = {}
        for s in registros:
            if s.get("municipio"):
                k = (s["municipio"], s.get("uf") or "??")
                munis[k] = munis.get(k, 0) + 1
        saida["top_municipios"] = [{"municipio": m, "uf": u, "count": c} for (m, u), c in sorted(munis.items(), key=lambda kv: -kv[1])[:15]]
    if "rede_virtual" in op.blocos:
        credenciadas = [s for s in registros if (s.get("rede_virtual") or {}).get("papel") == "credenciada"]
        saida["rede_virtual"] = {
            "hosts": sum(1 for s in registros if (s.get("rede_virtual") or {}).get("papel") == "host"),
            "credenciadas": len(credenciadas),
            "credenciadas_sem_outorga_propria": sum(1 for s in credenciadas if not s.get("data_outorga")),
        }
    return saida
