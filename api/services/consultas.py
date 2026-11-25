# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consulta composável (query/colunar), resolução de operadores e lugares e a tabela de organizações geolocalizadas.

Serviço sobre o `Store`: guarda os caches e a lógica deste assunto; o que lê de outros artefatos pede ao `Store` por
`__getattr__`, então o `Store` segue sendo a fachada e delega aqui os métodos públicos.
"""
from __future__ import annotations

import threading

import json
from typing import Optional

from cachetools import LRUCache

from api.services import decix_rs as _decix_rs
from core.cpf import mascarar_cpf_em


class ConsultasService:
    def __init__(self, store):
        self._s = store
        # Tabelas colunares abertas por mmap ("{date}/{nome}"): só as 3 últimas; os códigos ficam fora do heap
        self._colunares: dict[str, object] = {}
        self._colunares_lock = threading.Lock()
        # Cache: date_str → {int asn: {uf, city, cnpj, lat, lon}} de geo_orgs.json.gz
        self._geo_orgs_cache: dict[str, dict[int, dict]] = {}
        # Resultados de `query` por (data, collection, corpo): snapshot publicado é imutável, então o resultado nunca envelhece. A home faz 5
        # POST /query iguais a cada visita e cada um custava 0,5–0,8 s sem cache (POST não passa pelo cache de GET do nginx) — 1.4.7.1.
        self._resultados = LRUCache(maxsize=self.RESULTADOS_MAX)
        self._resultados_lock = threading.Lock()

    RESULTADOS_MAX = 256
    RESULTADO_MAX_LINHAS = 500          # respostas maiores não entram: a memória do cache é por entrada, não por byte

    def __getattr__(self, nome):
        if nome == "_s":
            raise AttributeError(nome)
        return getattr(self._s, nome)

    def _load_geo_orgs(self, date_str: str) -> dict[int, dict]:
        """{int asn: {...campos do CNPJ + geo}} de geo_orgs.json.gz. Cacheado.

        Inclui classificação (cnae/porte/natureza), identidade (razão social/nome
        fantasia/cnpj_root), contatos (email/telefone/endereço) e coordenadas.
        """
        if date_str in self._geo_orgs_cache:
            return self._geo_orgs_cache[date_str]
        path = self.base / "normalized" / date_str / "summary" / "geo_orgs.json.gz"
        # normalized/ não passa pela máscara da publicação (core.cpf.mascarar_snapshot): a razão social de EI/MEI traz o CPF inteiro e vai
        # para a resposta (nome alternativo do AS, perfis). Um arquivo por data, guardado em memória.
        data = mascarar_cpf_em(self._read_json_gz(path) or {})
        orgs = data.get("orgs", {}) if isinstance(data, dict) else {}
        out: dict[int, dict] = {}
        for key, org in orgs.items():
            try:
                asn = int(key)
            except (TypeError, ValueError):
                continue
            lat, lon = org.get("lat"), org.get("lon")
            cnpj = org.get("cnpj") or ""
            phone = org.get("ddd_telefone_1") or org.get("ddd_telefone_2") or None
            # Endereço legível a partir dos componentes do CNPJ.
            parts = [
                org.get("descricao_tipo_de_logradouro"), org.get("logradouro"),
                org.get("numero"), org.get("complemento"), org.get("bairro"),
            ]
            address = ", ".join(str(p) for p in parts if p) or None
            out[asn] = {
                "uf": org.get("uf"),
                "city": org.get("municipio"),
                "cnpj": cnpj or None,
                "cnpj_root": cnpj[:8] if len(cnpj) >= 8 else None,
                "razao_social": org.get("razao_social") or org.get("name"),
                "nome_fantasia": org.get("nome_fantasia") or None,
                "cnae": org.get("cnae_fiscal_descricao"),
                "cnae_code": org.get("cnae_fiscal"),
                "porte": org.get("porte"),
                "natureza_juridica": org.get("natureza_juridica"),
                "email": (org.get("email") or "").strip() or None,
                "phone": phone,
                "address": address,
                "bairro": org.get("bairro") or None,
                "cep": org.get("cep") or None,
                "lat": float(lat) if lat is not None else None,
                "lon": float(lon) if lon is not None else None,
            }
        self._geo_orgs_cache[date_str] = out
        return out

    #: `series_asn` guarda as N datas mais recentes de ASN BR (~9 mil linhas por data); séries longas: /history/asns/{asn}
    SERIES_ASN_DATAS = 8

    def _tabela_historico(self, collection: str) -> list[dict]:
        from api.repos.historico import HistoricoRepo
        from api.services.historico import _INFERIDOS

        repo = getattr(self, "_historico", None)
        if repo is None:
            repo = self._historico = HistoricoRepo(self.base)
        if collection == "series_asn":
            return repo.series_asn_br(self.SERIES_ASN_DATAS)
        linhas = []
        for e in repo.todos_eventos():
            d = e.get("detalhe") or {}
            linhas.append({**{k: v for k, v in e.items() if k != "detalhe"}, "natureza": "inferido" if e["tipo"] in _INFERIDOS else "observado",
                           "ixp": d.get("ixp"), "servico": d.get("servico"), "rpki": d.get("rpki"), "provedor": d.get("provedor")})
        return linhas

    def query_table(self, date_str: str, collection: str) -> list[dict]:
        """Monta (e cacheia) a tabela consultável de uma collection.

        Para `asns`, faz join em memória do índice compacto com geo_orgs (uf/city/
        region/cnpj/lat/lon) e com asn_ix_presence (campos virtuais ixps_direct/
        ixps_origin). As demais collections vêm direto dos índices publicados.
        """
        from api import query as _q

        if collection not in _q.COLLECTIONS:
            raise _q.QueryError(
                f"collection inválida: '{collection}'. Use: {', '.join(_q.COLLECTIONS)}"
            )
        if collection in ("eventos", "series_asn"):
            return self._tabela_historico(collection)           # camada de histórico: não depende do snapshot e não fica em _query_tables
        cache_key = f"{date_str}/{collection}"
        if cache_key in self._query_tables:
            return self._query_tables[cache_key]

        if collection == "asns":
            geo = self._load_geo_orgs(date_str)
            pres = self.asn_ix_presence(date_str).get("asns", {})
            rows: list[dict] = []
            # Campos PII não devem ser expostos pela query layer pública — o endpoint
            # protegido /asns/{asn}/contacts é o único caminho legítimo para esses dados.
            _PII = {"email", "phone", "address", "bairro", "cep"}
            for base in self.asn_index(date_str):
                asn = base.get("asn")
                g = geo.get(asn, {})
                uf = g.get("uf")
                p = pres.get(str(asn), {})
                rows.append({
                    **base,
                    **{k: v for k, v in g.items() if k not in _PII},
                    "region": _q.REGION_BY_UF.get(uf) if uf else None,
                    "ixps_direct": p.get("m", []),
                    "ixps_origin": p.get("o", []),
                })
        elif collection == "ixps":
            rows = list(self.ixp_index(date_str))
        elif collection == "external_ixps":
            idx = self.external_ixp_index(date_str) or {}
            rows = [
                {k: v for k, v in e.items() if k != "members"}
                for e in (idx.get("ixps", []) if isinstance(idx, dict) else [])
            ]
            rows = _decix_rs.linhas_query(rows, self.decix_rs_doc(date_str))
        elif collection == "cdns":
            data = self.cdn_presence(date_str) or {}
            rows = list(data.get("cdns", [])) if isinstance(data, dict) else []
        elif collection == "prefixes":
            gj = self.geo_map(date_str, "prefixes") or {}
            rows = []
            for ft in gj.get("features", []):
                props = ft.get("properties") or {}
                coords = (ft.get("geometry") or {}).get("coordinates") or [None, None]
                rows.append({**props, "lon": coords[0],
                             "lat": coords[1] if len(coords) > 1 else None})
        elif collection == "global_prefixes":
            gj = self.geo_map(date_str, "global_prefixes") or {}
            rows = []
            for ft in gj.get("features", []):
                props = ft.get("properties") or {}
                coords = (ft.get("geometry") or {}).get("coordinates") or [None, None]
                rows.append({**props, "lon": coords[0],
                             "lat": coords[1] if len(coords) > 1 else None})
        elif collection == "scms":
            rows = list(self.scm_index(date_str))
        elif collection == "operadoras":
            rows = self.operadora_index(date_str)
        elif collection == "acessos_municipio":
            rows = self.acessos_municipio_index(date_str)
        elif collection in ("smps", "stfcs", "seacs"):
            rows = list(getattr(self, f"{collection[:-1]}_index")(date_str))
        elif collection == "operadoras_movel":
            rows = self.operadora_movel_index(date_str)
        elif collection == "acessos_movel_municipio":
            rows = self.acessos_movel_municipio_index(date_str)
        elif collection == "socios":
            rows = self.socios_grupos_index(date_str)
        elif collection == "municipios":
            rows = self.territorio_linhas(date_str)
        elif collection == "cetic_indicadores":
            from api.services.cetic import linhas as _linhas_cetic
            rows = _linhas_cetic([d for d in (self.cetic_doc(date_str, p) for p in ("domicilios", "provedores")) if d])
        elif collection == "cetic_estimativas_uf":
            from api.services.cetic import linhas_uf as _linhas_cetic_uf
            rows = _linhas_cetic_uf(self.cetic_uf_doc(date_str))
        elif collection == "transferencias_ipv4":
            from api.services.ipv4 import linhas_transferencias as _lt
            rows = _lt(self.ipv4_transferencias_doc(date_str))
        elif collection == "subasignacoes_ipv4":
            from api.services.ipv4 import linhas_subasignacoes as _lsub
            rows = _lsub(self.ipv4_subasig_doc(date_str))
        elif collection == "espaco_ipv4":
            from api.services.ipv4 import linhas_espaco as _lesp
            rows = _lesp(self.ipv4_espaco_doc(date_str))
        elif collection == "uso_por_terceiros_ipv4":
            from api.services.ipv4 import linhas_uso as _luso
            rows = _luso(self.ipv4_uso_doc(date_str))
        elif collection == "recuperacao_ipv4":
            from api.services.ipv4 import linhas_recuperacao as _lr
            rows = _lr(self.ipv4_recuperacao_doc(date_str))
        elif collection == "eventos_bloco":
            from api.services.ipv4 import linhas_eventos as _le
            rows = _le(self.ipv4_eventos_br(), date_str)
        elif collection == "erbs_municipio":
            from api.services.erbs import linhas as _linhas_erbs
            rows = _linhas_erbs(self.erbs_doc(date_str))
        elif collection == "prontidao_agregado":
            from api.services.prontidao import linhas as _linhas_pr
            rows = _linhas_pr(self.prontidao_doc(date_str))
        elif collection == "prontidao_asn":
            from api.services.prontidao import lista_nominal_habilitada, linhas_asn as _linhas_pa
            if not lista_nominal_habilitada():
                from api.query import QueryError
                raise QueryError("A coleção prontidao_asn ainda não foi liberada: aguarda a aprovação da metodologia (use prontidao_agregado).")
            rows = _linhas_pa(self.prontidao_doc(date_str), self.asn_names(date_str))
        elif collection == "fust_municipio":
            from api.services.fust import linhas as _linhas_fust
            rows = _linhas_fust(self.fust_doc(date_str))
        elif collection == "multas_empresa":
            from api.services.regulatorio import linhas_multas as _lm
            rows = _lm(self.multas_doc(date_str))
        elif collection == "qualidade_uf":
            from api.services.qualidade import linhas_uf as _lqu
            rows = _lqu(self.rqual_doc(date_str))
        elif collection == "consumidor_marca":
            from api.services.consumidor import linhas_marcas as _lcm
            rows = _lcm(self.consumidor_doc(date_str))
        elif collection == "reclamacoes_marca":
            from api.services.qualidade import linhas_marcas as _lrm
            rows = _lrm(self.reclamacoes_doc(date_str))
        elif collection == "faixas_espectro":
            from api.services.regulatorio import linhas_faixas as _lf
            rows = _lf(self.faixas_doc(date_str))
        elif collection == "satelites_direitos":
            from api.services.regulatorio import linhas_satelites as _ls
            rows = _ls(self.satelites_doc(date_str))
        elif collection == "demanda_oferta":
            from api.services.demanda_oferta import linhas as _linhas_do
            rows = _linhas_do(self.demanda_oferta_doc(date_str))
        elif collection == "rs_sessoes":
            from api.services.route_servers import linhas as _linhas_rs
            rows = _linhas_rs(self.route_servers_asns_doc(date_str), self.route_servers_ixps_doc(date_str))
        elif collection in ("rs_communities", "rs_filtradas"):
            from api.services.rs_policy import linhas as _linhas_pol
            rows = _linhas_pol(self.rs_policy_linhas_doc(date_str), collection)
        elif collection == "transito_uf":
            from api.services.transito import linhas_uf as _linhas_tuf
            rows = _linhas_tuf(self.transito_ufs_doc(date_str))
        elif collection == "transito_asn":
            from api.services.transito import linhas_asn as _linhas_tasn
            rows = _linhas_tasn(self.transito_asns_doc(date_str))
        elif collection == "bloqueios_asn":
            from api.services.bloqueios import linhas as _linhas_blq
            rows = _linhas_blq(self.bloqueios_doc(date_str))
        elif collection == "organizacoes_asn":
            from api.services.as2org import linhas as _linhas_org
            rows = _linhas_org(self.as2org_doc(date_str), self.abuso_doc(date_str))
        elif collection in ("facilities", "facilidades_rede", "redes_peering"):
            from api.services import instalacoes as _inst
            if collection == "facilities":
                rows = _inst.linhas_facilities(self.instalacoes_doc(date_str))
            elif collection == "facilidades_rede":
                rows = _inst.linhas_facilidades_rede(self.instalacoes_doc(date_str), self.vinculos_instalacoes_doc(date_str))
            else:
                rows = _inst.linhas_redes_peering(self.atributos_rede_doc(date_str), self.vinculos_instalacoes_doc(date_str), self.portas_externas_doc(date_str))
        elif collection == "seguranca_asn":
            from api.services.seguranca import linhas as _linhas_seg
            rows = _linhas_seg(self.seguranca_doc(date_str))
        elif collection == "indicadores_operadora":
            ind = self.sici_indicadores(date_str) or {}
            rows = [{"cnpj": c, "empresa": o["empresa"], "uf": o["uf"], "acessos": o["acessos"], "share_br": o["share_br"], "posicao_br": o["posicao_br"],
                     **{f"{k}_{x}": o[k][x] for k in ("var_mm", "var_aa") if k in o for x in ("abs", "pct")},
                     "meses_declinio": o["meses_declinio"], "em_declinio": o["em_declinio"], "mes_referencia": ind["mes_referencia"]}
                    for c, o in (ind.get("operadoras") or {}).items()]
        elif collection == "omissao_sici":
            om = self.omissao_sici(date_str) or {}
            rows = [{"cnpj": c, **v, "mes_referencia": om["mes_referencia"]} for c, v in (om.get("itens") or {}).items()]
        else:  # pragma: no cover — guard acima já cobre
            rows = []

        if not rows and not (self._pub(date_str) / "manifest.json").exists():
            return rows                                         # data sem snapshot não fica no cache (seria uma entrada por data inventada)
        self._query_tables[cache_key] = rows
        return rows

    #: coleções cujas linhas são prefixos: a posição individual (lat/lon/cidade) não sai, só entra no filtro `near`
    COLECOES_SEM_POSICAO = ("prefixes", "global_prefixes")

    #: coleções com tabela colunar publicada ao lado do GeoJSON (`maps/<nome>.col`)
    COLECOES_COLUNARES = ("global_prefixes",)
    COLUNARES_ABERTAS = 3

    def colunar(self, date_str: str, nome: str):
        """`TabelaColunar` de `maps/{nome}.col` do snapshot, ou None se não foi publicada (snapshot antigo): quem chama cai
        no caminho por linhas, mais lento. Aberta por mmap e guardada para as `COLUNARES_ABERTAS` datas mais recentes."""
        from core import colunar as _c

        chave = f"{date_str}/{nome}"
        with self._colunares_lock:
            if chave in self._colunares:
                return self._colunares[chave]
            caminho = self._pub(date_str) / "maps" / f"{nome}{_c.EXTENSAO}"
            tab = _c.aberta_ou_none(caminho) if caminho.exists() else None
            if tab is None:
                return None
            while len(self._colunares) >= self.COLUNARES_ABERTAS:
                self._colunares.pop(next(iter(self._colunares)))     # a mais antiga; o GC fecha o mmap
            self._colunares[chave] = tab
            return tab

    def query(self, date_str: str, collection: str, body: dict) -> dict:
        """`_executar` com cache de resultado. O dict devolvido é compartilhado: quem chama não o altera (a rota serializa, o MCP devolve)."""
        try:
            chave = (date_str, collection, json.dumps(body or {}, sort_keys=True, default=str))
        except (TypeError, ValueError):
            return self._executar(date_str, collection, body)
        with self._resultados_lock:
            hit = self._resultados.get(chave)
        if hit is not None:
            return hit
        resultado = self._executar(date_str, collection, body)
        linhas = len(resultado.get("items") or ()) + len(resultado.get("groups") or ())
        if linhas <= self.RESULTADO_MAX_LINHAS:
            with self._resultados_lock:
                self._resultados[chave] = resultado
        return resultado

    def _executar(self, date_str: str, collection: str, body: dict) -> dict:
        """Executa uma consulta (filtro/seleção/ordenação/agregação) sobre uma collection.

        Suporta a conveniência `near` no corpo: `{"point":[lat,lon]|"ixp":code|
        "place":nome, "radius_km":N}` — resolvida para centro(s) e aplicada como
        predicado geográfico `within_radius` (AND com o filtro existente).
        """
        from api import query as _q
        from core.geoip import CAMPOS_POSICAO, sem_posicao

        body = dict(body or {})
        if collection in self.COLECOES_SEM_POSICAO:
            proibido = sorted({r for r in _q._field_refs(body) if r in CAMPOS_POSICAO})
            if proibido:
                raise _q.QueryError(
                    f"{', '.join(proibido)}: a posição de cada prefixo não é servida em '{collection}'. "
                    "Use `near` para buscar prefixos perto de um lugar, ou agregue por `uf`/`country`.")
        near = body.pop("near", None)
        tab = self.colunar(date_str, collection) if collection in self.COLECOES_COLUNARES else None
        rows = [] if tab is not None else self.query_table(date_str, collection)

        # Valida campos/enums com mensagem que ensina (campo errado → vazio silencioso).
        _q.validate(collection, body, (tab.linha(0) if tab.n else None) if tab is not None else (rows[0] if rows else None))
        if tab is None:
            _q.validar_valores_de_lista(rows, body)

        near_meta = None
        if near is not None:
            centers, radius, label = self.near_centers(date_str, near)
            wr = {"op": "within_radius", "centers": centers, "radius_km": radius}
            base = body.get("filter")
            body["filter"] = {"and": [wr, base]} if base is not None else wr
            near_meta = {"radius_km": radius, "resolved": label, "centers": centers}

        if tab is not None:
            from api import query_colunar

            result = query_colunar.execute(tab, body)
        else:
            result = _q.execute(rows, body)
        if collection in self.COLECOES_SEM_POSICAO and result.get("items"):
            result["items"] = [sem_posicao(i) for i in result["items"]]
        result["snapshot_date"] = date_str
        result["collection"] = collection
        if near_meta is not None:
            result["near"] = near_meta
        return result

    def query_schema(self, collection: Optional[str] = None) -> dict:
        """Catálogo de schema das collections consultáveis."""
        from api import query as _q

        return _q.schema(collection)

    def resolve_operator(self, date_str: str, name: str) -> dict:
        """Marca/operador → ASNs, nesta ordem (o resultado diz qual valeu em `metodo`):

        1. `curada`: a tabela marca → raiz de CNPJ (`config/curada_marcas_operadoras.yaml`, `core.marcas`) e os ASNs dessas raízes, mais os
           ASNs estrangeiros da marca (seção `asns_estrangeiros`, devolvidos também em `asns_estrangeiros`);
        2. `sici`: operadora do SICI com o nome (empresa) ou o grupo econômico igual à marca;
        3. `cdn`: CDN/CAP de `cdns.json`;
        4. `nome_do_as`: trecho do nome do AS, só ASNs brasileiros (os estrangeiros só sem nenhum brasileiro), agrupado pela raiz de CNPJ.

        Só com o passo 4, sem filtro de país, "Vivo" devolveria Vivor (NL), Invivo (FR) e Vivo (CO) e nenhum AS da Telefônica Brasil."""
        from core import marcas

        q = name.strip().lower()
        n = marcas.normalizar(name)
        tab = self.query_table(date_str, "asns")
        nomes = {r["asn"]: r.get("name") for r in tab}
        matches: list[dict] = []
        asns: set[int] = set()
        metodo, base = None, None

        try:
            tabela = marcas.carregar_curada()
            curada = marcas.casar(name, tabela, {}, automatico=False)
        except Exception:
            tabela, curada = {}, None
        estrangeiros: set[int] = set()
        if curada:
            raizes = set(curada["raizes"])
            asns = {r["asn"] for r in tab if r.get("cnpj_root") in raizes}
            metodo, base = "curada", curada["base"]
        else:
            # marca só da seção `asns_estrangeiros` (Starlink → AS14593): o vínculo `estrangeiro` da decisão D5
            e = next((e for e in tabela.get("asns_estrangeiros") or [] if marcas.normalizar(e["marca"]) == n), None) if n else None
            if e:
                raizes = set(e["raizes"])
                asns = {r["asn"] for r in tab if r.get("cnpj_root") in raizes}
                curada = {"raizes": e["raizes"]}
                metodo, base = "curada", e["base"]
        if curada:
            raizes = set(curada["raizes"])
            for e in tabela.get("asns_estrangeiros") or []:
                if raizes & set(e["raizes"]):
                    estrangeiros.update(e["asns"])
            asns |= estrangeiros

        if not asns and n:
            try:
                ops = self.query_table(date_str, "operadoras")
            except Exception:
                ops = []
            casadas = [o for o in ops if n in (marcas.normalizar(o.get("empresa")), marcas.normalizar(o.get("grupo_economico")))]
            for o in casadas:
                asns.update(o.get("asns") or [])
            if asns:
                metodo, base = "sici", "operadora(s) do SICI com o nome ou o grupo econômico igual à marca: " + \
                    ", ".join(sorted({o.get("empresa") or "" for o in casadas}))[:300]

        data = self.cdn_presence(date_str) or {}
        for c in (data.get("cdns", []) if isinstance(data, dict) else []):
            if q and q in (c.get("name") or "").lower():
                matches.append({"source": "cdn", "name": c.get("name"), "asns": c.get("asns", [])})
                if metodo is None:
                    asns.update(c.get("asns", []))
        if metodo is None and matches:
            metodo, base = "cdn", "CDN/CAP com esse nome"

        if not asns and q:
            def casa(row):
                return q in " ".join(str(row.get(k) or "") for k in ("name", "razao_social", "nome_fantasia")).lower()
            achados = [r for r in tab if casa(r)]
            br = [r for r in achados if r.get("is_br")]
            usados = br or achados
            roots = {r["cnpj_root"] for r in usados if r.get("cnpj_root")}
            asns = {r["asn"] for r in usados} | {r["asn"] for r in tab if roots and r.get("cnpj_root") in roots}
            if asns:
                metodo = "nome_do_as"
                base = ("trecho do nome do AS (só ASNs brasileiros); confira os nomes" if br else
                        "trecho do nome do AS; nenhum AS brasileiro casou, os listados são estrangeiros: confira os nomes")

        out = {"snapshot_date": date_str, "query": name, "asns": sorted(asns), "cdn_matches": matches,
               "metodo": metodo, "base": base, "nomes": {str(a): nomes.get(a) for a in sorted(asns)[:40]}}
        if estrangeiros:
            out["asns_estrangeiros"] = sorted(estrangeiros)       # AS de fora do Brasil ligado à marca pela tabela curada (vínculo inferido)
        if not asns:
            out["aviso"] = "nenhum AS casou: tente o nome da empresa (outorga_lista(q=...)) ou o CNPJ"
        return out

    # -------------------------------------------------------------------------
    # Resolvers geográficos (lugar/PTT → coordenadas)
    # -------------------------------------------------------------------------
