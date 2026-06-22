import time
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "dbname": "tecnoservi360",
    "user": "admin",
    "password": "admin123",
}

CSV_FILE = "documentos_tecnoservi360.csv"
VECTOR_SIZE = 384

def esperar_postgres(intentos=30, segundos=2):
    for intento in range(1, intentos + 1):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            print("PostgreSQL está disponible.")
            return
        except Exception:
            print(f"Esperando PostgreSQL... intento {intento}/{intentos}")
            time.sleep(segundos)
    print("No se pudo conectar con PostgreSQL.")
    sys.exit(1)

def vector_a_pgvector(vector):
    return "[" + ",".join(str(float(x)) for x in vector) + "]"

def main():
    esperar_postgres()

    if not Path(CSV_FILE).exists():
        print(f"No se encuentra el archivo {CSV_FILE}")
        sys.exit(1)

    print("Leyendo CSV...")
    df = pd.read_csv(CSV_FILE)

    columnas = [
        "id_documento", "titulo", "descripcion", "tipo_documento",
        "departamento", "modelo_equipo", "fecha_actualizacion",
        "prioridad", "cliente_sector"
    ]

    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        print("Faltan columnas:", faltantes)
        sys.exit(1)

    df["texto_busqueda"] = df["titulo"].astype(str) + ". " + df["descripcion"].astype(str)

    print("Generando vectores...")
    vectorizer = HashingVectorizer(
        n_features=VECTOR_SIZE,
        alternate_sign=False,
        norm=None
    )

    matriz = vectorizer.transform(df["texto_busqueda"])
    matriz = normalize(matriz)
    vectores = matriz.toarray()

    print("Conectando a PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Activando pgvector y creando tabla...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documentos_tecnicos (
            id_documento INT PRIMARY KEY,
            titulo TEXT,
            descripcion TEXT,
            texto_busqueda TEXT,
            tipo_documento TEXT,
            departamento TEXT,
            modelo_equipo TEXT,
            fecha_actualizacion DATE,
            prioridad TEXT,
            cliente_sector TEXT,
            embedding VECTOR(384)
        );
    """)

    print("Limpiando tabla anterior...")
    cur.execute("TRUNCATE TABLE documentos_tecnicos;")

    print("Insertando documentos...")
    for i, row in df.iterrows():
        embedding = vector_a_pgvector(vectores[i])
        cur.execute("""
            INSERT INTO documentos_tecnicos (
                id_documento, titulo, descripcion, texto_busqueda,
                tipo_documento, departamento, modelo_equipo,
                fecha_actualizacion, prioridad, cliente_sector, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector);
        """, (
            int(row["id_documento"]),
            row["titulo"],
            row["descripcion"],
            row["texto_busqueda"],
            row["tipo_documento"],
            row["departamento"],
            row["modelo_equipo"],
            row["fecha_actualizacion"],
            row["prioridad"],
            row["cliente_sector"],
            embedding,
        ))

    print("Creando índice HNSW...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_embedding_hnsw
        ON documentos_tecnicos
        USING hnsw (embedding vector_cosine_ops);
    """)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM documentos_tecnicos;")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"Carga terminada correctamente. Documentos insertados: {total}")
    print("Abre la app en http://localhost:8501")

if __name__ == "__main__":
    main()
