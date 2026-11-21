# Arquivos da instância

O Arandurapé é o software; o site que o roda tem nome, endereço e contato próprios (`SITE_*` no `.env`, `core/site.py`) e também marca
própria. A marca da instância fica nesta pasta, **fora do repositório** (só este README é versionado), e entra na imagem do frontend na
compilação (`Dockerfile.frontend`).

`instancia/marca/` substitui os arquivos de mesmo nome em `frontend/public/`:

| Arquivo | Onde aparece | Padrão do software |
|---|---|---|
| `marca.svg` | Cabeçalho de todas as páginas e tela de login | Um "A" |
| `favicon.svg`, `favicon.ico` | Ícone da aba e dos favoritos | Um "A" |

Outros arquivos da pasta também são copiados para a raiz do site (ex.: um `logo.svg` para usar fora do código).

Sem a pasta, o site sai com o "A" do software. Depois de trocar um arquivo, reconstrua o frontend (`docker compose build frontend`, ou
`restart-safe.sh`, que também limpa o `nginx_cache`).
