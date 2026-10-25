# combustiveis-data-analysis

Pipeline de dados de ponta a ponta sobre o preço dos combustíveis no Brasil, com dados abertos da
ANP (Série Histórica de Preços de Combustíveis).

```
ANP (gov.br) ─► Airflow ─► PySpark ─► Postgres (gold) ─► Dashboard Streamlit
                 bronze      silver       analytics
```

| Pasta | O que é |
|---|---|
| [`pipeline/`](pipeline/) | Airflow 3 + PySpark (modo local) + Postgres: extração, limpeza e agregação semanal |
| [`dashboard/`](dashboard/) | Streamlit + Plotly lendo a camada gold com um usuário somente leitura |

**Stack:** Apache Airflow 3.3 · PySpark 4.1 · PostgreSQL 16 · Streamlit · Plotly · Docker Compose
(tudo arm64, rodando numa VM Ampere da Oracle Cloud).

## Como rodar

```bash
# 1. Pipeline (sobe primeiro: cria o Postgres e a rede analytics-net)
cd pipeline
cp .env.example .env        # preencha as senhas
docker compose build && docker compose up -d
docker exec airflow-scheduler airflow dags unpause anp_precos_combustiveis
docker exec airflow-scheduler airflow dags trigger anp_precos_combustiveis

# 2. Dashboard
cd ../dashboard
cp .env.example .env        # DB_PASSWORD = DASHBOARD_RO_PASSWORD da pipeline
docker compose up -d --build
```

Detalhes e decisões de arquitetura no README de cada pasta.
