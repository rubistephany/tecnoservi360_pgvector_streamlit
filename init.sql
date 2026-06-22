CREATE EXTENSION IF NOT EXISTS vector;

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
