# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Operadoras e grupos: índices de operadoras (fixa e móvel), sócios e grupos societários, empresas relacionadas e contatos PeeringDB.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

import gzip
import json
import threading
from typing import Optional

from api.store import _log, _strip_scm_contacts
from core import marcas
from core.cpf import sem_socios_pessoa_fisica
from core.nome_grupo import nome_do_grupo
from core.outorgas import eh_outorga
from core.sociedade_anonima import marca_do_cnpj


#: Vínculo ASN ↔ CNPJ (decisão D5), do mais forte ao mais fraco. `cnpj`: o ASN está registrado no Registro.br com o mesmo CNPJ de 14 dígitos (fato);
#: `raiz`: com outro CNPJ da mesma raiz de 8 dígitos, matriz ou filial da mesma pessoa jurídica (inferido); `marca`: com a raiz de outra empresa da mesma marca na
#: tabela curada `config/curada_marcas_operadoras.yaml` (inferido); `estrangeiro`: AS de fora do Brasil ligado à marca pela seção `asns_estrangeiros` da mesma tabela
#: (inferido, rótulo próprio). `nenhum`: nada disso.
VINCULOS_ASN = ("cnpj", "raiz", "marca", "estrangeiro")
SELO_VINCULO = {"cnpj": "fato", "raiz": "inferido", "marca": "inferido", "estrangeiro": "inferido"}
REGRA_VINCULO = ("Vínculo ASN ↔ CNPJ: `cnpj` = ASN registrado no Registro.br com o mesmo CNPJ (fato); `raiz` = com outro CNPJ da mesma raiz de 8 dígitos, matriz "
                 "ou filial (inferido); `marca` = com a raiz de outra empresa da mesma marca na tabela curada do projeto (inferido); `estrangeiro` = AS de fora do "
                 "Brasil ligado pela marca (inferido); `nenhum` = nenhum desses. Somas de rede usam só `cnpj` e `raiz` (a mesma pessoa jurídica).")


LIMITE_INTEGRANTES_CABECALHO = 12     # integrantes do grupo societário listados no cabeçalho da operadora; o resto vai no link para o grupo


