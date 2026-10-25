"""Bronze (CSV da ANP) -> Silver (Parquet limpo, tipado e deduplicado).

Executado via spark-submit pela DAG. Também roda à mão dentro do container:
  docker exec -it airflow-scheduler spark-submit /opt/airflow/include/jobs/bronze_para_silver.py
"""

import json
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

BRONZE = Path("/opt/airflow/data/bronze/anp")
SILVER = "/opt/airflow/data/silver/precos_revenda"

# Layout publicado pela ANP (todas as colunas lidas como texto; a tipagem é feita aqui)
COLUNAS = [
    ("Regiao - Sigla", "regiao"), ("Estado - Sigla", "uf"), ("Municipio", "municipio"),
    ("Revenda", "revenda"), ("CNPJ da Revenda", "cnpj"), ("Nome da Rua", "rua"),
    ("Numero Rua", "numero"), ("Complemento", "complemento"), ("Bairro", "bairro"),
    ("Cep", "cep"), ("Produto", "produto"), ("Data da Coleta", "data_coleta"),
    ("Valor de Venda", "valor_venda"), ("Valor de Compra", "valor_compra"),
    ("Unidade de Medida", "unidade"), ("Bandeira", "bandeira"),
]
SCHEMA = StructType([StructField(orig, StringType()) for orig, _ in COLUNAS])


def decimal_br(col):
    """'6,39' -> 6.39"""
    return F.regexp_replace(F.trim(col), ",", ".").cast("double")


def main():
    spark = SparkSession.builder.appName("anp_bronze_para_silver").getOrCreate()
    manifest = json.loads((BRONZE / "manifest.json").read_text())
    arquivos = [str(BRONZE / a["arquivo"]) for a in manifest["arquivos"]]

    bruto = (spark.read
             .option("header", True).option("sep", ";").option("encoding", "UTF-8")
             .schema(SCHEMA)
             .csv(arquivos)
             .withColumn("arquivo_origem", F.col("_metadata.file_name")))
    for orig, novo in COLUNAS:
        bruto = bruto.withColumnRenamed(orig, novo)

    df = (bruto
          .withColumn("cnpj", F.trim("cnpj"))
          .withColumn("regiao", F.upper(F.trim("regiao")))
          .withColumn("uf", F.upper(F.trim("uf")))
          .withColumn("produto", F.upper(F.trim("produto")))
          .withColumn("data_coleta", F.to_date(F.trim("data_coleta"), "dd/MM/yyyy"))
          .withColumn("valor_venda", decimal_br(F.col("valor_venda")))
          .withColumn("valor_compra", decimal_br(F.col("valor_compra"))))

    total = df.count()
    # Regras de qualidade: descarta linhas sem data/UF/CNPJ ou com preço fora de faixa plausível
    df = df.filter(
        F.col("data_coleta").isNotNull() & F.col("uf").rlike("^[A-Z]{2}$")
        & F.col("cnpj").isNotNull() & F.col("valor_venda").between(0.5, 30)
    )
    # Um preço por posto, produto e dia (arquivos vizinhos às vezes repetem coletas)
    df = df.dropDuplicates(["cnpj", "produto", "data_coleta"])

    df = (df.withColumn("ano", F.year("data_coleta")).withColumn("mes", F.month("data_coleta")))
    (df.repartition("ano", "mes")
       .write.mode("overwrite").partitionBy("ano", "mes").parquet(SILVER))

    final = spark.read.parquet(SILVER).count()
    print(f"[silver] linhas lidas={total} gravadas={final} descartadas={total - final}")
    spark.stop()


if __name__ == "__main__":
    main()
