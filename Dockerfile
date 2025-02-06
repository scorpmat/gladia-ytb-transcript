FROM python:3.10

WORKDIR /app/app

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Définir les variables d'environnement par défaut
ENV PYTHONPATH=/app

CMD ["python", "main.py"]