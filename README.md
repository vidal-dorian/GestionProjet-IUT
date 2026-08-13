# GestionProjet-IUT

Outil de suivi de projet (heures, membres, dashboard). Voir le backlog dans les issues GitHub du dépôt.

## Stack

- **Backend** : Python / FastAPI / SQLAlchemy
- **Frontend** : React (Vite) / TypeScript
- **Base de données** : MySQL

## Lancer en local

### Base de données

```bash
docker compose up -d mysql
```

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload
```

L'API est disponible sur `http://localhost:8000` (doc interactive sur `/docs`).

Lancer les tests :

```bash
cd backend
.venv/bin/pytest
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

L'application est disponible sur `http://localhost:5173`.
