FROM python:3.12-slim

WORKDIR /app

# Instala as bibliotecas primeiro (o Docker reaproveita essa etapa se o requirements não mudar)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do projeto (app.py, geojson, .streamlit/)
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