class OperadorasService:
    def __init__(self, store):
        self._s = store
        # Cache: date_str → (scm, sici, linhas) do operadora_index; vale enquanto o SCM e o SICI carregados forem os mesmos objetos
        self._operadora_index_cache: dict[str, tuple] = {}
        self._operadora_index_trava = threading.Lock()
        # Cache: "{date}/cnpj_asns" → {cnpj14: [asn, ...]}
        self._cnpj_asns_cache: dict[str, dict[str, list[int]]] = {}
        # Cache: date_str → {str(asn): [poc_dict, ...]} de peeringdb_contacts.json.gz
        self._pdb_contacts_cache: dict[str, Optional[dict]] = {}
        # Cache: date_str → (mtime, doc) de rdap_contatos.json.gz (muda a cada rodada diária, por isso a chave inclui o mtime)
        self._rdap_contatos_cache: dict[str, tuple[float, Optional[dict]]] = {}
        # Cache: date_str → índice do vínculo ASN ↔ CNPJ (`vinculo_asn_index`)
        self._vinculo_cache: dict[str, dict] = {}
        # Cache: date_str → dict completo de grupos_societarios.json.gz (sócios, `socios_grupos`)
        self._socios_grupos_cache: dict[str, Optional[dict]] = {}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def operadora_movel_index(self, date_str: str) -> list[dict]:
        """Uma linha por CNPJ operador móvel: cadastro SMP + acessos SICI móvel + ASNs.

        Espelha operadora_index, mas para SMP — mantido separado porque o universo é
        bem menor (~30 CNPJs) e majoritariamente disjunto do de SCM.
        """
        smp = self._load_smp(date_str)
        sici = self._load_sici_movel(date_str)
        if not smp and not sici:
            return []
        sici_cnpjs = (sici or {}).get("cnpjs", {})
        mes_ref = (sici or {}).get("mes_referencia", "")
        rows: dict[str, dict] = {}

        for cnpj, recs in (smp or {}).get("by_cnpj", {}).items():
            rec = _strip_scm_contacts(recs[0]) if recs else {}
            rows[cnpj] = {
                "cnpj": cnpj,
                "razao_social": rec.get("razao_social", ""),
                "nome_fantasia": rec.get("nome_fantasia", ""),
                "municipio_sede": rec.get("municipio", ""),
                "uf_sede": rec.get("uf", ""),
                "data_outorga": rec.get("data_outorga", ""),
                "outorgas": len(recs),
                "asns": rec.get("asns", []),
                "licenciado": True,
                "ativo": False,
                "rede_virtual": rec.get("rede_virtual"),
            }

        for cnpj, agg in sici_cnpjs.items():
            row = rows.setdefault(cnpj, {
                "cnpj": cnpj, "razao_social": "", "nome_fantasia": "",
                "municipio_sede": "", "uf_sede": "", "data_outorga": "",
                "outorgas": 0,
                "asns": agg.get("asns", []), "licenciado": False,
            })
            row.update({
                "ativo": True,
                "mes_referencia": mes_ref,
                "empresa": agg.get("empresa", ""),
                "grupo_economico": agg.get("grupo", ""),
                "porte": agg.get("porte", ""),
                "acessos": agg.get("acessos", 0),
                "acessos_pf": agg.get("pf", 0),
                "acessos_pj": agg.get("pj", 0),
                "acessos_m2m": agg.get("acessos_m2m", 0),
                "municipios": agg.get("municipios", 0),
                "geracao_predominante": agg.get("geracao_predominante", ""),
                "acessos_compartilhados": agg.get("acessos_compartilhados", False),
            })
            if not row["asns"]:
                row["asns"] = agg.get("asns", [])
        for row in rows.values():
            row.setdefault("acessos", 0)
            row.setdefault("acessos_pf", 0)
            row.setdefault("acessos_pj", 0)
            row.setdefault("municipios", 0)
            self._marcar_vinculo(date_str, row)
        return list(rows.values())

    def acessos_movel_municipio_index(self, date_str: str) -> list[dict]:
        """Uma linha por (município, operador móvel): acessos, share e ASNs."""
        rows: list[dict] = []
        for ibge, mun in self.sici_movel_municipios(date_str).items():
            for op in mun.get("operadores", []):
                rows.append({
                    "ibge": ibge,
                    "municipio": mun.get("nome", ""),
                    "uf": mun.get("uf", ""),
                    "cnpj": op.get("cnpj", ""),
                    "empresa": op.get("empresa", ""),
                    "acessos": op.get("acessos", 0),
                    "share": op.get("share", 0.0),
                    "asns": op.get("asns", []),
                    **self.vinculo_resumo(date_str, op.get("cnpj", "")),
                    "municipio_acessos": mun.get("acessos", 0),
                    "municipio_operadores": mun.get("operadores_count", 0),
                    "municipio_hhi": mun.get("hhi", 0),
                })
        return rows

    def operadora_index(self, date_str: str) -> list[dict]:
        """Uma linha por CNPJ operador: cadastro SCM + acessos SICI + ASNs.

        É a entidade que faltava no modelo: `scms` tem uma linha por OUTORGA, não por
        operadora. Inclui também CNPJs licenciados que não declaram acesso (`ativo`
        falso) — metade da base.
        """
        scm = self._load_scm(date_str)
        sici = self._load_sici(date_str)
        if not scm and not sici:
            return []
        # Memoizado: refeito a cada chamada, era ~12% do tempo da API no teste de carga de 2026-11-23 (o perfil de UF e o /meta o chamam
        # por pedido). As linhas são compartilhadas entre pedidos: só leitura.
        atual = self._operadora_index_cache.get(date_str)
        if atual is not None and atual[0] is scm and atual[1] is sici:
            return atual[2]
        with self._operadora_index_trava:
            atual = self._operadora_index_cache.get(date_str)
            if atual is not None and atual[0] is scm and atual[1] is sici:
                return atual[2]
            linhas = self._montar_operadora_index(date_str, scm, sici)
            self._operadora_index_cache[date_str] = (scm, sici, linhas)
            return linhas

    def _montar_operadora_index(self, date_str: str, scm, sici) -> list[dict]:
        sici_cnpjs = (sici or {}).get("cnpjs", {})
        mes_ref = (sici or {}).get("mes_referencia", "")
        rows: dict[str, dict] = {}

        for cnpj, recs in (scm or {}).get("by_cnpj", {}).items():
            rec = _strip_scm_contacts(recs[0]) if recs else {}
            rows[cnpj] = {
                "cnpj": cnpj,
                "razao_social": rec.get("razao_social", ""),
                "nome_fantasia": rec.get("nome_fantasia", ""),
                "municipio_sede": rec.get("municipio", ""),
                "uf_sede": rec.get("uf", ""),
                "data_outorga": rec.get("data_outorga", ""),
                "outorgas": len(recs),
                "asns": rec.get("asns", []),
                "licenciado": True,
                "ativo": False,
            }

        for cnpj, agg in sici_cnpjs.items():
            row = rows.setdefault(cnpj, {
                "cnpj": cnpj, "razao_social": "", "nome_fantasia": "",
                "municipio_sede": "", "uf_sede": "", "data_outorga": "",
                "outorgas": 0,
                "asns": agg.get("asns", []), "licenciado": False,
            })
            row.update({
                "ativo": True,
                "mes_referencia": mes_ref,
                "empresa": agg.get("empresa", ""),
                "grupo_economico": agg.get("grupo", ""),
                "porte": agg.get("porte", ""),
                "acessos": agg.get("acessos", 0),
                "acessos_pf": agg.get("pf", 0),
                "acessos_pj": agg.get("pj", 0),
                "capacidade_mbps": agg.get("capacidade_mbps", 0.0),
                "velocidade_media_mbps": agg.get("velocidade_media_mbps", 0.0),
                "velocidade_mediana_mbps": agg.get("velocidade_mediana_mbps", 0.0),
                "municipios": agg.get("municipios", 0),
                "tecnologia": agg.get("tecnologia_predominante", ""),
                "meio": agg.get("meio_predominante", ""),
                "acessos_compartilhados": agg.get("acessos_compartilhados", False),
            })
            if not row["asns"]:
                row["asns"] = agg.get("asns", [])
        for row in rows.values():
            row.setdefault("acessos", 0)
            row.setdefault("acessos_pf", 0)
            row.setdefault("acessos_pj", 0)
            row.setdefault("municipios", 0)
            self._marcar_vinculo(date_str, row)
        return list(rows.values())

    # -------------------------------------------------------------------------
    # Sócios — cruzamento de quadro societário (Receita Federal: `receita_socios` e `socios_grupos`)
    # -------------------------------------------------------------------------

    def _load_socios_grupos(self, date_str: str) -> Optional[dict]:
        """Carrega grupos_societarios.json.gz do snapshot. None se não disponível."""
        if date_str not in self._socios_grupos_cache:
            path = self._pub(date_str) / "grupos_societarios.json.gz"
            if not path.exists():
                self._socios_grupos_cache[date_str] = None
            else:
                try:
                    with gzip.open(path, "rt", encoding="utf-8") as f:
                        self._socios_grupos_cache[date_str] = sem_socios_pessoa_fisica(json.load(f))      # snapshots antigos ainda trazem sócio pessoa física
                except Exception:
                    _log.warning("failed to load grupos_societarios.json.gz for %s", date_str)
                    self._socios_grupos_cache[date_str] = None
        return self._socios_grupos_cache[date_str]

    def socios_grupos_index(self, date_str: str) -> list[dict]:
        """Uma linha por CNPJ: grupo societário, sócios, empresas relacionadas
        e holdings externas cruzadas via dados abertos de CNPJ da Receita.

        CNPJs sem nenhuma relação societária relevante (grupo de tamanho 1)
        não aparecem aqui — só o universo com algum sinal de cruzamento.
        """
        data = self._load_socios_grupos(date_str)
        if not data:
            return []
        return [row for row in data.get("by_cnpj", {}).values() if row.get("grupo_id")]

    def nome_comercial_do_cnpj(self, date_str: str, cnpj: str) -> Optional[str]:
        """Nome comercial de exibição de um CNPJ (cadeia de `_display_name_for_cnpj`), ou None quando nenhuma fonte tem nome: quem exibe não mostra o CNPJ como nome."""
        agg = self.sici_for_cnpj(date_str, cnpj)
        if agg and agg.get("empresa"):
            return agg["empresa"]
        agg_movel = self.sici_movel_for_cnpj(date_str, cnpj)
        if agg_movel and agg_movel.get("empresa"):
            return agg_movel["empresa"]
        for outorgas in (
            self.scm_for_cnpj(date_str, cnpj),
            self.smp_for_cnpj(date_str, cnpj),
            self.stfc_for_cnpj(date_str, cnpj),
            self.seac_for_cnpj(date_str, cnpj),
        ):
            if outorgas:
                nome = outorgas[0].get("razao_social") or outorgas[0].get("nome_fantasia")
                if nome:
                    return nome
        return None

    def _display_name_for_cnpj(self, date_str: str, cnpj: str) -> str:
        """Nome comercial de exibição — mesma cadeia de fallback da página de
        Operadora (OperadoraPage.tsx): SICI fixo → SICI móvel → outorga SCM →
        SMP → STFC → SeAC → o próprio CNPJ, se nada mais existir. Um CNPJ que só
        tem outorga SMP/STFC/SeAC (sem SCM nem declaração ao SICI) não tinha
        nome nenhum antes desse fallback completo."""
        return self.nome_comercial_do_cnpj(date_str, cnpj) or cnpj

    def outorgas_flags_for_cnpj(self, date_str: str, cnpj: str) -> dict[str, bool]:
        """Quais das 4 outorgas Anatel (SCM/SMP/STFC/SeAC) um CNPJ tem — para
        badges nas listas (Grupos de Empresas, empresas relacionadas, grupo
        econômico SICI). Um único lookup em `by_cnpj` de cada fonte já
        publicada, sem nova estrutura de dados."""
        return {
            "has_scm": cnpj in (self._load_scm(date_str) or {}).get("by_cnpj", {}),
            # credenciamento de rede virtual não é outorga SMP (`core.outorgas.eh_outorga`)
            "has_smp": any(eh_outorga(r) for r in (self._load_smp(date_str) or {}).get("by_cnpj", {}).get(cnpj, [])),
            "has_stfc": cnpj in (self._load_stfc(date_str) or {}).get("by_cnpj", {}),
            "has_seac": cnpj in (self._load_seac(date_str) or {}).get("by_cnpj", {}),
        }

    def _grupos_e_individuais(self, date_str: str) -> list[dict]:
        """Grupos societários (2+ empresas, de `grupos`) seguidos das empresas
        individuais — CNPJ básico da base sem relação societária com nenhuma
        outra — como "grupos de uma empresa só" (`grupo_id` = ``ind_{básico}``,
        classificação ``individual``; `cnpjs` = matriz + filiais do básico)."""
        socios_data = self._load_socios_grupos(date_str)
        if not socios_data:
            return []
        grupos = [
            {
                "grupo_id": g["grupo_id"],
                "classificacao": g.get("classificacao", "parcial"),
                "tamanho": g.get("tamanho", len(g.get("cnpjs", []))),
                "cnpjs": g.get("cnpjs", []),
            }
            for g in socios_data.get("grupos", [])
        ]
        individuais: dict[str, list[str]] = {}
        for cnpj, row in socios_data.get("by_cnpj", {}).items():
            if not row.get("grupo_id"):
                individuais.setdefault(cnpj[:8], []).append(cnpj)
        grupos.extend(
            {
                "grupo_id": f"ind_{basico}",
                "classificacao": "individual",
                "tamanho": 1,
                "cnpjs": sorted(cnpjs),
            }
            for basico, cnpjs in sorted(individuais.items())
        )
        return grupos

    def _grupos_indice(self, date_str: str) -> tuple[dict[str, dict], dict[str, str]]:
        """({grupo_id: grupo}, {cnpj básico: grupo_id}) de `_grupos_e_individuais`, cacheado por data."""
        chave = f"{date_str}/grupos_indice"
        atual = self._query_tables.get(chave)
        if atual is None:
            por_id: dict[str, dict] = {}
            por_basico: dict[str, str] = {}
            for g in self._grupos_e_individuais(date_str):
                por_id[g["grupo_id"]] = g
                for c in g["cnpjs"]:
                    por_basico[c[:8]] = g["grupo_id"]
            atual = self._query_tables[chave] = (por_id, por_basico)
        return atual

    def grupo_equivalente(self, date_str: str, grupo_id: str) -> Optional[str]:
        """Id atual do grupo para um `grupo_id` antigo (GRUPO-E14): o id de snapshots anteriores era a raiz da union-find (`grp_` + um CNPJ básico
        do conjunto, qualquer um) e hoje é o menor CNPJ básico. Ordem: o próprio id, a tabela `equivalencia_grupo_id` do snapshot, e o grupo (ou a
        empresa individual) que hoje contém o CNPJ básico do id (`grp_X`, `ind_X`). `None` se o CNPJ básico saiu da base."""
        por_id, por_basico = self._grupos_indice(date_str)
        if grupo_id in por_id:
            return grupo_id
        eq = ((self._load_socios_grupos(date_str) or {}).get("equivalencia_grupo_id") or {}).get(grupo_id)
        if eq in por_id:
            return eq
        prefixo, _, basico = grupo_id.partition("_")
        if prefixo in ("grp", "ind") and len(basico) == 8 and basico.isdigit():
            return por_basico.get(basico)
        return None

    def grupos_societarios_overview(self, date_str: str) -> list[dict]:
        """Uma linha por grupo societário (`grupo_id`), para a página "Grupos de
        Empresas": classificação (total/misto/parcial/individual), CNPJs membros,
        visibilidade BGP (algum AS do grupo origina bloco na tabela global),
        total de assinantes (acessos fixos SICI/SCM — não inclui móvel) e a
        distribuição municipal agregada dos acessos de todos os CNPJs do grupo
        (para o mapa). Inclui as empresas individuais (ver
        `_grupos_e_individuais`).

        Cacheado em memória por snapshot — é uma agregação um pouco pesada
        (itera `por_municipio` de cada CNPJ) e a página pede isso uma vez só.
        """
        cache_key = f"{date_str}/grupos_overview"
        cached = self._query_tables.get(cache_key)
        if cached is not None:
            return cached

        cnpj_asns = self.cnpj_asns_index(date_str)
        asn_map = self.asn_map(date_str)
        try:
            curada_marcas = marcas.carregar_curada()
        except Exception:
            _log.warning("curada_marcas_operadoras ilegível: nome do grupo sem marca curada", exc_info=True)
            curada_marcas = None

        sa_por_cnpj = {c: True for c, r in ((self._load_socios_grupos(date_str) or {}).get("by_cnpj") or {}).items() if r.get("grupo_inferivel") is False}
        rows: list[dict] = []
        for g in self._grupos_e_individuais(date_str):
            cnpjs = g["cnpjs"]
            raizes_sa = {c[:8] for c in cnpjs if sa_por_cnpj.get(c)}
            assinantes = 0
            assinantes_por_cnpj: dict[str, int] = {}
            municipios: dict[str, dict] = {}
            for cnpj in cnpjs:
                agg = self.sici_for_cnpj(date_str, cnpj)
                if agg:
                    acessos_cnpj = agg.get("acessos", 0)
                    assinantes += acessos_cnpj
                    assinantes_por_cnpj[cnpj] = acessos_cnpj
                    for ibge, mun in agg.get("por_municipio", {}).items():
                        entry = municipios.setdefault(ibge, {
                            "ibge": ibge, "nome": mun.get("nome", ""), "uf": mun.get("uf", ""),
                            "acessos": 0, "pf": 0, "pj": 0,
                        })
                        entry["acessos"] += mun.get("acessos", 0)
                        entry["pf"] += mun.get("pf", 0)
                        entry["pj"] += mun.get("pj", 0)
            # vínculo pela raiz (D5): o ASN registrado numa filial que não declara (AS26615 da TIM, AS4230 da Claro) entra no grupo;
            # a soma é sobre o conjunto de ASNs, então um ASN com dois CNPJs do grupo não conta duas vezes
            vinculados = self.asns_do_grupo(date_str, cnpjs)
            asns_do_grupo = {v["asn"] for v in vinculados}

            usuarios_apnic = sum(
                (asn_map.get(asn, {}).get("apnic_users") or 0) for asn in asns_do_grupo
            )
            # Algum AS do grupo origina ao menos um bloco na tabela BGP global.
            visibilidade_bgp = any(
                (asn_map.get(asn, {}).get("global_prefixes_v4_count") or 0)
                + (asn_map.get(asn, {}).get("global_prefixes_v6_count") or 0) > 0
                for asn in asns_do_grupo
            )

            cnpjs_out = sorted(
                (
                    {
                        "cnpj": cnpj,
                        "empresa": self._display_name_for_cnpj(date_str, cnpj),
                        "assinantes": assinantes_por_cnpj.get(cnpj, 0),
                        "asns": cnpj_asns.get(cnpj, []),
                        **self.outorgas_flags_for_cnpj(date_str, cnpj),
                        **({"grupo_inferivel": False} if sa_por_cnpj.get(cnpj) else {}),
                    }
                    for cnpj in cnpjs
                ),
                key=lambda c: -c["assinantes"],
            )

            rows.append({
                "grupo_id": g["grupo_id"],
                **nome_do_grupo(cnpjs, assinantes_por_cnpj, lambda c: self._display_name_for_cnpj(date_str, c), curada_marcas),
                "classificacao": g["classificacao"],
                "tamanho": g["tamanho"],
                "sociedades_anonimas": len(raizes_sa),             # empresas (raízes) do grupo cujo quadro não informa acionistas (P8)
                **(marca_do_cnpj({"grupo_inferivel": False}) if g["classificacao"] == "individual" and raizes_sa else {}),
                "assinantes": assinantes,
                "usuarios_apnic": usuarios_apnic,
                "visibilidade_bgp": visibilidade_bgp,
                "asns": sorted(asns_do_grupo),                                       # vínculos `cnpj` e `raiz` (D5)
                "asns_raiz": [v["asn"] for v in vinculados if v["vinculo"] == "raiz"],    # os que entram só pela raiz (filial que não está no grupo)
                "cnpjs": cnpjs_out,
                "municipios": sorted(municipios.values(), key=lambda m: -m["acessos"]),
            })

        self._query_tables[cache_key] = rows
        return rows

    def grupo_prefixos_geo(self, date_str: str, grupo_id: str) -> Optional[dict]:
        """Fallback de mapa para grupos sem acessos declarados ao SICI: bolhas
        dos blocos IPv6/IPv4 (tabela global) de todos os ASNs das empresas do
        grupo, agregadas por cidade — reaproveita `asn_geo` (fulltable_v4/v6),
        a mesma fonte do mapa de um AS individual.

        Calculado SOB DEMANDA (não em `grupos_societarios_overview`): geolocalizar
        prefixo por prefixo na base mmdb é caro demais para fazer eager nos
        ~18 mil grupos/empresas — só vale a pena para o grupo em foco na página, e só quando ele
        não tem município nenhum vindo do SICI.
        """
        grupo = next(
            (g for g in self._grupos_e_individuais(date_str) if g["grupo_id"] == grupo_id),
            None,
        )
        if not grupo:
            return None

        asns = {v["asn"] for v in self.asns_do_grupo(date_str, grupo.get("cnpjs", []))}
        if not asns:
            return {"type": "FeatureCollection", "features": []}

        agg: dict[tuple, dict] = {}
        for asn in asns:
            for afi in ("v4", "v6"):
                fc = self.asn_geo(date_str, asn, f"fulltable_{afi}")
                if not fc:
                    continue
                for feat in fc.get("features", []):
                    coords = (feat.get("geometry") or {}).get("coordinates")
                    props = feat.get("properties") or {}
                    if not coords:
                        continue
                    lon, lat = coords[0], coords[1]
                    key = (round(lat, 2), round(lon, 2), afi)
                    entry = agg.setdefault(key, {
                        "lat": lat, "lon": lon, "afi": afi,
                        "city": props.get("city", ""), "uf": props.get("uf", ""),
                        "block_count": 0,
                    })
                    entry["block_count"] += props.get("block_count", 0)

        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
                "properties": {k: v for k, v in e.items() if k not in ("lat", "lon")},
            }
            for e in agg.values()
        ]
        return {"type": "FeatureCollection", "features": features}

    def empresas_relacionadas(self, date_str: str, cnpj: str) -> dict:
        """Empresas relacionadas a um CNPJ via quadro societário (Receita), com
        nome comercial e ASNs resolvidos — para as seções "Empresas relacionadas"
        das páginas de Operadora e ASN."""
        socios_data = self._load_socios_grupos(date_str)
        row = (socios_data or {}).get("by_cnpj", {}).get(cnpj, {})
        cnpj_asns = self.cnpj_asns_index(date_str)

        def _enrich(items: list[dict]) -> list[dict]:
            return [
                {
                    **item,
                    "empresa": self._display_name_for_cnpj(date_str, item["cnpj"]),
                    "asns": cnpj_asns.get(item["cnpj"], []),
                    **{k: v for k, v in self.vinculo_resumo(date_str, item["cnpj"]).items() if k != "com_asn"},
                    **self.outorgas_flags_for_cnpj(date_str, item["cnpj"]),
                }
                for item in items
            ]

        grupo_id = row.get("grupo_id") or (f"ind_{cnpj[:8]}" if row else None)
        por_id, _ = self._grupos_indice(date_str)
        g = por_id.get(grupo_id) if grupo_id else None
        resumo = None
        if g:
            acessos = {c: (self.sici_for_cnpj(date_str, c) or {}).get("acessos", 0) for c in g["cnpjs"]}
            try:
                curada = marcas.carregar_curada()
            except Exception:
                curada = None
            resumo = {
                "grupo_id": g["grupo_id"], "classificacao": g["classificacao"], "tamanho": g["tamanho"],
                **nome_do_grupo(g["cnpjs"], acessos, lambda c: self._display_name_for_cnpj(date_str, c), curada),
                "integrantes": [{"cnpj": c, "empresa": self._display_name_for_cnpj(date_str, c), **self.outorgas_flags_for_cnpj(date_str, c)}
                                for c in g["cnpjs"] if c != cnpj][:LIMITE_INTEGRANTES_CABECALHO],
                "integrantes_total": len([c for c in g["cnpjs"] if c != cnpj]),
                **marca_do_cnpj(row),
            }
        return {
            "cnpj": cnpj,
            **marca_do_cnpj(row),
            "grupo_id": grupo_id,     # leva à página do grupo (`GET /grupos/{grupo_id}`)
            "grupo_societario": resumo,
            "mesmo_grupo": _enrich(row.get("mesmo_grupo", [])),
            "relacionadas_parcial": _enrich(row.get("relacionadas_parcial", [])),
        }

    def acessos_municipio_index(self, date_str: str) -> list[dict]:
        """Uma linha por (município, operador): acessos, share e ASNs, com o mês do SICI (`mes_referencia`)."""
        rows: list[dict] = []
        mes = self.sici_meta(date_str).get("mes_referencia") or None
        for ibge, mun in self.sici_municipios(date_str).items():
            for op in mun.get("operadores", []):
                rows.append({
                    "ibge": ibge,
                    "municipio": mun.get("nome", ""),
                    "uf": mun.get("uf", ""),
                    "cnpj": op.get("cnpj", ""),
                    "empresa": op.get("empresa", ""),
                    "acessos": op.get("acessos", 0),
                    "share": op.get("share", 0.0),
                    "asns": op.get("asns", []),
                    **self.vinculo_resumo(date_str, op.get("cnpj", "")),
                    "municipio_acessos": mun.get("acessos", 0),
                    "municipio_operadores": mun.get("operadores_count", 0),
                    "municipio_hhi": mun.get("hhi", 0),
                    "mes_referencia": mes,
                })
        return rows

    def cnpj_asns_index(self, date_str: str) -> dict[str, list[int]]:
        """Índice CNPJ (14 dígitos) → [asn, ...], a partir de geo_orgs. Cacheado.

        Independe de dados SCM; serve para listar ASNs de um mesmo grupo econômico.
        """
        key = f"{date_str}/cnpj_asns"
        cached = self._cnpj_asns_cache.get(key)
        if cached is not None:
            return cached
        import re as _re
        idx: dict[str, list[int]] = {}
        geo = self._load_geo_orgs(date_str) or {}
        for asn, org in geo.items():
            cnpj = _re.sub(r"\D", "", (org or {}).get("cnpj") or "")
            if len(cnpj) == 14:
                idx.setdefault(cnpj, []).append(int(asn))
        for v in idx.values():
            v.sort()
        self._cnpj_asns_cache[key] = idx
        return idx

    # -------------------------------------------------------------------------
    # Vínculo ASN ↔ CNPJ (decisão D5): fonte única para operadora, grupo, grupos, /ases, Home e MCP
    # -------------------------------------------------------------------------

    def vinculo_asn_index(self, date_str: str) -> dict:
        """Índice do vínculo ASN ↔ CNPJ de uma data: `por_raiz` {raiz: [(asn, cnpj14)]} (Registro.br, via `cnpj_asns_index`), `marcas_por_raiz`
        {raiz: [marca]} e `estrangeiros_por_raiz` {raiz: [entrada]} da tabela curada (`core.marcas.carregar_curada`). Cacheado por data."""
        atual = self._vinculo_cache.get(date_str)
        if atual is not None:
            return atual
        from core import marcas

        por_raiz: dict[str, list[tuple[int, str]]] = {}
        for cnpj, asns in self.cnpj_asns_index(date_str).items():
            por_raiz.setdefault(cnpj[:8], []).extend((a, cnpj) for a in asns)
        for v in por_raiz.values():
            v.sort()
        try:
            curada = marcas.carregar_curada()
        except Exception:
            _log.warning("curada_marcas_operadoras ilegível: vínculo ASN ↔ CNPJ sem `marca` nem `estrangeiro`", exc_info=True)
            curada = {"marcas": {}, "asns_estrangeiros": []}
        marcas_por_raiz: dict[str, list[dict]] = {}
        for chave in sorted(curada["marcas"]):
            m = curada["marcas"][chave]
            for r in m["raizes"]:
                marcas_por_raiz.setdefault(r, []).append(m)
        estrangeiros_por_raiz: dict[str, list[dict]] = {}
        for e in curada.get("asns_estrangeiros") or []:
            for r in e["raizes"]:
                estrangeiros_por_raiz.setdefault(r, []).append(e)
        idx = {"por_raiz": por_raiz, "marcas_por_raiz": marcas_por_raiz, "estrangeiros_por_raiz": estrangeiros_por_raiz, "memo": {}}
        self._vinculo_cache[date_str] = idx
        return idx

    def asns_vinculados(self, date_str: str, cnpj: str) -> list[dict]:
        """ASNs ligados a um CNPJ, um por ASN com o vínculo mais forte (`VINCULOS_ASN`): `{asn, vinculo, selo, cnpj_registro, marca?, base?, data?}`,
        em ordem de vínculo e ASN. `cnpj_registro` é o CNPJ do ASN no Registro.br (nulo no `estrangeiro`)."""
        cnpj = "".join(c for c in (cnpj or "") if c.isdigit())
        if len(cnpj) != 14:
            return []
        idx = self.vinculo_asn_index(date_str)
        memo = idx["memo"]
        if cnpj in memo:
            return memo[cnpj]
        raiz = cnpj[:8]
        vistos: dict[int, dict] = {}

        def por(asn: int, vinculo: str, **extra) -> None:
            if asn not in vistos:
                vistos[asn] = {"asn": asn, "vinculo": vinculo, "selo": SELO_VINCULO[vinculo], **extra}

        registrados = idx["por_raiz"].get(raiz, ())
        for asn, reg in registrados:
            if reg == cnpj:
                por(asn, "cnpj", cnpj_registro=reg)
        for asn, reg in registrados:
            por(asn, "raiz", cnpj_registro=reg)
        for m in idx["marcas_por_raiz"].get(raiz, ()):
            for outra in m["raizes"]:
                if outra != raiz:
                    for asn, reg in idx["por_raiz"].get(outra, ()):
                        por(asn, "marca", cnpj_registro=reg, marca=m["marca"], base=m["base"], data=m["data"])
        for e in idx["estrangeiros_por_raiz"].get(raiz, ()):
            for asn in e["asns"]:
                por(asn, "estrangeiro", cnpj_registro=None, marca=e["marca"], base=e["base"], data=e["data"])
        ordem = {v: i for i, v in enumerate(VINCULOS_ASN)}
        out = sorted(vistos.values(), key=lambda x: (ordem[x["vinculo"]], x["asn"]))
        memo[cnpj] = out
        return out

    def asn_vinculo(self, date_str: str, cnpj: str) -> str:
        """O vínculo mais forte do CNPJ com algum ASN (`cnpj`, `raiz`, `marca`, `estrangeiro`) ou `nenhum`."""
        v = self.asns_vinculados(date_str, cnpj)
        return v[0]["vinculo"] if v else "nenhum"

    def asns_mesma_pj(self, date_str: str, cnpj: str) -> list[int]:
        """ASNs da mesma pessoa jurídica (vínculos `cnpj` e `raiz`): a base das somas de rede de uma operadora."""
        return sorted(v["asn"] for v in self.asns_vinculados(date_str, cnpj) if v["vinculo"] in ("cnpj", "raiz"))

    def vinculo_resumo(self, date_str: str, cnpj: str) -> dict:
        """Campos do vínculo numa linha de collection: `asn_vinculo`, `asns_vinculados` (todos os vínculos) e `com_asn` (algum ASN brasileiro
        ligado: `cnpj`, `raiz` ou `marca`; o `estrangeiro` não conta)."""
        v = self.asns_vinculados(date_str, cnpj)
        vinculo = v[0]["vinculo"] if v else "nenhum"
        return {"asn_vinculo": vinculo, "asns_vinculados": [x["asn"] for x in v], "com_asn": vinculo in ("cnpj", "raiz", "marca")}

    def _marcar_vinculo(self, date_str: str, row: dict) -> None:
        # `asns` segue sendo o do mesmo CNPJ (fato); o vínculo pela raiz, pela marca e o estrangeiro vêm em `asns_vinculados`
        row.update(self.vinculo_resumo(date_str, row.get("cnpj", "")))

    def asns_do_grupo(self, date_str: str, cnpjs: list[str]) -> list[dict]:
        """ASNs de um conjunto de CNPJs (grupo societário) pelos vínculos da mesma pessoa jurídica: `cnpj` quando o ASN está registrado num
        dos CNPJs do conjunto, `raiz` quando está noutro CNPJ de uma das raízes (filial que não declara). Um ASN aparece uma vez. Marca não
        entra: liga empresas que podem estar em outro grupo, e um ASN não pode somar em dois grupos."""
        idx = self.vinculo_asn_index(date_str)
        membros = set(cnpjs)
        vistos: dict[int, dict] = {}
        for raiz in sorted({c[:8] for c in cnpjs}):
            for asn, reg in idx["por_raiz"].get(raiz, ()):
                vinculo = "cnpj" if reg in membros else "raiz"
                atual = vistos.get(asn)
                if atual is None or (atual["vinculo"] == "raiz" and vinculo == "cnpj"):
                    vistos[asn] = {"asn": asn, "vinculo": vinculo, "selo": SELO_VINCULO[vinculo], "cnpj_registro": reg}
        return sorted(vistos.values(), key=lambda x: (x["vinculo"] != "cnpj", x["asn"]))

    # -------------------------------------------------------------------------
    # PeeringDB contacts
    # -------------------------------------------------------------------------

    def _load_pdb_contacts(self, date_str: str) -> Optional[dict]:
        """Carrega peeringdb_contacts.json.gz. None se não disponível.

        Lê de normalized/ (artefato interno) — não de published/ — para que o arquivo
        não precise ser copiado para a superfície pública do snapshot.
        """
        if date_str not in self._pdb_contacts_cache:
            # normalized/ primeiro (contatos não vão para published/, pela AUP do PeeringDB);
            # published/ como alternativa para snapshot que os tenha publicado.
            norm_path = self.base / "normalized" / date_str / "summary" / "peeringdb_contacts.json.gz"
            pub_path = self._pub(date_str) / "peeringdb_contacts.json.gz"
            path = norm_path if norm_path.exists() else pub_path if pub_path.exists() else None
            if path is None:
                self._pdb_contacts_cache[date_str] = None
            else:
                try:
                    with gzip.open(path, "rt", encoding="utf-8") as f:
                        self._pdb_contacts_cache[date_str] = json.load(f)
                except Exception:
                    _log.warning("failed to load peeringdb_contacts.json.gz for %s", date_str)
                    self._pdb_contacts_cache[date_str] = None
        return self._pdb_contacts_cache[date_str]

    def peeringdb_contacts_for_asn(self, date_str: str, asn: int) -> list[dict]:
        """Contatos PeeringDB de visibilidade `Public` para um ASN. [] se não disponível.

        Só `Public`. Arquivo de coleta anterior a essa mudança não traz `visible`: nada dele é servido,
        porque ali `Public` e `Users` estão misturados; a coleta semanal seguinte repõe os públicos."""
        data = self._load_pdb_contacts(date_str)
        if not data:
            return []
        return [c for c in data.get("contacts", {}).get(str(asn), []) if c.get("visible") == "Public"]

    # -------------------------------------------------------------------------
    # RDAP do Registro.br: contatos administrativo e de abuso
    # -------------------------------------------------------------------------

    def _load_rdap_contatos(self, date_str: str) -> Optional[dict]:
        """`rdap_contatos.json.gz` mais recente até `date_str`, lido de normalized/ (NUNCA de published/: é dado de contato). None se não houver."""
        raiz = self.base / "normalized"
        if not raiz.is_dir():
            return None
        arq = None
        for d in sorted((p.name for p in raiz.iterdir() if p.is_dir() and p.name <= date_str), reverse=True):
            cand = raiz / d / "summary" / "rdap_contatos.json.gz"
            if cand.is_file():
                arq = cand
                break
        if arq is None:
            return None
        mtime = arq.stat().st_mtime
        cache = self._rdap_contatos_cache.get(date_str)
        if cache and cache[0] == mtime:
            return cache[1]
        try:
            with gzip.open(arq, "rt", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            _log.warning("failed to load rdap_contatos.json.gz for %s", date_str)
            doc = None
        self._rdap_contatos_cache[date_str] = (mtime, doc)
        return doc

    def rdap_contatos_for_asn(self, date_str: str, asn: int) -> dict:
        """Contatos RDAP de um ASN: {contatos: [{papel, email, handle}], leitura_em, tentou_em, status, cobertura}. Sem arquivo ou sem o ASN: contatos vazios.

        Só serve rota protegida por login. `cobertura` é o resumo do rodízio (contagens e datas, sem dado pessoal): "N de M ASNs com contato lido"."""
        doc = self._load_rdap_contatos(date_str) or {}
        v = (doc.get("contatos") or {}).get(str(asn)) or {}
        return {"contatos": v.get("contatos") or [], "leitura_em": v.get("em"), "tentou_em": v.get("tentou_em"), "status": v.get("status"),
                "cobertura": doc.get("cobertura")}
