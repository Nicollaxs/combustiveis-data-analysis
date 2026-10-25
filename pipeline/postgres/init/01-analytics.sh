#!/bin/bash
# Executado pelo Postgres SOMENTE na primeira inicialização (volume vazio).
# Cria o banco analítico (camada gold) e dois usuários:
#   - ANALYTICS_WRITER: usado pelo Spark para gravar
#   - DASHBOARD_RO:     somente leitura, usado pelo dashboard
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v writer_pw="$ANALYTICS_WRITER_PASSWORD" -v ro_pw="$DASHBOARD_RO_PASSWORD" <<'SQL'
CREATE ROLE analytics_writer LOGIN PASSWORD :'writer_pw';
CREATE ROLE dashboard_ro LOGIN PASSWORD :'ro_pw';
CREATE DATABASE analytics OWNER analytics_writer;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname analytics <<'SQL'
REVOKE ALL ON DATABASE analytics FROM PUBLIC;
GRANT CONNECT ON DATABASE analytics TO dashboard_ro;
CREATE SCHEMA gold AUTHORIZATION analytics_writer;
GRANT USAGE ON SCHEMA gold TO dashboard_ro;
-- Tabelas que o writer criar no futuro já nascem legíveis pelo dashboard
ALTER DEFAULT PRIVILEGES FOR ROLE analytics_writer IN SCHEMA gold GRANT SELECT ON TABLES TO dashboard_ro;
SQL
