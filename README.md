# TecnoServi360 - PostgreSQL + pgvector + Streamlit

## Objetivo

Crear una interfaz visual para buscar documentos técnicos por significado usando PostgreSQL con pgvector.

## Estructura

```text
tecnoservi360_pgvector_streamlit
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── init.sql
├── documentos_tecnoservi360.csv
├── cargar_datos.py
└── app.py
```

## Arranque

Desde PowerShell:

```powershell
cd C:\Users\fuent\Desktop\tecnoservi360_pgvector_streamlit
docker compose up -d --build postgres app
docker compose run --rm loader
```

Abre:

```text
http://localhost:8501
```

## Parar

```powershell
docker compose down
```

No uses `docker compose down -v` salvo que quieras borrar la base de datos.
