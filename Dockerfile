# Image Python officielle
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système pour psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgobject-2.0-0 \
    libcairo2 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code de l'application
COPY . .

# Créer le dossier uploads
RUN mkdir -p /app/app/static/uploads

# Exposer le port
EXPOSE 5000

# Commande de démarrage
CMD ["python", "run.py"]