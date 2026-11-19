# frontend/ — interface web

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Interface web do Arandurapé: React 18, Vite, TypeScript e Tailwind CSS. Consome a API REST (`api/`) e é servida pelo nginx do
contêiner `frontend` (`Dockerfile.frontend`, `docker/nginx-frontend.conf`). Node e npm não precisam estar instalados: build e
testes rodam em contêiner (`bash scripts/front-test.sh`; servidor de desenvolvimento no README).

## Raiz

| Arquivo | Papel |
|---|---|
| `package.json`, `package-lock.json` | Dependências e scripts (`dev`, `build`, `typecheck`, `test`). |
| `index.html` | Página de entrada do Vite. |
| `vite.config.ts` | Configuração do Vite e do Vitest. |
| `tsconfig.json` | Configuração do TypeScript. |
| `tailwind.config.ts`, `postcss.config.js` | Tailwind CSS. |
| `tsconfig.tsbuildinfo` | Cache incremental do `tsc`, gerado no build (não precisa ser versionado). |

## `src/`

| Pasta ou arquivo | Papel |
|---|---|
| `main.tsx` | Ponto de entrada: rotas (React Router), provedores (TanStack Query, autenticação) e layout. |
| `pages/` | Uma página por rota (listas, entidades, panoramas, fontes, sobre, privacidade, perfil). |
| `features/` | Partes de página por assunto, uma pasta por entidade ou tema (`asn/`, `ptt/`, `operadora/`, `municipio/`, `uf/`, `prefixo/`, `grupo/`, `panorama/`, `home/`, `localizador/`, `comparar/`, `historico/` e os produtos de cada fonte). |
| `components/` | Componentes reutilizáveis: `layout/` (cabeçalho, menu, seletor de snapshot), `ui/` (primitivas), `entidade/`, `maps/` (MapLibre GL), `hilbert/` (curva de Hilbert do espaço IP), `bgp/`, `graphs/` (D3), `charts/` (Recharts), `stats/`, `tables/`, `acessos/`, `socios/`. |
| `auth/` | Contexto de autenticação, modal de login (todo 401 o abre) e `accessPolicy.ts`, espelho da política de acesso do servidor (conferido por `tests/unit/test_front_access_mirror.py`). |
| `services/` | Cliente da API (`api.ts`), React Query e camadas estáticas do mapa endereçadas por conteúdo. |
| `hooks/` | Hooks compartilhados. |
| `lib/` | Utilitários sem React: `site.ts` (nome e URL do site, lidos do `.env` na compilação), `familias.ts` (IPv6 antes de IPv4 em toda ordem), formatação, datas, escalas e cores de mapa. |
| `store/` | Estado global (Zustand): snapshot selecionado. |
| `types/` | Tipos TypeScript; `openapi.gen.ts` é gerado do OpenAPI (`bash scripts/front-test.sh --gen-tipos`). |
| `test/` | Configuração do Vitest e do msw; `fixtures/` traz respostas reais da API sobre o dataset sintético (`python -m tests.synth.export_front_fixtures`). |
| `utils/` | Regiões e UFs. |
| `index.css` | Estilos globais e tokens de cor. |

## `public/` (servido como está)

| Arquivo | Papel |
|---|---|
| `favicon.ico`, `favicon.svg`, `arandu-mark.svg` | Ícones e marca. |
| `arandu-logo.svg` | Logotipo completo (sem referência no código atual). |
| `br-states.geojson`, `br-places.geojson`, `world-places.geojson` | Contornos dos estados e rótulos de lugares dos mapas. |
| `malha-municipal.pmtiles`, `malha-municipal.json` | Malha municipal do IBGE em tiles vetoriais e seus metadados (`scripts/build-malha-municipal.py`). |
| `municipios-centroides.json` | Centroides dos municípios (`scripts/build-municipio-centroides.py`, que grava também a cópia em `config/`). |
| `catalogo.json` | Catálogo público das fontes para a página Fontes (gerado por `scripts/gen_docs.py`). |

## Regras

Ver `AGENTS.md` (seção "Como codificar"): hover sem estado do React, mapas que não re-renderizam por hover, IPv6 antes de IPv4,
acessibilidade ABNT NBR 17225 / WCAG 2.2 AA, nome do site sempre por `SITE`.
