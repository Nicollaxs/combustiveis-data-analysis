"""Pipeline semanal de preços de combustíveis da ANP.

extrair (bronze) -> bronze_para_silver (Spark) -> silver_para_gold (Spark -> Postgres) -> validar_gold
"""

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

# Spark em modo local, dentro do container do scheduler (LocalExecutor).
# Driver de 5 GB cabe no mem_limit de 8 GB do scheduler; 3 threads para não monopolizar as 4 OCPUs.
SPARK_SUBMIT = (
    "spark-submit --master 'local[3]' --driver-memory 5g "
    "--conf spark.sql.shuffle.partitions=12 --conf spark.ui.enabled=false "
    "--jars /opt/jars/postgresql.jar "
)
JOBS = "/opt/airflow/include/jobs"


@dag(
    dag_id="anp_precos_combustiveis",
    schedule="0 7 * * 1",  # toda segunda às 07:00 (horário de Brasília)
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=10)},
    tags=["anp", "spark"],
    doc_md=__doc__,
)
def anp_precos_combustiveis():

    @task
    def extrair():
        from anp_extract import extrair as _extrair
        return _extrair()

    bronze_para_silver = BashOperator(
        task_id="bronze_para_silver",
        bash_command=SPARK_SUBMIT + f"{JOBS}/bronze_para_silver.py",
    )

    silver_para_gold = BashOperator(
        task_id="silver_para_gold",
        bash_command=SPARK_SUBMIT + f"{JOBS}/silver_para_gold.py",
    )

    @task
    def validar_gold():
        """Checagens mínimas antes de considerar a carga boa."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id="analytics_db")
        n_ufs = hook.get_first("SELECT count(DISTINCT codigo) FROM gold.resumo WHERE nivel = 'uf'")[0]
        semana, preco_br = hook.get_first(
            "SELECT semana_atual, preco_atual FROM gold.resumo WHERE nivel = 'pais'")
        dias = (pendulum.today("America/Sao_Paulo").date() - semana).days

        erros = []
        if n_ufs != 27:
            erros.append(f"esperava 27 UFs no resumo, achei {n_ufs}")
        if not (3 <= float(preco_br) <= 15):
            erros.append(f"preço médio Brasil fora do plausível: {preco_br}")
        if dias > 90:
            erros.append(f"dado mais recente tem {dias} dias (semana {semana})")
        if erros:
            raise ValueError("; ".join(erros))
        print(f"OK: 27 UFs, Brasil R$ {preco_br} na semana {semana} ({dias} dias atrás)")

    extrair() >> bronze_para_silver >> silver_para_gold >> validar_gold()


anp_precos_combustiveis()
