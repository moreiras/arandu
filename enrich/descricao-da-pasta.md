# enrich/ — atalhos de compatibilidade

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Nomes antigos dos enriquecedores, mantidos para quem ainda os chama (`python -m enrich.<nome>` ou `import enrich.<nome>`). Cada arquivo
só importa o módulo novo e emite `DeprecationWarning`; o código Python do projeto não os importa (`tests/unit/test_sem_uso_dos_atalhos.py`).
Os enriquecedores vivem em `sources/<id>/enrich.py`. Detalhes em `sources/descricao-da-pasta.md`.

| Nome antigo | Módulo atual |
|---|---|
| `enrich.cnpj_geo` | `sources.cnpj_geo.enrich` |
| `enrich.global_prefix_geo` | `sources.global_prefix_geo.enrich` |
| `enrich.peeringdb_intl_geo` | `sources.peeringdb_intl_geo.enrich` |
| `enrich.prefix_geo` | `sources.prefix_geo.enrich` |
| `enrich.rdap` | `sources.rdap.enrich` |
| `enrich.scm_geo` | `sources.scm_geo.enrich` |
| `enrich.seac_geo` | `sources.seac_geo.enrich` |
| `enrich.smp_geo` | `sources.smp_geo.enrich` |
| `enrich.socios_grupos` | `sources.socios_grupos.enrich` |
| `enrich.stfc_geo` | `sources.stfc_geo.enrich` |
