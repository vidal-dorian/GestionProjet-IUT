FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Utilisateur sans privilèges : une faille dans le traitement d'un fichier
# envoyé (logo, export) ne donnerait pas les droits root dans le conteneur.
RUN useradd --system --no-create-home --uid 10001 app
USER app

EXPOSE 8000

# --no-server-header : ne pas annoncer la version d'uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
