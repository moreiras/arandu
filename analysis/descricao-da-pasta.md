# analysis/ — atalhos de compatibilidade

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Nomes antigos dos módulos de análise, mantidos para quem ainda os chama (`python -m analysis.<nome>` ou `import analysis.<nome>`). Cada arquivo
só importa o módulo novo e emite `DeprecationWarning`; o código Python do projeto não os importa (`tests/unit/test_sem_uso_dos_atalhos.py`).
Os módulos de análise vivem em `products/<id>/`. Detalhes em `products/descricao-da-pasta.md`.

| Nome antigo | Módulo atual |
|---|---|
| `analysis.bgp_parser` | `products.bgp_routes.build` |
| `analysis.bgp_stability` | `products.bgp_stability.build` |
| `analysis.bgp_stability_deep` | `products.bgp_stability.deep` |
| `analysis.metrics` | `products.ixp_metrics.build` |
| `analysis.routing_analysis` | `products.routing_analysis.build` |
