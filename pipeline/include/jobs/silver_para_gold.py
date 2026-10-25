"""Silver -> Gold: agregados de GASOLINA COMUM gravados no Postgres (banco analytics, schema gold).

Tabelas geradas (recriadas por completo a cada execução):
  gold.preco_semanal  — preço médio/mín/máx por semana em 3 níveis: pais (BR), regiao, uf
  gold.resumo         — fotografia atual por nível: preço da última semana, faixa histórica, variação 12m
"""

import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

SILVER = "/opt/airflow/data/silver/precos_revenda"
PRODUTO = "GASOLINA"  # gasolina comum (aditivada é "GASOLINA ADITIVADA")

JDBC_URL = "jdbc:postgresql://postgres:5432/analytics"
JDBC_PROPS = {
    "user": "analytics_writer",
    "password": os.environ["ANALYTICS_WRITER_PASSWORD"],
    "driver": "org.postgresql.Driver",
}

NOMES_REGIAO = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}
NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará",
    "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}


def gravar(df, tabela):
    # truncate=True: esvazia e reaproveita a tabela (mantém os GRANTs do dashboard)
    (df.write.mode("overwrite").option("truncate", True)
       .jdbc(JDBC_URL, f"gold.{tabela}", properties=JDBC_PROPS))
    print(f"[gold] {tabela}: {df.count()} linhas")


def main():
    spark = SparkSession.builder.appName("anp_silver_para_gold").getOrCreate()
    spark.conf.set("spark.sql.session.timeZone", "America/Sao_Paulo")

    mapa_regiao = F.create_map(*[F.lit(x) for kv in NOMES_REGIAO.items() for x in kv])
    mapa_uf = F.create_map(*[F.lit(x) for kv in NOMES_UF.items() for x in kv])

    base = (spark.read.parquet(SILVER)
            .filter(F.col("produto") == PRODUTO)
            # semana começando na segunda-feira
            .withColumn("semana", F.to_date(F.date_trunc("week", "data_coleta")))
            .select("semana", "regiao", "uf", "valor_venda")
            .cache())

    def agrega(df, nivel, codigo, nome, regiao):
        return (df.groupBy("semana", codigo.alias("codigo"))
                  .agg(F.round(F.avg("valor_venda"), 3).alias("preco_medio"),
                       F.min("valor_venda").alias("preco_min"),
                       F.max("valor_venda").alias("preco_max"),
                       F.count("*").alias("n_coletas"),
                       F.first(regiao).alias("regiao"))
                  .withColumn("nivel", F.lit(nivel))
                  .withColumn("nome", nome))

    semanal = (
        agrega(base, "pais", F.lit("BR"), F.lit("Brasil"), F.lit(None).cast("string"))
        .unionByName(agrega(base, "regiao", F.col("regiao"), mapa_regiao[F.col("codigo")], F.col("regiao")))
        .unionByName(agrega(base, "uf", F.col("uf"), mapa_uf[F.col("codigo")], F.col("regiao")))
        .select("semana", "nivel", "codigo", "nome", "regiao",
                "preco_medio", "preco_min", "preco_max", "n_coletas")
    )
    # Os arquivos são mensais/semestrais, então semanas nas pontas (e na lacuna de 2022) vêm pela
    # metade. Mantemos só semanas com pelo menos 50% da mediana de coletas do país.
    br = semanal.filter(F.col("nivel") == "pais")
    mediana = br.agg(F.percentile_approx("n_coletas", 0.5)).first()[0]
    completas = br.filter(F.col("n_coletas") >= mediana * 0.5).select("semana")
    semanal = semanal.join(completas, "semana", "left_semi").cache()
    ultima = semanal.agg(F.max("semana")).first()[0]
    gravar(semanal.orderBy("nivel", "codigo", "semana"), "preco_semanal")

    # ---- resumo: última semana completa vs. histórico
    w = Window.partitionBy("nivel", "codigo")
    hist = (semanal.groupBy("nivel", "codigo", "nome", "regiao")
            .agg(F.min("preco_medio").alias("minimo_semanal"),
                 F.round(F.avg("preco_medio"), 3).alias("media_periodo"),
                 F.max("preco_medio").alias("maximo_semanal"),
                 F.min("semana").alias("primeira_semana")))
    atual = (semanal.filter(F.col("semana") == F.lit(ultima))
             .select("nivel", "codigo", F.col("preco_medio").alias("preco_atual"),
                     F.col("n_coletas").alias("n_coletas_atual")))
    # preço de ~12 meses atrás: a semana mais próxima de (última - 52 semanas)
    alvo = F.date_sub(F.lit(ultima), 364)
    ano_atras = (semanal.withColumn("dist", F.abs(F.datediff("semana", alvo)))
                 .filter(F.col("dist") <= 14)
                 .withColumn("rk", F.row_number().over(w.orderBy("dist")))
                 .filter("rk = 1")
                 .select("nivel", "codigo", F.col("preco_medio").alias("preco_12m_atras")))

    resumo = (hist.join(atual, ["nivel", "codigo"], "left")
              .join(ano_atras, ["nivel", "codigo"], "left")
              .withColumn("variacao_12m_pct",
                          F.round((F.col("preco_atual") / F.col("preco_12m_atras") - 1) * 100, 2))
              .withColumn("semana_atual", F.lit(ultima))
              .withColumn("atualizado_em", F.current_timestamp()))
    gravar(resumo.orderBy("nivel", "codigo"), "resumo")
    spark.stop()


if __name__ == "__main__":
    main()
