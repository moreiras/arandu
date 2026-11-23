# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estabilidade BGP: série semanal, histórico resumido, visão geral e documento por AS (index compacto em memória).

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import Optional


def _data_ou_none(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


class BgpEstabilidadeService:
    def __init__(self, store):
        self._s = store
        self._bgp_horaria_cache: dict[str, dict] = {}
        self._bgp_idx: dict[str, dict] = {}
        self._bgp_visao: dict[str, dict] = {}
        self._bgp_carga: dict[tuple, dict] = {}

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def bgp_stability(self, date_str: str) -> Optional[dict]:
        """Análise de estabilidade de updates BGP — ASes BR ruidosos."""
        return self._docs.bgp_stability(date_str)

    def bgp_stability_history(self, date_str: str, weeks: int = 6) -> list[dict]:
        """Análise de estabilidade BGP dos snapshots publicados nas últimas
        `weeks` semanas de calendário até (e incluindo) `date_str`, em ordem
        cronológica crescente.

        A janela é por tempo, não por contagem: se houver lacunas na série de
        snapshots, um snapshot muito mais antigo que `weeks` semanas não entra
        só porque é "o próximo mais recente disponível". Snapshots sem
        bgp_stability.json são simplesmente omitidos — o chamador não precisa
        preencher lacunas.
        """
        # Um snapshot por semana: com coleta diária a janela por data traria 7 cópias (quase iguais) de cada semana —
        # 27 MB e ~1 min no primeiro pedido (1.4.2.1).
        candidates = self.bgp_stability_datas_semanais(date_str, weeks)
        ja_em_cache = self._docs.bgp_stability_datas_em_memoria()
        history = []
        for d in candidates:
            data = self.bgp_stability(d)
            if data is not None:
                history.append({"date": d, "data": data})
        # As semanas antigas só existem para esta resposta: não ficam retidas (cada JSON parseado ocupa centenas de MiB; as de
        # `/bgp-stability/asn` usam a forma compacta). O `date_str` e o que já estava em cache ficam como estavam.
        for d in candidates:
            if d != date_str and d not in ja_em_cache:
                self._docs.soltar_bgp_stability(d)
        return history

    def _bgp_horaria(self, date_str: str) -> Optional[dict]:
        """Séries horárias de TODOS os ASes de um snapshot em forma compacta: `{timestamps, series: {asn: {ann, wd, attr_upd}}}`
        com `array('I')` (≈16 MB por snapshot, contra ~120 MB das listas do JSON). Lê o arquivo sem retê-lo (só o `latest` já fica
        no `DocumentosRepo` por outras rotas); cacheado em até 12 datas. Passo 1.4.2.1."""
        cache = self._bgp_horaria_cache
        if date_str in cache:
            return cache[date_str]
        doc = self._docs.bgp_stability_em_memoria(date_str)
        if doc is None:
            doc = self._read_json(self._pub(date_str) / "bgp_stability.json")
        if not doc:
            return None
        from array import array
        series = {}
        # volume da semana por AS e família (anúncios + retiradas + mudanças de atributo) e prefixos com update: alguns inteiros por AS,
        # lidos nesta mesma passagem para `bgp_stability_carga` não precisar reabrir o documento de cada semana
        carga: dict[int, tuple] = {}
        for a in doc.get("as_stability", []):
            h = a.get("hourly")
            if h:
                series[a["asn"]] = {k: array("I", v) for k, v in h.items()}
            p = a.get("period") or {}
            if "announcements_v6" in p or "announcements_v4" in p:
                carga[a["asn"]] = (
                    a.get("name") or "",
                    sum(p.get(k) or 0 for k in ("announcements_v6", "withdrawals_v6", "attribute_updates_v6")),
                    sum(p.get(k) or 0 for k in ("announcements_v4", "withdrawals_v4", "attribute_updates_v4")),
                    a.get("prefix_count_v6") or 0, a.get("prefix_count_v4") or 0,
                )
        per = doc.get("period") or {}
        out = {"timestamps": (doc.get("hourly_global") or {}).get("timestamps", []), "series": series,
               "global": doc.get("hourly_global") or {}, "carga": carga,
               "periodo": {k: per.get(k) for k in ("start", "end", "days", "collector", "files_missing")}}
        if len(cache) >= 12:
            cache.pop(next(iter(cache)))
        cache[date_str] = out
        return out

    def bgp_stability_datas_semanais(self, date_str: str, weeks: int = 6) -> list[str]:
        """Um snapshot por semana, do mais antigo ao `date_str`: cada `bgp_stability.json` cobre 7 dias, então com coleta diária
        usar todos os snapshots da janela repete a mesma semana 7 vezes. Para cada semana (`date_str` − 7k dias) vale o snapshot
        daquele dia ou, na falta, o mais recente até 3 dias antes."""
        existentes = set(self.list_snapshots())
        alvo0 = date.fromisoformat(date_str)
        datas = []
        for k in range(weeks):
            alvo = alvo0 - timedelta(weeks=k)
            achada = next((c for c in ((alvo - timedelta(days=i)).isoformat() for i in range(4)) if c in existentes), None)
            if achada and achada not in datas:
                datas.append(achada)
        return sorted(datas)

    def aquecer_estabilidade(self, date_str: str, weeks: int = 6) -> int:
        """Monta as séries compactas das semanas de `bgp_stability_asn` (bloqueante; rode em thread). Devolve quantas semanas."""
        n = 0
        for d in self.bgp_stability_datas_semanais(date_str, weeks):
            if self._bgp_horaria(d) is not None:
                n += 1
        return n

    def bgp_stability_historico_resumo(self, date_str: str, weeks: int = 6) -> list[dict]:
        """Como `bgp_stability_history`, mas só com o `hourly_global` de cada semana (o que o gráfico de atividade da página `/bgp`
        usa): alguns KB em vez de 13,5 MB comprimidos. Sai das séries compactas, aquecidas ao subir."""
        out = []
        for d in self.bgp_stability_datas_semanais(date_str, weeks):
            h = self._bgp_horaria(d)
            if h and h.get("global"):
                out.append({"date": d, "data": {"hourly_global": h["global"]}})
        return out

    def bgp_stability_carga(self, date_str: str, weeks: int = 6, top: int = 10) -> Optional[dict]:
        """Os `top` ASes com mais updates BGP (anúncios + retiradas + mudanças de atributo) somados nas últimas `weeks` semanas, por
        família, com o volume de cada semana. É a carga na tabela, em número absoluto: não é a métrica por prefixo da tabela de
        estabilidade. Sai das formas compactas de `_bgp_horaria` (as mesmas semanas do gráfico de atividade). None se nenhuma semana
        da janela tem a análise."""
        chave = (date_str, weeks, top)
        if chave in self._bgp_carga:
            return self._bgp_carga[chave]
        semanas: list[dict] = []
        cargas: list[dict] = []
        anterior_fim: Optional[date] = None
        for d in self.bgp_stability_datas_semanais(date_str, weeks):
            h = self._bgp_horaria(d)
            if not h or h.get("carga") is None:
                continue
            per = h.get("periodo") or {}
            inicio, fim = _data_ou_none(per.get("start")), _data_ou_none(per.get("end"))
            # `end` é exclusivo (a janela é [start, start + 7 dias)). Semanas escolhidas com folga (até 3 dias): a janela real pode se
            # sobrepor à anterior ou deixar dias de fora
            sobreposicao = lacuna = 0
            if anterior_fim and inicio:
                delta = (inicio - anterior_fim).days
                sobreposicao, lacuna = max(0, -delta), max(0, delta)
            anterior_fim = fim or anterior_fim
            c = h["carga"]
            semanas.append({"date": d, "inicio": per.get("start"),
                            "ultimo_dia": (fim - timedelta(days=1)).isoformat() if fim else None, "dias": per.get("days"),
                            "coletor": per.get("collector"), "arquivos_faltando": per.get("files_missing"),
                            "sobreposicao_dias": sobreposicao, "lacuna_dias": lacuna,
                            "total_v6": sum(v[1] for v in c.values()), "total_v4": sum(v[2] for v in c.values())})
            cargas.append(c)
        if not semanas:
            return None
        nomes: dict[int, str] = {}
        for c in cargas:                                   # o nome mais recente que houver
            for asn, v in c.items():
                if v[0]:
                    nomes[asn] = v[0]
        out: dict = {"snapshot_date": date_str, "weeks": weeks, "top": top, "coletor": semanas[-1]["coletor"], "semanas": semanas}
        for fam, i_upd, i_pfx in (("v6", 1, 3), ("v4", 2, 4)):
            totais: dict[int, int] = {}
            for c in cargas:
                for asn, v in c.items():
                    if v[i_upd]:
                        totais[asn] = totais.get(asn, 0) + v[i_upd]
            soma = sum(totais.values())
            maiores = sorted(totais.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
            # AS ausente da análise de uma semana não teve update visto naquela semana: 0, não falta de dado
            ases = [{"asn": asn, "nome": nomes.get(asn, ""), "total": total,
                     "semanas": [(c.get(asn) or (None, 0, 0, 0, 0))[i_upd] for c in cargas],
                     "prefixos": [(c.get(asn) or (None, 0, 0, 0, 0))[i_pfx] for c in cargas]}
                    for asn, total in maiores]
            soma_top = sum(a["total"] for a in ases)
            out[fam] = {"total": soma, "total_top": soma_top,
                        "parcela_top_pct": round(100 * soma_top / soma, 1) if soma else None,
                        "parcela_top_semana_pct": [round(100 * sum(a["semanas"][k] for a in ases) / t, 1) if t else None
                                                   for k, t in enumerate(s[f"total_{fam}"] for s in semanas)],
                        "ases": ases}
        if len(self._bgp_carga) >= 8:
            self._bgp_carga.pop(next(iter(self._bgp_carga)))
        self._bgp_carga[chave] = out
        return out

    _BGP_PESADOS = ("hourly", "top_prefixes")   # séries por AS: ficam em /bgp-stability/asn/{asn}

    # colunas ordenáveis da tabela de estabilidade (StabilitySection.tsx): valor ausente conta como 0

    _BGP_ORDENS = {

        "rank": lambda a: a.get("rank") or 0,

        "epppd": lambda a: (a.get("period") or {}).get("events_per_prefix_per_day") or 0,

        "epppd_v6": lambda a: (a.get("period") or {}).get("events_per_prefix_per_day_v6") or 0,

        "epppd_v4": lambda a: (a.get("period") or {}).get("events_per_prefix_per_day_v4") or 0,

        "flap": lambda a: (a.get("period") or {}).get("flapping_prefixes") or 0,

    }

    def bgp_stability_visao_geral(self, date_str: str, top: int = 10) -> Optional[dict]:
        """O que a seção de estabilidade da página `/bgp` mostra, sem o documento de ~46 MB: período, distribuição, estatísticas,
        atividade global, a contagem de ASes por categoria de ruído e por severidade e os `top` ASes mais ruidosos (por rank, sem
        as séries horárias nem os prefixos). Cacheado por data (4). Passo 1.4.2.5."""
        cache = self._bgp_visao
        if date_str in cache:
            return cache[date_str]
        doc = self.bgp_stability(date_str)
        if doc is None:
            return None
        ases = doc.get("as_stability", [])
        categorias = {"estavel": 0, "inquieto": 0, "barulhento": 0, "critico": 0}
        severidades: dict[str, int] = {}
        for a in ases:
            c = a.get("noise_category") or "estavel"
            categorias[c] = categorias.get(c, 0) + 1
            severidades[a.get("severity", "")] = severidades.get(a.get("severity", ""), 0) + 1
        maiores = sorted(ases, key=lambda a: a.get("rank", 0))[:top]
        # Tabela recolhida da página: as `top` primeiras linhas da MESMA ordem que "Ver todos" daria (severidade média ou maior), para cada
        # coluna e sentido. Ordenar só as 10 linhas da visão geral escondia, por exemplo, os mais instáveis em IPv4.
        medios = sorted((a for a in ases if a.get("severity") in ("critical", "high", "medium")), key=lambda a: a.get("rank", 0))
        ordens: dict[str, dict[str, list]] = {}
        escolhidos: dict = {a.get("asn"): a for a in maiores}
        for chave, valor in self._BGP_ORDENS.items():
            cresc = sorted(medios, key=valor)                          # estável: empate fica na ordem de rank, como no navegador
            decr = sorted(medios, key=valor, reverse=True)
            ordens[chave] = {"asc": [a.get("asn") for a in cresc[:top]], "desc": [a.get("asn") for a in decr[:top]]}
            for a in cresc[:top] + decr[:top]:
                escolhidos.setdefault(a.get("asn"), a)
        out = {
            "snapshot_date": date_str,
            "period": doc.get("period"), "distribution": doc.get("distribution"), "epppd_stats": doc.get("epppd_stats"),
            "hourly_global": doc.get("hourly_global"), "published_at": doc.get("published_at"),
            "categorias": {**categorias, "total": len(ases)},
            "severidades": severidades,
            "medio_ou_maior": sum(severidades.get(k, 0) for k in ("critical", "high", "medium")),
            "as_stability": [{k: v for k, v in a.items() if k not in self._BGP_PESADOS} for a in maiores],
            # ASes das `ordens` que não estão em `as_stability` (mesmo formato enxuto); `ordens[coluna][asc|desc]` = ASNs, na ordem
            "as_stability_ordens": [{k: v for k, v in a.items() if k not in self._BGP_PESADOS}
                                    for asn, a in escolhidos.items() if asn not in {m.get("asn") for m in maiores}],
            "ordens": ordens,
        }
        if len(cache) >= 4:
            cache.pop(next(iter(cache)))
        cache[date_str] = out
        return out

    def bgp_stability_asn(self, date_str: str, asn: int, weeks: int = 6) -> Optional[dict]:
        """Tudo o que a página de um AS usa da estabilidade BGP, sem baixar o documento inteiro (46 MB) nem o histórico de todos
        os ASes (27 MB): o `stability` do AS (snapshot ativo), `epppd_stats`, os `timestamps` da semana, o `diagnosis` aprofundado e as
        séries horárias do AS nas últimas `weeks` semanas. None se o snapshot não tem a análise."""
        doc = self.bgp_stability(date_str)
        if doc is None:
            return None
        idx = self._bgp_idx.get(date_str)
        if idx is None:
            idx = {a.get("asn"): a for a in doc.get("as_stability", [])}
            if len(self._bgp_idx) >= 4:
                self._bgp_idx.pop(next(iter(self._bgp_idx)))
            self._bgp_idx[date_str] = idx
        deep = self.bgp_stability_deep(date_str) or {}
        diag = next((d for d in deep.get("as_diagnosis", []) if d.get("asn") == asn), None)
        semanas = []
        for d in self.bgp_stability_datas_semanais(date_str, weeks):
            h = self._bgp_horaria(d)
            serie = (h or {}).get("series", {}).get(asn)
            if serie:
                semanas.append({"date": d, "timestamps": h["timestamps"], "series": {k: list(v) for k, v in serie.items()}})
        return {"snapshot_date": date_str, "asn": asn, "stability": idx.get(asn),
                "epppd_stats": doc.get("epppd_stats"), "timestamps": (doc.get("hourly_global") or {}).get("timestamps", []),
                "diagnosis": diag, "weeks": semanas}

    def bgp_stability_deep(self, date_str: str) -> Optional[dict]:
        """Diagnóstico aprofundado dos ASes mais ruidosos (etapa 2)."""
        return self._docs.bgp_stability_deep(date_str)

    # -------------------------------------------------------------------------
    # IXPs
    # -------------------------------------------------------------------------
