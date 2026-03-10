FROM python:3.13-slim

WORKDIR /app

# Installation de curl pour le healthcheck et les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
RUN pip install --no-cache-dir \
    "pandas>=2.2.0" \
    "pyarrow>=19.0.0" \
    "plotly>=5.24.0,<6.0" \
    "requests>=2.32.0" \
    "streamlit>=1.41.0" \
    "python-dotenv>=1.0.0" \
    "watchdog>=6.0.0"

# Copie des fichiers de l'application
COPY st_main.py .
COPY .streamlit/ .streamlit/

# Création du dossier data s'il n'existe pas
RUN mkdir -p data

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "st_main.py", "--server.port=8501", "--server.address=0.0.0.0"]
