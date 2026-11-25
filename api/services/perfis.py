# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Perfis territoriais e outorgas unificadas: município, UF, PTTs próximos, centroides e a lista única de outorgas por CNPJ.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from api.geo import haversine_km
from api.store import _MMDB_UNINIT


# Base mínima da taxa de reclamações por município: a mesma régua de 30 casos das demais estatísticas de reclamação.
MIN_RECLAMACOES_TAXA = 30

class PerfisService:
    def __init__(self, store):
        self._s = store
        self._asns_por_uf: dict[str, dict[str, dict]] = {}
        self._centroides: Optional[dict] = _MMDB_UNINIT  # type: ignore[assignment]
        self._outorgas_unif: dict[str, list[dict]] = {}
        self._ptts_pontos: dict[str, list[dict]] = {}
        self._resumo_ufs: dict[str, list[dict]] = {}
        self._operadoras_por_uf: dict[str, dict[str, list[dict]]] = {}
        self._territorio_linhas: dict[str, list[dict]] = {}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def outorgas_unificadas(self, date_str: str) -> list[dict]:
        """Uma linha por CNPJ que tem outorga de SCM, SMP, STFC e/ou SeAC: `servicos` (siglas em maiúsculas), `outorgas`, sede
        (UF/município da primeira outorga com UF), `asns`, `porte` e os acessos declarados ao SICI (fixo e móvel). Sem contatos.
        Cacheado por data (2)."""
        cache = self._outorgas_unif
        if date_str in cache:
            return cache[date_str]
        linhas: dict[str, dict] = {}
        for sigla in self._SERVICOS_SIGLAS:
            for rec in self._outorgas[sigla].index(date_str):
                cnpj = rec.get("cnpj")
                if not cnpj:
                    continue
                l = linhas.get(cnpj)
                if l is None:
                    l = linhas[cnpj] = {"cnpj": cnpj, "razao_social": "", "nome_fantasia": "", "uf": "", "municipio": "",
                                        "data_outorga": "", "data_outorga_por_servico": {}, "servicos": [], "outorgas": 0, "asns": []}
                if self._SERVICOS_NOMES[sigla] not in l["servicos"]:
                    l["servicos"].append(self._SERVICOS_NOMES[sigla])
                l["outorgas"] += 1
                for campo in ("razao_social", "nome_fantasia"):
                    l[campo] = l[campo] or rec.get(campo) or ""
                if not l["uf"] and rec.get("uf"):
                    l["uf"], l["municipio"] = rec["uf"], rec.get("municipio") or ""
                l["asns"] = l["asns"] or list(rec.get("asns") or [])
                d = rec.get("data_outorga") or ""
                nome = self._SERVICOS_NOMES[sigla]
                if d and (not l["data_outorga_por_servico"].get(nome) or self._data_br(d) < self._data_br(l["data_outorga_por_servico"][nome])):
                    l["data_outorga_por_servico"][nome] = d
        fixo = (self._load_sici(date_str) or {}).get("cnpjs", {})
        movel = (self._load_sici_movel(date_str) or {}).get("cnpjs", {})
        for cnpj, l in linhas.items():
            f, m = fixo.get(cnpj) or {}, movel.get(cnpj) or {}
            l["acessos_fixo"] = f.get("acessos", 0)
            l["pj_fixo"] = f.get("pj", 0)
            l["municipios_fixo"] = f.get("municipios", 0)
            l["tecnologia_fixo"] = f.get("tecnologia_predominante", "")
            l["acessos_movel"] = m.get("acessos", 0)
            l["pj_movel"] = m.get("pj", 0)
            l["municipios_movel"] = m.get("municipios", 0)
            datas = sorted(l["data_outorga_por_servico"].values(), key=self._data_br)
            l["data_outorga"] = datas[0] if datas else ""
            l["acessos"] = l["acessos_fixo"] + l["acessos_movel"]
            l["ativo"] = l["acessos"] > 0
            l["porte"] = f.get("porte") or m.get("porte") or ""
            if not l["razao_social"]:
                l["razao_social"] = f.get("empresa") or m.get("empresa") or ""
            l["servicos"].sort(key=self._SERVICOS_ORDEM.index)
            l.update(self.vinculo_resumo(date_str, cnpj))                # `asn_vinculo`, `asns_vinculados` e `com_asn` (D5)
        out = sorted(linhas.values(), key=lambda r: r["cnpj"])
        if len(cache) >= 2:
            cache.pop(next(iter(cache)))
        cache[date_str] = out
        return out

    _SERVICOS_ORDEM = ("SCM", "SMP", "STFC", "SeAC")

    @staticmethod
    def _data_br(d: str) -> tuple:
        """"DD/MM/AAAA" → (ano, mês, dia); inválida = (0, 0, 0) (mais antiga)."""
        p = (d or "").split("/")
        try:
            return (int(p[2]), int(p[1]), int(p[0])) if len(p) == 3 else (0, 0, 0)
        except ValueError:
            return (0, 0, 0)

    def outorgas_do_cnpj(self, date_str: str, cnpj: str) -> dict[str, list[dict]]:
        """As outorgas de um CNPJ por serviço (`{"SCM": [...], ...}`), sem contatos; serviços sem outorga ficam de fora."""
        out = {}
        for sigla in self._SERVICOS_SIGLAS:
            recs = self._outorgas[sigla].for_cnpj(date_str, cnpj)
            if recs:
                out[self._SERVICOS_NOMES[sigla]] = recs
        return out



    # -------------------------------------------------------------------------
    # Perfil do município: fixo + móvel + PTTs mais próximos numa resposta
    # -------------------------------------------------------------------------

    def municipio_centroide(self, ibge: str) -> Optional[tuple[float, float]]:
        """(lon, lat) do município, de config/municipios-centroides.json (mesma fonte do frontend)."""
        if self._centroides is _MMDB_UNINIT:
            path = Path(__file__).resolve().parents[2] / "config" / "municipios-centroides.json"
            try:
                self._centroides = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._centroides = {}
        c = (self._centroides or {}).get(ibge)  # type: ignore[union-attr]
        return (c[0], c[1]) if c else None

    def ptts_pontos(self, date_str: str) -> list[dict]:
        """PTTs com coordenadas, um por (código, local de PIX), na ordem da configuração. Cacheado por data.

        Só os PTTs do snapshot (`ixps/index.json` da data, com ou sem coleta): é a mesma lista da contagem de PTTs por UF, e um PTT que
        ainda não existia na data não serve de "PTT mais próximo". Sem índice na data, vale a configuração inteira."""
        if date_str not in self._ptts_pontos:
            vistos: set[tuple] = set()
            out: list[dict] = []
            do_snapshot = {e.get("code") for e in self.ixp_index(date_str) or []}
            for f in self._pix_features(date_str):
                c = f.get("geometry", {}).get("coordinates") or []
                p = f.get("properties", {})
                code = p.get("ixp_code")
                if len(c) < 2 or not code or (code, c[0], c[1]) in vistos or (do_snapshot and code not in do_snapshot):
                    continue
                vistos.add((code, c[0], c[1]))
                out.append({"codigo": code, "nome": p.get("ixp_name") or code, "lon": c[0], "lat": c[1]})
            self._ptts_pontos[date_str] = out
        return self._ptts_pontos[date_str]

    def ptt_mais_proximo(self, date_str: str, lon: float, lat: float) -> Optional[dict]:
        """O PTT mais próximo (com `km`), sem ordenar todos: usado nas contas por município."""
        pontos = self.ptts_pontos(date_str)
        if not pontos:
            return None
        p = min(pontos, key=lambda q: haversine_km(lat, lon, q["lat"], q["lon"]))
        return {**p, "km": round(haversine_km(lat, lon, p["lat"], p["lon"]), 1)}

    def ptts_proximos(self, date_str: str, lon: float, lat: float, n: int = 5) -> list[dict]:
        """Os `n` PTTs mais próximos do ponto, com a distância em linha reta (km). Um PTT com vários locais
        (ex.: vix) aparece uma vez só, pelo local mais próximo."""
        out = [{**p, "km": round(haversine_km(lat, lon, p["lat"], p["lon"]), 1)} for p in self.ptts_pontos(date_str)]
        out.sort(key=lambda x: x["km"])
        unicos, vistos = [], set()
        for p in out:
            if p["codigo"] not in vistos:
                vistos.add(p["codigo"])
                unicos.append(p)
        return unicos[:n]

    def _reclamacoes_100mil(self, date_str: str) -> dict:  # noqa: C901
        """Reclamações na Anatel por 100 mil habitantes de cada município no **último ano completo** (o ano em curso fica de fora: está pela metade).
        `{"ano": A, "por_ibge": {ibge: taxa}}`; vazio se as reclamações não estão publicadas. A taxa vem do próprio bloco municipal (`por_100mil_hab`)."""
        vazio = {"ano": None, "por_ibge": {}}
        try:
            doc = self.reclamacoes_doc(date_str)
        except AttributeError:      # dublê de teste sem reclamações
            return vazio
        if not doc or not doc.get("anos"):
            return vazio
        corrente = int(str(date_str)[:4])
        completos = [a for a in doc["anos"] if a < corrente]
        ano = max(completos) if completos else max(doc["anos"])
        por_ibge: dict[str, float] = {}
        for uf in sorted(set((doc.get("municipios_uf") or {}).values())):
            d_uf = self.reclamacoes_municipios_uf(date_str, uf)
            for ibge, mun in ((d_uf or {}).get("municipios") or {}).items():
                pop = mun.get("populacao")
                n = sum(i["reclamacoes"] for i in mun["itens"] if i["ano"] == ano)
                if pop and n >= MIN_RECLAMACOES_TAXA:           # abaixo disso a taxa é ruído (um caso a mais muda a ordem): sem taxa, não zero
                    por_ibge[ibge] = round(n * 100000 / pop, 2)
        return {"ano": ano, "por_ibge": por_ibge}

    def territorio_linhas(self, date_str: str) -> list[dict]:
        """Uma linha por município do IBGE com população, domicílios, acessos, penetração, mercado não visto e o PTT mais próximo (km em linha reta
        do centróide). Cacheada por data (as 2 mais recentes)."""
        if date_str not in self._territorio_linhas:
            doc = self.territorio_doc(date_str) or {}
            reclam = self._reclamacoes_100mil(date_str)
            linhas = []
            for ibge, m in (doc.get("municipios") or {}).items():
                ln = {"ibge": ibge, **m}
                if ibge in reclam["por_ibge"]:
                    ln["reclam_100mil"] = reclam["por_ibge"][ibge]
                    ln["reclam_ano"] = reclam["ano"]
                try:
                    fibra = (self.sici_municipio(date_str, ibge) or {}).get("fibra_pct")
                except AttributeError:      # dublê de teste sem SICI
                    fibra = None
                if fibra is not None:
                    ln["fibra_pct"] = fibra
                cen = self.municipio_centroide(ibge)
                p = self.ptt_mais_proximo(date_str, cen[0], cen[1]) if cen else None
                if p:
                    ln.update({"ptt_proximo": p["codigo"], "km_ptt": p["km"], "sem_ptt_proximo": p["km"] > self.RAIO_SEM_PTT_KM})
                linhas.append(ln)
            while len(self._territorio_linhas) >= 2:
                self._territorio_linhas.pop(next(iter(self._territorio_linhas)))
            self._territorio_linhas[date_str] = linhas
        return self._territorio_linhas[date_str]

    def perfil_municipio(self, date_str: str, ibge: str, blocos: Optional[set[str]] = None) -> Optional[dict]:
        """Perfil do município: `fixo` e `movel` (SICI), `centroide` e `ptts_proximos`. None se não há fixo nem móvel.

        `blocos` limita as seções (fixo, movel, ptts); None = todas. Os blocos mantêm a forma das rotas
        `/acessos/municipio/{ibge}` e `/acessos-movel/municipio/{ibge}`, sem o envelope repetido."""
        fixo = self.sici_municipio(date_str, ibge)
        movel = self.sici_movel_municipio(date_str, ibge)
        if not fixo and not movel:
            return None
        base = fixo or movel
        quer = lambda b: blocos is None or b in blocos  # noqa: E731
        out: dict = {"snapshot_date": date_str, "ibge": ibge, "nome": base.get("nome", ""), "uf": base.get("uf", "")}
        if quer("fixo"):
            m = self.sici_meta(date_str) or {}
            out["fixo"] = {"mes_referencia": m.get("mes_referencia"), **fixo} if fixo else None
        if quer("movel"):
            m = self.sici_movel_meta(date_str) or {}
            out["movel"] = {"mes_referencia": m.get("mes_referencia"), **movel} if movel else None
        cen = self.municipio_centroide(ibge)
        out["centroide"] = list(cen) if cen else None
        if quer("ptts"):
            out["ptts_proximos"] = self.ptts_proximos(date_str, cen[0], cen[1]) if cen else []
        return out


    # -------------------------------------------------------------------------
    # Perfil e resumo das UFs
    # -------------------------------------------------------------------------

    RAIO_SEM_PTT_KM = 100

    def asns_por_uf(self, date_str: str) -> dict[str, dict]:
        """UF → {quantidade, usuarios} dos ASNs BR (UF pela geo da organização); `usuarios` = soma do APNIC. Cacheado por data."""
        if date_str not in self._asns_por_uf:
            acc: dict[str, dict] = {}
            for r in self.query_table(date_str, "asns"):
                uf = r.get("uf")
                if not uf or not r.get("is_br"):
                    continue
                d = acc.setdefault(uf.upper(), {"quantidade": 0, "usuarios": 0})
                d["quantidade"] += 1
                d["usuarios"] += r.get("apnic_users") or 0
            self._asns_por_uf[date_str] = acc
        return self._asns_por_uf[date_str]

    def _municipios_da_uf(self, date_str: str, uf: str) -> list[dict]:
        """Municípios da UF com acessos fixos, operadores, HHI, fibra e o PTT mais próximo (km do centróide)."""
        out = []
        for ibge, m in self.sici_municipios(date_str).items():
            if (m.get("uf") or "").upper() != uf:
                continue
            cen = self.municipio_centroide(ibge)
            ptt = self.ptt_mais_proximo(date_str, cen[0], cen[1]) if cen else None
            out.append({"ibge": ibge, "nome": m.get("nome", ""), "acessos": m.get("acessos", 0),
                        "operadores": m.get("operadores_count", 0), "hhi": m.get("hhi", 0),
                        "fibra_pct": m.get("fibra_pct"),
                        "km_ptt": ptt["km"] if ptt else None, "ptt": ptt["nome"] if ptt else None,
                        "ptt_codigo": ptt["codigo"] if ptt else None})
        out.sort(key=lambda r: -r["acessos"])
        return out

    @staticmethod
    def _fibra_pct(municipios: list[dict], fixos: dict[str, dict]) -> Optional[float]:
        fibra = total = 0
        for m in municipios:
            f = fixos.get(m["ibge"], {})
            if "fibra" in f:
                fibra += f["fibra"]
                total += f.get("acessos", 0)
        return round(100 * fibra / total, 1) if total else None

    def perfil_uf(self, date_str: str, uf: str, blocos: Optional[set[str]] = None) -> dict:
        """Perfil da UF: totais (acessos, fibra, usuários), PTTs, municípios com a distância ao PTT, operadoras presentes na UF
        (`operadoras_presentes`, acessos na UF) e sediadas (`operadoras`, acessos no país), as 10 maiores de cada, e ASNs. `blocos`: ptts, municipios, operadoras (None = todos); os totais vêm sempre."""
        quer = lambda b: blocos is None or b in blocos  # noqa: E731
        municipios = self._municipios_da_uf(date_str, uf)
        fixos = self.sici_municipios(date_str)
        tem_sici = bool(fixos)                 # snapshot sem SICI: acessos e municípios são ausência, não zero
        tem_distancia = tem_sici and bool(self.ptts_pontos(date_str))
        asns = self.asns_por_uf(date_str).get(uf, {"quantidade": 0, "usuarios": 0})
        acessos = sum(m["acessos"] for m in municipios)
        sem_ptt = [m for m in municipios if m["km_ptt"] is not None and m["km_ptt"] > self.RAIO_SEM_PTT_KM]
        out: dict = {
            "snapshot_date": date_str, "uf": uf,
            "mes_referencia": (self.sici_meta(date_str) or {}).get("mes_referencia"),
            "totais": {
                "municipios": len(municipios) if tem_sici else None, "acessos": acessos if tem_sici else None,
                "fibra_pct": self._fibra_pct(municipios, fixos),
                "asns": asns["quantidade"], "usuarios": asns["usuarios"],
                "municipios_sem_ptt": len(sem_ptt) if tem_distancia else None,
                "acessos_sem_ptt": sum(m["acessos"] for m in sem_ptt) if tem_distancia else None,
                "raio_sem_ptt_km": self.RAIO_SEM_PTT_KM,
            },
        }
        if quer("ptts"):
            out["ixps"] = [e for e in self.ixp_index(date_str) if (e.get("uf") or "").upper() == uf]
        if quer("municipios"):
            out["municipios"] = municipios
        if quer("operadoras"):
            ops = [r for r in self.operadora_index(date_str) if r.get("ativo") and (r.get("uf_sede") or "").upper() == uf]
            ops.sort(key=lambda r: -(r.get("acessos") or 0))
            out["operadoras"] = {"total": len(ops), "items": ops[:10]}          # sediadas, acessos no país (como antes)
            presentes = self.operadoras_presentes_uf(date_str).get(uf, [])
            out["operadoras_presentes"] = {"total": len(presentes), "acessos": sum(r["acessos"] for r in presentes), "items": presentes[:10]}
        return out

    def operadoras_presentes_uf(self, date_str: str) -> dict[str, list[dict]]:
        """Por UF, os CNPJs com acesso fixo declarado ao SICI em algum município da UF, com os acessos **na UF** (`acessos`), a parcela
        sobre a soma da UF (`share`, %), os municípios da UF e os acessos no país (`acessos_brasil`); em ordem de acessos na UF (UF-E2: o
        bloco listava só as sediadas, com acessos nacionais). Um CNPJ, uma linha, mesmo com vários ASNs. Cacheado por data."""
        if date_str in self._operadoras_por_uf:
            return self._operadoras_por_uf[date_str]
        sici = (self._load_sici(date_str) or {}).get("cnpjs", {})
        sede = {r["cnpj"]: r for r in self.operadora_index(date_str)}
        por_uf: dict[str, dict[str, list[int]]] = {}
        for cnpj, agg in sici.items():
            for m in (agg.get("por_municipio") or {}).values():
                if m.get("acessos"):
                    u = (m.get("uf") or "").upper()
                    par = por_uf.setdefault(u, {}).setdefault(cnpj, [0, 0])
                    par[0] += m["acessos"]
                    par[1] += 1
        out: dict[str, list[dict]] = {}
        for u, ops in por_uf.items():
            total = sum(a for a, _ in ops.values()) or 1
            linhas = []
            for cnpj, (ac, nmun) in ops.items():
                agg, s = sici[cnpj], sede.get(cnpj) or {}
                linhas.append({"cnpj": cnpj, "empresa": agg.get("empresa") or s.get("razao_social") or "", "razao_social": s.get("razao_social", ""),
                               "uf_sede": s.get("uf_sede", ""), "acessos": ac, "share": round(100 * ac / total, 2), "municipios": nmun,
                               "acessos_brasil": agg.get("acessos", 0), "asns": agg.get("asns") or s.get("asns") or []})
            linhas.sort(key=lambda r: (-r["acessos"], r["cnpj"]))
            out[u] = linhas
        if len(self._operadoras_por_uf) >= 2:
            self._operadoras_por_uf.pop(next(iter(self._operadoras_por_uf)))
        self._operadoras_por_uf[date_str] = out
        return out

    def resumo_ufs(self, date_str: str) -> list[dict]:
        """Uma linha por UF (as 27): PTTs, municípios, acessos fixos, % de fibra, ASNs, usuários, municípios sem PTT e penetração (acessos ÷ domicílios projetados). Cacheado por data."""
        if date_str not in self._resumo_ufs:
            fixos = self.sici_municipios(date_str)
            por_uf: dict[str, list[dict]] = {}
            for ibge, m in fixos.items():
                por_uf.setdefault((m.get("uf") or "").upper(), []).append({"ibge": ibge, "acessos": m.get("acessos", 0)})
            # PTTs da UF: os do snapshot, com ou sem coleta (a mesma lista da distância, `ptts_pontos`); `ptts_com_coleta` à parte.
            ptts_uf: dict[str, int] = {}
            ptts_coleta_uf: dict[str, int] = {}
            for e in self.ixp_index(date_str):
                if e.get("uf"):
                    u = e["uf"].upper()
                    ptts_uf[u] = ptts_uf.get(u, 0) + 1
                    ptts_coleta_uf[u] = ptts_coleta_uf.get(u, 0) + (e.get("status") != "missing")
            tem_sici = bool(fixos)                 # snapshot sem SICI: acessos e municípios são ausência, não zero
            pontos = self.ptts_pontos(date_str)
            asns = self.asns_por_uf(date_str)
            # Penetração por UF: acessos fixos ÷ domicílios projetados, só dos municípios que têm domicílios no produto de território.
            dom_uf: dict[str, int] = {}
            acessos_dom_uf: dict[str, int] = {}
            try:
                for t in self.territorio_linhas(date_str) or []:
                    if t.get("domicilios_projetados"):
                        u = (t.get("uf") or "").upper()
                        dom_uf[u] = dom_uf.get(u, 0) + int(t["domicilios_projetados"])
                        acessos_dom_uf[u] = acessos_dom_uf.get(u, 0) + int(t.get("acessos") or 0)
            except Exception:  # snapshot sem o produto de território: a penetração sai nula
                pass
            linhas = []
            for uf in sorted(set(por_uf) | set(ptts_uf) | set(asns)):
                if len(uf) != 2:
                    continue
                muns = por_uf.get(uf, [])
                sem = 0
                for m in muns:
                    cen = self.municipio_centroide(m["ibge"])
                    if cen and pontos and self.ptt_mais_proximo(date_str, cen[0], cen[1])["km"] > self.RAIO_SEM_PTT_KM:
                        sem += 1
                linhas.append({
                    "uf": uf, "ptts": ptts_uf.get(uf, 0), "ptts_com_coleta": ptts_coleta_uf.get(uf, 0),
                    "municipios": len(muns) if tem_sici else None,
                    "acessos": sum(m["acessos"] for m in muns) if tem_sici else None, "fibra_pct": self._fibra_pct(muns, fixos),
                    "asns": asns.get(uf, {}).get("quantidade", 0), "usuarios": asns.get(uf, {}).get("usuarios", 0),
                    "municipios_sem_ptt": sem if tem_sici and pontos else None,
                    "domicilios": dom_uf.get(uf) or None,
                    "penetracao": round(acessos_dom_uf[uf] / dom_uf[uf], 4) if dom_uf.get(uf) else None,
                })
            self._resumo_ufs[date_str] = linhas
        return self._resumo_ufs[date_str]

    # -------------------------------------------------------------------------
    # SICI móvel — Acessos de telefonia móvel (SMP) declarados à Anatel
    # -------------------------------------------------------------------------
