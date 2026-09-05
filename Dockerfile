FROM python:3.12-slim
WORKDIR /app
LABEL org.opencontainers.image.title="Diagnóstico Territorial Preliminar"
LABEL org.opencontainers.image.description="Protótipo aberto de pré-diagnóstico territorial e ambiental inspirado no projeto CNPq RHAE 443538/2024-7"
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "web/app.py", "--server.address=0.0.0.0"]
