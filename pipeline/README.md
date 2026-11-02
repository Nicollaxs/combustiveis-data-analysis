# pipeline

Pipeline de dados que coleta os preços de combustíveis publicados pela ANP, trata com
PySpark, grava agregados num Postgres e alimenta o dashboard em `../dashboard`.

```
ANP (gov.br) ──► extrair ──► bronze_para_silver ──► silver_para_gold ──► validar_gold
                 (Python)     (Spark)                (Spark → Postgres)   (SQL)
                    │             │                        │
             data/bronze/   data/silver/            analytics.gold.*  ◄── dashboard_gasolina
             CSV UTF-8      Parquet por ano/mês     preco_semanal, resumo
```

DAG `anp_precos_combustiveis`, toda segunda às 07:00 (horário de Brasília).

## Componentes

| Serviço | Papel | Limite de memória |
|---|---|---|
| `pipeline-postgres` | Metadados do Airflow (banco `airflow`) + camada gold (banco `analytics`) | 1 GB |
| `airflow-apiserver` | UI e API do Airflow 3 (`127.0.0.1:8081`) | 1,5 GB |
| `airflow-scheduler` | Agenda **e executa** as tasks (LocalExecutor), inclusive o Spark | 8 GB |
| `airflow-dag-processor` | Lê os arquivos de DAG | 1 GB |
| `airflow-init` | Roda uma vez: migra o banco e prepara diretórios | — |

Imagem própria (`Dockerfile`): `apache/airflow:3.3.2-python3.12` (arm64) + Java 17 + PySpark 4.1.3
+ driver JDBC do Postgres.

## Camadas de dados

- **Bronze** (`data/bronze/anp/`): CSVs da ANP como publicados, só convertidos para UTF-8.
  `manifest.json` lista os arquivos usados na última execução.
- **Silver** (`data/silver/precos_revenda/`): Parquet particionado por `ano`/`mes`, uma linha por
  posto × produto × dia. Colunas tipadas; descarta linhas sem data/UF/CNPJ e preços fora de R$ 0,50–30.
- **Gold** (Postgres `analytics`, schema `gold`), só gasolina comum:
  - `preco_semanal` — por semana (segunda a domingo) e nível (`pais`, `regiao`, `uf`): média, mín, máx, nº de coletas.
  - `resumo` — por nível: preço da última semana completa, mín/média/máx das médias semanais,
    preço de 12 meses antes e variação %.

## Decisões

- **Spark em modo local dentro do Airflow** (não cluster): o volume (~4 milhões de linhas) cabe numa
  máquina; menos containers e menos memória. `spark-submit --master local[3] --driver-memory 5g`.
- **Gold no Postgres** (não Parquet compartilhado): o dashboard consulta via SQL com um usuário
  somente leitura (`dashboard_ro`), pela rede Docker `analytics-net`.
- **LocalExecutor, sem Redis/Celery e sem triggerer**: suficiente para uma DAG; economiza ~1 GB.
- **Fontes da ANP**: semestral (`ca-AAAA-SS`) quando existe; mensal só para meses que nenhum
  semestral cobre. Os links são lidos da página porque os nomes dos mensais são irregulares.
  Quando sai um semestral novo, os mensais que ele cobre são apagados da bronze.
- **Lacuna conhecida**: a ANP não publica o 1º semestre de 2022 (jan–jun). A série tem esse buraco.
- **Última semana**: como os arquivos fecham no fim do mês, a última semana costuma vir parcial;
  o gold ignora semanas com menos de 50% da mediana de coletas.
- Gravação no Postgres com `overwrite` + `truncate`: preserva as permissões do `dashboard_ro`.
  Se mudar as colunas de uma tabela gold, apague a tabela antes (`DROP TABLE gold.x`).

## Operação

```bash
cd ~/projetos/combustiveis-data-analysis/pipeline
docker compose up -d            # sobe tudo
docker compose ps               # status
docker compose logs -f airflow-scheduler

# UI do Airflow: no SEU computador
ssh -L 8081:127.0.0.1:8081 ubuntu@<ip-da-vm>    # depois abra http://localhost:8081
# usuário/senha: AIRFLOW_ADMIN_USER / AIRFLOW_ADMIN_PASSWORD do .env

# Rodar a DAG na hora
docker exec airflow-scheduler airflow dags trigger anp_precos_combustiveis

# Consultar o gold
docker exec -it pipeline-postgres psql -U analytics_writer -d analytics \
  -c "select * from gold.resumo where nivel <> 'uf'"
```

### Primeira instalação

1. `cp .env.example .env` e preencha. **Senhas não podem começar com `-`** (o CLI do Airflow
   confunde com uma opção e o usuário admin não é criado). Gere com `python3 -c "import secrets;print(secrets.token_hex(24))"`.
2. `docker compose build && docker compose up -d`
3. O script `postgres/init/01-analytics.sh` cria o banco `analytics` e os usuários
   `analytics_writer` / `dashboard_ro` **somente na primeira subida** (volume vazio).

### Manutenção

- Logs do Airflow em `logs/` — limpar periodicamente (ex.: apagar com mais de 30 dias).
- Disco: bronze ~1 GB de CSV, silver bem menor (Parquet comprimido).

## Avisos por email

- Sucesso: task final `notificar_sucesso` envia resumo (se houve dado novo da ANP, semana mais recente, preço médio).
- Erro: `on_failure_callback` (`include/notificar.py`) envia email só quando a task falha de vez (após os 2 retries).
- Envio via SMTP do Gmail (`smtp.gmail.com:465`) com **senha de app** — gratuito, sem serviço de terceiros.
- Variáveis no `.env`: `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFY_EMAIL`. Sem elas o envio é só pulado (com warning no log).
- Após mudar o `.env`: `docker compose up -d` (recria os containers para lerem as variáveis).
