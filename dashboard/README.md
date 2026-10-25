# dashboard

Painel Streamlit + Plotly com o preço da gasolina comum no Brasil. É a etapa final da
pipeline em `../pipeline`.

## De onde vêm os dados

Lê duas tabelas do schema `gold` no banco `analytics` (Postgres da pipeline):

- `gold.preco_semanal`: série semanal (Brasil, regiões e UFs), usada no gráfico de evolução.
- `gold.resumo`: retrato atual e histórico por nível, usado em KPIs, ranking, faixas, mapa e insights.

Nada é fixo no código: KPIs, ranking, estados destacados e insights são recalculados a cada
carga. O cache é de 1 hora (`st.cache_data(ttl=3600)`) e a pipeline roda toda segunda.

## Decisões

- Conexão com o usuário **`dashboard_ro`** (somente leitura). Credenciais no `.env`
  (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), que fica fora do Git e da imagem
  (`.dockerignore`).
- O container entra na rede Docker externa **`analytics-net`**, criada pelo compose da pipeline.
  Por isso a pipeline precisa estar no ar antes (`docker compose up -d` lá primeiro).
- O gráfico de evolução mostra a lacuna do 1º semestre de 2022, que a ANP não publicou, em vez
  de ligar os pontos.
- Publicado só em `127.0.0.1:8501`. Acesse com `ssh -L 8501:127.0.0.1:8501 ubuntu@<ip-da-vm>`.

## Operação

```bash
cd ~/projetos/combustiveis-data-analysis/dashboard
docker compose up -d --build
docker compose logs -f dashboard
```
