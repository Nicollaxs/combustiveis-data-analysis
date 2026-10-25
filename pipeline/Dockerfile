# Imagem do Airflow + Java + PySpark (Spark roda em modo local dentro do Airflow)
FROM apache/airflow:3.3.2-python3.12

USER root
# Spark precisa de uma JVM. default-jre-headless instala o Java padrão da distro (17 ou 21, ambos suportados pelo Spark 4)
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Driver JDBC do Postgres, usado pelo Spark para gravar a camada gold
ARG PG_JDBC_VERSION=42.7.4
RUN mkdir -p /opt/jars \
 && curl -fsSL -o /opt/jars/postgresql.jar \
    https://repo1.maven.org/maven2/org/postgresql/postgresql/${PG_JDBC_VERSION}/postgresql-${PG_JDBC_VERSION}.jar

USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt
