import time
import sys

import pandas as pd
import psycopg2
import streamlit as st
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize

DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "dbname": "tecnoservi360",
    "user": "admin",
    "password": "admin123",
}

VECTOR_SIZE = 384

def esperar_postgres(intentos=30, segundos=2):
    for _ in range(intentos):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            return
        except Exception:
            time.sleep(segundos)
    st.error("No se pudo conectar con PostgreSQL.")
    sys.exit(1)

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def vector_a_pgvector(vector):
    return "[" + ",".join(str(float(x)) for x in vector) + "]"

def vectorizar_consulta(consulta):
    vectorizer = HashingVectorizer(
        n_features=VECTOR_SIZE,
        alternate_sign=False,
        norm=None
    )
    vector = vectorizer.transform([consulta])
    vector = normalize(vector)
    return vector_a_pgvector(vector.toarray()[0])

def obtener_opciones(campo):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT DISTINCT {campo} FROM documentos_tecnicos ORDER BY {campo};")
    valores = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return ["Todos"] + valores

def contar_documentos():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM documentos_tecnicos;")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total

def buscar_documentos(consulta, modelo, departamento, prioridad, limite):
    vector_consulta = vectorizar_consulta(consulta)
    condiciones = []
    parametros = []

    if modelo != "Todos":
        condiciones.append("modelo_equipo = %s")
        parametros.append(modelo)

    if departamento != "Todos":
        condiciones.append("departamento = %s")
        parametros.append(departamento)

    if prioridad != "Todos":
        condiciones.append("prioridad = %s")
        parametros.append(prioridad)

    where_sql = ""
    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)

    sql = f"""
        SELECT
            titulo,
            tipo_documento,
            departamento,
            modelo_equipo,
            fecha_actualizacion,
            prioridad,
            cliente_sector,
            descripcion,
            ROUND((embedding <=> %s::vector)::numeric, 4) AS distancia
        FROM documentos_tecnicos
        {where_sql}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """

    parametros_finales = [vector_consulta] + parametros + [vector_consulta, limite]
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=parametros_finales)
    conn.close()
    return df

st.set_page_config(page_title="TecnoServi360 - pgvector", layout="wide")
esperar_postgres()

st.title("TecnoServi360")
st.subheader("Buscador semántico con PostgreSQL + pgvector + Streamlit")

st.write("""
Busca documentos técnicos por significado y filtra por modelo, departamento o prioridad.
La base usa PostgreSQL con la extensión pgvector.
""")

try:
    total = contar_documentos()
except Exception:
    total = 0

if total == 0:
    st.warning("La tabla está vacía. Ejecuta primero: docker compose run --rm loader")
    st.stop()

st.success(f"Documentos cargados: {total}")

col1, col2 = st.columns([2, 1])
with col1:
    consulta = st.text_input("Consulta", value="manual de calibración XR")
with col2:
    limite = st.slider("Resultados", min_value=3, max_value=15, value=8)

c1, c2, c3 = st.columns(3)
with c1:
    modelo = st.selectbox("Modelo", obtener_opciones("modelo_equipo"))
with c2:
    departamento = st.selectbox("Departamento", obtener_opciones("departamento"))
with c3:
    prioridad = st.selectbox("Prioridad", obtener_opciones("prioridad"))

if st.button("Buscar"):
    if not consulta.strip():
        st.error("Escribe una consulta.")
        st.stop()

    resultados = buscar_documentos(consulta, modelo, departamento, prioridad, limite)

    if resultados.empty:
        st.warning("No hay resultados con esos filtros.")
    else:
        st.dataframe(resultados, use_container_width=True)

        for _, row in resultados.iterrows():
            with st.expander(f"{row['titulo']} | {row['modelo_equipo']} | distancia: {row['distancia']}"):
                st.write(f"**Tipo:** {row['tipo_documento']}")
                st.write(f"**Departamento:** {row['departamento']}")
                st.write(f"**Prioridad:** {row['prioridad']}")
                st.write(f"**Sector:** {row['cliente_sector']}")
                st.write(f"**Fecha:** {row['fecha_actualizacion']}")
                st.write(row["descripcion"])

st.divider()
st.write("### Pruebas recomendadas")
st.code("""
1. Busca: manual de calibración XR
   Sin filtros.

2. Busca: manual de calibración XR
   Filtro modelo: XR-900

3. Busca: manual de calibración XR
   Filtro modelo: XR-800

4. Busca: fallo de temperatura en refrigeración
   Filtro departamento: Mantenimiento

5. Busca: protocolo de seguridad industrial
   Filtro prioridad: Crítica
""")
