"""Database layer — schema creation, seed data and query helpers."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "data" / "gestoralmacen.db"


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
-- Auth
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    permisos TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    departamento TEXT NOT NULL,
    rol_id INTEGER REFERENCES roles(id),
    activo INTEGER DEFAULT 1,
    ultimo_acceso TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

-- Almacén
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('MP','PT','EM','QP','OT'))
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referencia TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    categoria_id INTEGER REFERENCES categorias(id),
    unidad TEXT NOT NULL DEFAULT 'ud',
    stock_actual REAL DEFAULT 0,
    stock_minimo REAL DEFAULT 0,
    stock_maximo REAL DEFAULT 0,
    ubicacion TEXT,
    proveedor_id INTEGER,
    precio_compra REAL DEFAULT 0,
    activo INTEGER DEFAULT 1,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad REAL NOT NULL,
    cantidad_disponible REAL NOT NULL,
    fecha_entrada TEXT NOT NULL,
    fecha_caducidad TEXT,
    proveedor_id INTEGER,
    numero_alb_proveedor TEXT,
    precio_unitario REAL DEFAULT 0,
    estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo','agotado','caducado','bloqueado','cuarentena')),
    notas TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ubicaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    zona TEXT NOT NULL,
    pasillo TEXT,
    estante TEXT,
    nivel TEXT,
    capacidad_kg REAL DEFAULT 0,
    ocupado_kg REAL DEFAULT 0,
    tipo TEXT DEFAULT 'estandar',
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK(tipo IN ('entrada','salida','traspaso','ajuste','devolucion')),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    lote_id INTEGER REFERENCES lotes(id),
    cantidad REAL NOT NULL,
    ubicacion_origen TEXT,
    ubicacion_destino TEXT,
    referencia_doc TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    departamento TEXT,
    notas TEXT,
    fecha TEXT DEFAULT (datetime('now'))
);

-- Producción
CREATE TABLE IF NOT EXISTS formulas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    producto_id INTEGER REFERENCES productos(id),
    version TEXT DEFAULT '1.0',
    rendimiento_kg REAL DEFAULT 0,
    instrucciones TEXT,
    ingredientes TEXT DEFAULT '[]',
    activo INTEGER DEFAULT 1,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ordenes_fabricacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    formula_id INTEGER REFERENCES formulas(id),
    producto_id INTEGER REFERENCES productos(id),
    cantidad_planificada REAL NOT NULL,
    cantidad_producida REAL DEFAULT 0,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    fecha_planificada TEXT,
    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente','en_proceso','completada','cancelada','pausada')),
    operario_id INTEGER REFERENCES usuarios(id),
    lote_producido TEXT,
    merma_kg REAL DEFAULT 0,
    notas TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

-- Compras
CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    nif TEXT,
    email TEXT,
    telefono TEXT,
    direccion TEXT,
    ciudad TEXT,
    pais TEXT DEFAULT 'España',
    contacto TEXT,
    plazo_entrega INTEGER DEFAULT 7,
    condiciones_pago TEXT,
    activo INTEGER DEFAULT 1,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ordenes_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    fecha TEXT NOT NULL,
    fecha_entrega_prevista TEXT,
    estado TEXT DEFAULT 'borrador' CHECK(estado IN ('borrador','enviada','confirmada','recibida_parcial','recibida','cancelada')),
    lineas TEXT DEFAULT '[]',
    total REAL DEFAULT 0,
    notas TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    creado_en TEXT DEFAULT (datetime('now'))
);

-- Ventas
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    nif TEXT,
    email TEXT,
    telefono TEXT,
    direccion TEXT,
    ciudad TEXT,
    pais TEXT DEFAULT 'España',
    contacto TEXT,
    condiciones_pago TEXT,
    descuento_pct REAL DEFAULT 0,
    activo INTEGER DEFAULT 1,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pedidos_venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    fecha TEXT NOT NULL,
    fecha_entrega TEXT,
    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente','confirmado','en_preparacion','expedido','entregado','cancelado')),
    lineas TEXT DEFAULT '[]',
    total REAL DEFAULT 0,
    notas TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS albaranes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    pedido_id INTEGER REFERENCES pedidos_venta(id),
    fecha TEXT NOT NULL,
    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente','expedido','entregado','devuelto')),
    transportista TEXT,
    num_seguimiento TEXT,
    bultos INTEGER DEFAULT 1,
    peso_kg REAL DEFAULT 0,
    notas TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

-- Calidad
CREATE TABLE IF NOT EXISTS controles_calidad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL CHECK(tipo IN ('entrada','proceso','salida','ambiental')),
    producto_id INTEGER REFERENCES productos(id),
    lote_id INTEGER REFERENCES lotes(id),
    fecha TEXT NOT NULL,
    resultado TEXT CHECK(resultado IN ('conforme','no_conforme','pendiente','en_revision')),
    tecnico_id INTEGER REFERENCES usuarios(id),
    parametros TEXT DEFAULT '{}',
    observaciones TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS no_conformidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    modulo TEXT NOT NULL,
    severidad TEXT CHECK(severidad IN ('baja','media','alta','critica')),
    estado TEXT DEFAULT 'abierta' CHECK(estado IN ('abierta','en_investigacion','resuelta','cerrada')),
    producto_id INTEGER REFERENCES productos(id),
    lote_id INTEGER REFERENCES lotes(id),
    accion_correctiva TEXT,
    fecha_apertura TEXT DEFAULT (datetime('now')),
    fecha_cierre TEXT,
    responsable_id INTEGER REFERENCES usuarios(id),
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS fichas_seguridad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER REFERENCES productos(id),
    nombre_producto TEXT NOT NULL,
    numero_cas TEXT,
    clase_peligro TEXT,
    pictogramas TEXT DEFAULT '[]',
    epi_requerido TEXT DEFAULT '[]',
    temperatura_almacenamiento TEXT,
    incompatibilidades TEXT,
    version TEXT DEFAULT '1.0',
    fecha_revision TEXT,
    ruta_pdf TEXT,
    activo INTEGER DEFAULT 1
);

-- RRHH
CREATE TABLE IF NOT EXISTS empleados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    dni TEXT,
    email TEXT,
    telefono TEXT,
    departamento TEXT NOT NULL,
    cargo TEXT,
    fecha_alta TEXT,
    fecha_baja TEXT,
    tipo_contrato TEXT,
    jornada TEXT DEFAULT 'completa',
    estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo','baja_temporal','baja_definitiva','vacaciones')),
    usuario_id INTEGER REFERENCES usuarios(id),
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fichajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    fecha TEXT NOT NULL,
    hora_entrada TEXT,
    hora_salida TEXT,
    tipo TEXT DEFAULT 'normal',
    incidencia TEXT
);

CREATE TABLE IF NOT EXISTS vacaciones_solicitudes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    dias INTEGER,
    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente','aprobada','denegada','cancelada')),
    motivo TEXT,
    aprobado_por INTEGER REFERENCES empleados(id),
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS epis_asignados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    tipo_epi TEXT NOT NULL,
    descripcion TEXT,
    talla TEXT,
    fecha_entrega TEXT,
    proxima_revision TEXT,
    estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo','caducado','deteriorado','devuelto'))
);

-- Mantenimiento
CREATE TABLE IF NOT EXISTS equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    tipo TEXT,
    marca TEXT,
    modelo TEXT,
    numero_serie TEXT,
    ubicacion TEXT,
    fecha_compra TEXT,
    fecha_ultima_revision TEXT,
    fecha_proxima_revision TEXT,
    estado TEXT DEFAULT 'operativo' CHECK(estado IN ('operativo','en_mantenimiento','averiado','baja')),
    notas TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ordenes_mantenimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    equipo_id INTEGER REFERENCES equipos(id),
    tipo TEXT CHECK(tipo IN ('preventivo','correctivo','predictivo','mejora')),
    descripcion TEXT NOT NULL,
    prioridad TEXT DEFAULT 'normal' CHECK(prioridad IN ('baja','normal','alta','urgente')),
    estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente','en_proceso','completada','cancelada')),
    tecnico_id INTEGER REFERENCES empleados(id),
    fecha_apertura TEXT DEFAULT (datetime('now')),
    fecha_cierre TEXT,
    coste REAL DEFAULT 0,
    tiempo_horas REAL DEFAULT 0,
    repuestos TEXT DEFAULT '[]',
    notas TEXT
);

-- Sistemas
CREATE TABLE IF NOT EXISTS logs_actividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    username TEXT,
    accion TEXT NOT NULL,
    modulo TEXT,
    descripcion TEXT,
    ip TEXT,
    nivel TEXT DEFAULT 'INFO' CHECK(nivel IN ('INFO','WARN','ERROR','DEBUG')),
    fecha TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dispositivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    tipo TEXT CHECK(tipo IN ('pc','tablet','lector_qr','impresora','bascula','otro')),
    ubicacion TEXT,
    ip TEXT,
    mac TEXT,
    usuario_asignado INTEGER REFERENCES usuarios(id),
    estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo','inactivo','averiado')),
    ultimo_acceso TEXT,
    notas TEXT,
    creado_en TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backups_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT CHECK(tipo IN ('completo','incremental','semanal')),
    fecha TEXT NOT NULL,
    tamano_mb REAL,
    estado TEXT CHECK(estado IN ('ok','error','en_progreso','warn')),
    ruta TEXT,
    notas TEXT
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_mov_producto ON movimientos(producto_id);
CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos(fecha);
CREATE INDEX IF NOT EXISTS idx_lotes_producto ON lotes(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_caducidad ON lotes(fecha_caducidad);
CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_actividad(fecha);
CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_actividad(usuario_id);
"""


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    seed_if_empty()


# ── Seed data ─────────────────────────────────────────────────────────────────

def seed_if_empty():
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] > 0:
            return
        _seed(conn)
        conn.commit()


def _seed(conn):
    # Roles — new permission schema: {"modulos": [...], "nivel": "readonly"|"admin"}
    roles = [
        # id, nombre, descripcion, permisos
        (1,  "Admin Sistemas",       "Acceso total al sistema",            json.dumps({"modulos": ["*"],             "nivel": "admin"})),
        (18, "Sistemas",            "Sistemas — solo lectura",            json.dumps({"modulos": ["sistemas"],      "nivel": "readonly"})),
        (2,  "Almacén",             "Almacén — solo lectura",             json.dumps({"modulos": ["almacen"],       "nivel": "readonly"})),
        (3,  "Admin Almacén",       "Almacén — acceso completo",          json.dumps({"modulos": ["almacen"],       "nivel": "admin"})),
        (4,  "Producción",          "Producción — solo lectura",          json.dumps({"modulos": ["produccion"],    "nivel": "readonly"})),
        (5,  "Admin Producción",    "Producción — acceso completo",       json.dumps({"modulos": ["produccion"],    "nivel": "admin"})),
        (6,  "Compras",             "Compras — solo lectura",             json.dumps({"modulos": ["compras"],       "nivel": "readonly"})),
        (7,  "Admin Compras",       "Compras — acceso completo",          json.dumps({"modulos": ["compras"],       "nivel": "admin"})),
        (8,  "Ventas",              "Ventas — solo lectura",              json.dumps({"modulos": ["ventas"],        "nivel": "readonly"})),
        (9,  "Admin Ventas",        "Ventas — acceso completo",           json.dumps({"modulos": ["ventas"],        "nivel": "admin"})),
        (10, "Calidad",             "Calidad — solo lectura",             json.dumps({"modulos": ["calidad"],       "nivel": "readonly"})),
        (11, "Admin Calidad",       "Calidad — acceso completo",          json.dumps({"modulos": ["calidad"],       "nivel": "admin"})),
        (12, "RRHH",                "RRHH — solo lectura",                json.dumps({"modulos": ["rrhh"],          "nivel": "readonly"})),
        (13, "Admin RRHH",          "RRHH — acceso completo",             json.dumps({"modulos": ["rrhh"],          "nivel": "admin"})),
        (14, "Mantenimiento",       "Mantenimiento — solo lectura",       json.dumps({"modulos": ["mantenimiento"], "nivel": "readonly"})),
        (15, "Admin Mantenimiento", "Mantenimiento — acceso completo",    json.dumps({"modulos": ["mantenimiento"], "nivel": "admin"})),
        (16, "Informes",            "Informes — solo lectura",            json.dumps({"modulos": ["informes"],      "nivel": "readonly"})),
        (17, "Admin Informes",      "Informes — acceso completo",         json.dumps({"modulos": ["informes"],      "nivel": "admin"})),
    ]
    conn.executemany("INSERT OR IGNORE INTO roles(id,nombre,descripcion,permisos) VALUES(?,?,?,?)", roles)

    # Usuarios — at least 2 per department (one normal, one admin). jgarcia → Admin Sistemas (id=1)
    usuarios = [
        # nombre, apellidos, username, email, password_hash, departamento, rol_id
        ("Jorge",   "García López",    "jgarcia",   "j.garcia@quimicasur.com",    _hash("admin123"), "Sistemas",      1),
        ("David",   "Pardo Sanz",      "dpardo",    "d.pardo@quimicasur.com",     _hash("pass123"),  "Sistemas",      18),
        # Almacén
        ("Antonio", "Jiménez Castro",  "ajimenez",  "a.jimenez@quimicasur.com",   _hash("pass123"),  "Almacén",       2),
        ("Ana",     "Martínez Ruiz",   "amartinez", "a.martinez@quimicasur.com",  _hash("pass123"),  "Almacén",       3),
        # Producción
        ("Felipe",  "Moreno Ramos",    "fmoreno",   "f.moreno@quimicasur.com",    _hash("pass123"),  "Producción",    4),
        ("Pedro",   "González Vega",   "pgonzalez", "p.gonzalez@quimicasur.com",  _hash("pass123"),  "Producción",    5),
        # Compras
        ("Isabel",  "Castillo Díaz",   "icastillo", "i.castillo@quimicasur.com",  _hash("pass123"),  "Compras",       6),
        ("Miguel",  "López Torres",    "mlopez",    "m.lopez@quimicasur.com",     _hash("pass123"),  "Compras",       7),
        # Ventas
        ("Beatriz", "Serrano Ortega",  "bserrano",  "b.serrano@quimicasur.com",   _hash("pass123"),  "Ventas",        8),
        ("Rosa",    "Navarro Jiménez", "rnavarro",  "r.navarro@quimicasur.com",   _hash("pass123"),  "Ventas",        9),
        # Calidad
        ("Lucía",   "Herrera Blanco",  "lherrera",  "l.herrera@quimicasur.com",   _hash("pass123"),  "Calidad",       10),
        ("Laura",   "Ruiz Sánchez",    "lruiz",     "l.ruiz@quimicasur.com",      _hash("pass123"),  "Calidad",       11),
        # RRHH
        ("Javier",  "Campos Molina",   "jcampos",   "j.campos@quimicasur.com",    _hash("pass123"),  "RRHH",          12),
        ("Sara",    "Torres Navarro",  "storres",   "s.torres@quimicasur.com",    _hash("pass123"),  "RRHH",          13),
        # Mantenimiento
        ("Roberto", "Fuentes Peña",    "rfuentes",  "r.fuentes@quimicasur.com",   _hash("pass123"),  "Mantenimiento", 14),
        ("Carlos",  "Vega Moreno",     "cvega",     "c.vega@quimicasur.com",      _hash("pass123"),  "Mantenimiento", 15),
        # Informes
        ("Patricia","Lozano Gil",      "plozano",   "p.lozano@quimicasur.com",    _hash("pass123"),  "Informes",      16),
        ("María",   "Castro Flores",   "mcastro",   "m.castro@quimicasur.com",    _hash("pass123"),  "Informes",      17),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO usuarios(nombre,apellidos,username,email,password_hash,departamento,rol_id) VALUES(?,?,?,?,?,?,?)",
        usuarios,
    )

    # Categorías
    cats = [
        (1, "Tensioactivos", "MP"),
        (2, "Humectantes y emolientes", "MP"),
        (3, "Conservantes", "MP"),
        (4, "Fragancias", "MP"),
        (5, "Espesantes", "MP"),
        (6, "Champús", "PT"),
        (7, "Detergentes", "PT"),
        (8, "Jabones y lavamanos", "PT"),
        (9, "Suavizantes", "PT"),
        (10, "Envases y tapones", "EM"),
        (11, "Cajas y embalaje", "EM"),
        (12, "Productos químicos peligrosos", "QP"),
    ]
    conn.executemany("INSERT OR IGNORE INTO categorias(id,nombre,tipo) VALUES(?,?,?)", cats)

    # Productos
    productos = [
        # Materias primas
        ("MP-0001", "Lauril Sulfato Sódico (SLS) 28%", "Tensioactivo aniónico para espuma", 1, "kg", 850, 200, 2000, "ZA-A-01", None, 2.45),
        ("MP-0002", "Cocamidopropil Betaína 35%", "Tensioactivo anfótero suavizante", 1, "kg", 620, 150, 1500, "ZA-A-02", None, 3.80),
        ("MP-0003", "Glicerina Vegetal 99.5%", "Humectante natural", 2, "kg", 430, 100, 1000, "ZA-B-01", None, 1.90),
        ("MP-0004", "Aceite de Argán", "Emoliente premium", 2, "kg", 85, 20, 200, "ZA-B-02", None, 28.50),
        ("MP-0005", "Metilparabeno", "Conservante antimicrobiano", 3, "kg", 45, 10, 100, "ZA-C-01", None, 12.00),
        ("MP-0006", "Fragancia Floral FG-44", "Aroma floral multiusos", 4, "kg", 62, 15, 150, "ZA-C-02", None, 35.00),
        ("MP-0007", "Fragancia Lavanda LV-12", "Esencia lavanda", 4, "kg", 48, 15, 150, "ZA-C-03", None, 32.00),
        ("MP-0008", "Carbopol 940", "Espesante acrílico", 5, "kg", 120, 30, 300, "ZA-D-01", None, 9.50),
        ("MP-0009", "Cloruro Sódico (NaCl)", "Espesante salino", 5, "kg", 980, 200, 2000, "ZA-D-02", None, 0.35),
        ("MP-0010", "Ácido Cítrico", "Regulador de pH", 12, "kg", 310, 50, 500, "ZE-A-01", None, 1.20),
        ("MP-0011", "Hidróxido Sódico (NaOH)", "Base fuerte - peligroso", 12, "kg", 240, 50, 500, "ZE-A-02", None, 0.80),
        ("MP-0012", "Betaína (extracto coco)", "Tensioactivo suave", 1, "kg", 180, 50, 500, "ZA-A-03", None, 4.20),
        # Producto terminado
        ("PT-0001", "Champú Hidratante Argán 250ml", "Gama premium argán", 6, "ud", 2840, 500, 10000, "ZB-A-01", None, 1.85),
        ("PT-0002", "Champú Lavanda 400ml", "Gama esencial lavanda", 6, "ud", 1620, 300, 8000, "ZB-A-02", None, 1.40),
        ("PT-0003", "Champú Anticaspa 300ml", "Uso medicinal", 6, "ud", 980, 200, 5000, "ZB-A-03", None, 1.60),
        ("PT-0004", "Detergente Lavavajillas 5L", "Uso profesional", 7, "ud", 740, 150, 4000, "ZB-B-01", None, 3.20),
        ("PT-0005", "Detergente Multiusos 1L", "Limpieza general", 7, "ud", 1240, 300, 6000, "ZB-B-02", None, 1.10),
        ("PT-0006", "Lavamanos Neutro 1L", "pH neutro para pieles sensibles", 8, "ud", 860, 200, 5000, "ZB-C-01", None, 0.95),
        ("PT-0007", "Jabón Líquido Fragancia Rosa 500ml", "Uso doméstico", 8, "ud", 1450, 300, 7000, "ZB-C-02", None, 1.20),
        ("PT-0008", "Suavizante Concentrado 2L", "Alta concentración", 9, "ud", 580, 100, 3000, "ZB-D-01", None, 2.40),
        # Envases y embalaje
        ("EM-0001", "Botella HDPE 250ml blanca", "Envase champú gama premium", 10, "ud", 8400, 2000, 30000, "ZC-A-01", None, 0.18),
        ("EM-0002", "Botella HDPE 400ml transparente", "Envase gama esencial", 10, "ud", 6200, 1500, 25000, "ZC-A-02", None, 0.22),
        ("EM-0003", "Tapón dosificador 24/410", "Tapón bomba para lavamanos", 10, "ud", 5400, 1000, 20000, "ZC-B-01", None, 0.12),
        ("EM-0004", "Caja cartón 24 ud", "Embalaje secundario estándar", 11, "ud", 3200, 500, 15000, "ZC-C-01", None, 0.85),
        ("EM-0005", "Film retráctil (rollo 400m)", "Paletizado", 11, "rollo", 28, 5, 50, "ZC-C-02", None, 42.00),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO productos(referencia,nombre,descripcion,categoria_id,unidad,stock_actual,stock_minimo,stock_maximo,ubicacion,proveedor_id,precio_compra) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        productos,
    )

    # Ubicaciones
    ubics = []
    for zona in ["ZA", "ZB", "ZC", "ZD", "ZE"]:
        for pasillo in ["A", "B", "C", "D"]:
            for estante in ["01", "02", "03"]:
                ubics.append((f"{zona}-{pasillo}-{estante}", zona, pasillo, estante, "1", 2000.0, 0.0))
    conn.executemany(
        "INSERT OR IGNORE INTO ubicaciones(codigo,zona,pasillo,estante,nivel,capacidad_kg,ocupado_kg) VALUES(?,?,?,?,?,?,?)",
        ubics,
    )

    # Lotes
    today = date.today()
    lotes = [
        ("LT-2024-001", 1, 500, 500, (today - timedelta(days=30)).isoformat(), (today + timedelta(days=335)).isoformat(), 1, "ALB-4521", 2.45),
        ("LT-2024-002", 2, 300, 300, (today - timedelta(days=20)).isoformat(), (today + timedelta(days=345)).isoformat(), 2, "ALB-3890", 3.80),
        ("LT-2024-003", 3, 200, 200, (today - timedelta(days=15)).isoformat(), (today + timedelta(days=350)).isoformat(), 3, "ALB-7231", 1.90),
        ("LT-2024-004", 6, 100, 85, (today - timedelta(days=10)).isoformat(), (today + timedelta(days=355)).isoformat(), 4, "ALB-2100", 28.50),
        ("LT-2024-005", 13, 5000, 2840, (today - timedelta(days=7)).isoformat(), (today + timedelta(days=358)).isoformat(), None, None, 1.85),
        ("LT-2024-006", 14, 3000, 1620, (today - timedelta(days=5)).isoformat(), (today + timedelta(days=360)).isoformat(), None, None, 1.40),
        ("LT-2024-007", 10, 200, 200, (today - timedelta(days=60)).isoformat(), (today + timedelta(days=25)).isoformat(), None, None, 1.20),  # próx. caducidad
        ("LT-2024-008", 5, 30, 30, (today - timedelta(days=300)).isoformat(), (today + timedelta(days=10)).isoformat(), None, None, 12.00),  # muy próx.
        ("LT-2023-099", 11, 50, 0, (today - timedelta(days=400)).isoformat(), (today - timedelta(days=35)).isoformat(), None, None, 0.80),   # caducado
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO lotes(numero,producto_id,cantidad,cantidad_disponible,fecha_entrada,fecha_caducidad,proveedor_id,numero_alb_proveedor,precio_unitario) VALUES(?,?,?,?,?,?,?,?,?)",
        lotes,
    )

    # Proveedores
    proveedores = [
        ("PROV-001", "QuímicaSur S.L.", "B-41123456", "pedidos@quimicasur.es", "955 234 567", "C/ Industria 14, Sevilla", "Sevilla", "Jorge Molina", 5, "30 días"),
        ("PROV-002", "Tensioactivos del Norte S.A.", "A-08765432", "compras@tensionorte.com", "932 456 789", "Av. Industrial 88, Barcelona", "Barcelona", "Marta Font", 7, "60 días"),
        ("PROV-003", "AgroGlicerina Ibérica", "B-28345678", "info@agroglicerina.es", "916 543 210", "Pol. Ind. Este, Madrid", "Madrid", "Luis García", 10, "30 días"),
        ("PROV-004", "Fragancias Premium S.L.", "B-46234567", "ventas@fragpremium.es", "963 123 456", "C/ Perfumería 3, Valencia", "Valencia", "Ana Belén", 14, "45 días"),
        ("PROV-005", "EnvasesPlás S.A.", "A-17890123", "pedidos@envasesplas.com", "971 234 567", "Pol. Son Castelló, Palma", "Palma", "Pere Roca", 3, "30 días"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO proveedores(codigo,nombre,nif,email,telefono,direccion,ciudad,contacto,plazo_entrega,condiciones_pago) VALUES(?,?,?,?,?,?,?,?,?,?)",
        proveedores,
    )

    # Clientes
    clientes = [
        ("CLI-001", "Distribuciones García e Hijos", "B-41567890", "pedidos@garciahijos.es", "955 678 901", "Av. Distribución 22, Sevilla", "Sevilla", "Ramón García", "30 días", 5.0),
        ("CLI-002", "Supermercados Nova S.A.", "A-28901234", "compras@supernova.es", "916 789 012", "C/ Logística 44, Madrid", "Madrid", "Isabel Ruiz", "60 días", 10.0),
        ("CLI-003", "Perfumerías Meridiano", "B-46890123", "info@meridiano.es", "963 890 123", "Av. Comerç 8, Valencia", "Valencia", "Carmen López", "45 días", 7.5),
        ("CLI-004", "Hostelería del Sur S.L.", "B-11234567", "pedidos@hostelsur.es", "952 123 456", "C/ Hotelería 12, Málaga", "Málaga", "Pedro Jiménez", "30 días", 3.0),
        ("CLI-005", "Limpieza Industrial Noreste", "A-17456789", "compras@limpiainoreste.es", "976 456 789", "Pol. Norte 55, Zaragoza", "Zaragoza", "Jesús Navarro", "30 días", 5.0),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO clientes(codigo,nombre,nif,email,telefono,direccion,ciudad,contacto,condiciones_pago,descuento_pct) VALUES(?,?,?,?,?,?,?,?,?,?)",
        clientes,
    )

    # Órdenes de compra (usuario_id: mlopez=7)
    oc = [
        ("OC-2024-001", 1, today.isoformat(), (today + timedelta(days=5)).isoformat(), "enviada",
         json.dumps([{"producto": "Lauril Sulfato Sódico", "cantidad": 500, "precio": 2.45}]), 1225.0, 7),
        ("OC-2024-002", 4, today.isoformat(), (today + timedelta(days=14)).isoformat(), "borrador",
         json.dumps([{"producto": "Fragancia Floral FG-44", "cantidad": 50, "precio": 35.00}]), 1750.0, 7),
        ("OC-2024-003", 2, (today - timedelta(days=3)).isoformat(), (today + timedelta(days=4)).isoformat(), "confirmada",
         json.dumps([{"producto": "Cocamidopropil Betaína", "cantidad": 300, "precio": 3.80}]), 1140.0, 7),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO ordenes_compra(numero,proveedor_id,fecha,fecha_entrega_prevista,estado,lineas,total,usuario_id) VALUES(?,?,?,?,?,?,?,?)",
        oc,
    )

    # Pedidos venta (usuario_id: rnavarro=9)
    pv = [
        ("PV-2024-001", 1, today.isoformat(), (today + timedelta(days=3)).isoformat(), "confirmado",
         json.dumps([{"producto": "Champú Hidratante Argán 250ml", "cantidad": 240, "precio": 3.20}]), 768.0, 9),
        ("PV-2024-002", 2, today.isoformat(), (today + timedelta(days=5)).isoformat(), "en_preparacion",
         json.dumps([{"producto": "Detergente Lavavajillas 5L", "cantidad": 180, "precio": 5.80}]), 1044.0, 9),
        ("PV-2024-003", 3, (today - timedelta(days=1)).isoformat(), (today + timedelta(days=7)).isoformat(), "pendiente",
         json.dumps([{"producto": "Lavamanos Neutro 1L", "cantidad": 500, "precio": 2.10}]), 1050.0, 9),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO pedidos_venta(numero,cliente_id,fecha,fecha_entrega,estado,lineas,total,usuario_id) VALUES(?,?,?,?,?,?,?,?)",
        pv,
    )

    # Fórmulas
    formulas = [
        ("FOR-001", "Champú Hidratante Argán", 13,  "2.3", 100.0,
         "1. Mezclar agua y SLS a 40°C. 2. Añadir betaína. 3. Agregar glicerina y aceite argán. 4. Ajustar pH con ácido cítrico (5.5-6.5). 5. Perfumar y envasar.",
         json.dumps([{"mp": "MP-0001", "nombre": "Lauril Sulfato Sódico", "pct": 12.0},
                     {"mp": "MP-0002", "nombre": "Cocamidopropil Betaína", "pct": 4.0},
                     {"mp": "MP-0003", "nombre": "Glicerina Vegetal", "pct": 3.0},
                     {"mp": "MP-0004", "nombre": "Aceite de Argán", "pct": 2.0},
                     {"mp": "MP-0006", "nombre": "Fragancia Floral FG-44", "pct": 0.5},
                     {"mp": "MP-0010", "nombre": "Ácido Cítrico", "pct": 0.3}])),
        ("FOR-002", "Champú Lavanda", 14, "1.5", 100.0,
         "1. Calentar agua base a 40°C. 2. Incorporar SLS con agitación. 3. Añadir betaína y NaCl. 4. Perfumar con lavanda. 5. Ajustar pH y envasar.",
         json.dumps([{"mp": "MP-0001", "nombre": "Lauril Sulfato Sódico", "pct": 10.0},
                     {"mp": "MP-0009", "nombre": "Cloruro Sódico", "pct": 2.0},
                     {"mp": "MP-0007", "nombre": "Fragancia Lavanda", "pct": 0.5}])),
        ("FOR-003", "Detergente Lavavajillas 5L", 16, "1.2", 100.0,
         "1. Disolver SLS en agua fría. 2. Agregar betaína y ácido cítrico. 3. Ajustar viscosidad con NaCl. 4. Controlar pH 6.0-7.0. 5. Envasar en garrafas 5L.",
         json.dumps([{"mp": "MP-0001", "nombre": "Lauril Sulfato Sódico", "pct": 15.0},
                     {"mp": "MP-0012", "nombre": "Betaína extracto coco", "pct": 5.0},
                     {"mp": "MP-0010", "nombre": "Ácido Cítrico", "pct": 1.5}])),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO formulas(codigo,nombre,producto_id,version,rendimiento_kg,instrucciones,ingredientes) VALUES(?,?,?,?,?,?,?)",
        formulas,
    )

    # Órdenes de fabricación
    ofs = [
        ("OF-2024-041", 1, 13, 2000.0, 1980.0, (today - timedelta(days=2)).isoformat(), today.isoformat(), today.isoformat(), "completada", 3, "LT-PT-041", 20.0, ""),
        ("OF-2024-042", 2, 14, 1500.0, 0.0, today.isoformat(), None, (today + timedelta(days=1)).isoformat(), "en_proceso", 3, None, 0.0, ""),
        ("OF-2024-043", 3, 16, 3000.0, 0.0, None, None, (today + timedelta(days=3)).isoformat(), "pendiente", 3, None, 0.0, ""),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO ordenes_fabricacion(numero,formula_id,producto_id,cantidad_planificada,cantidad_producida,fecha_inicio,fecha_fin,fecha_planificada,estado,operario_id,lote_producido,merma_kg,notas) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ofs,
    )

    # Empleados (usuario_id references match new user ordering above: jgarcia=1, ajimenez=2, amartinez=3, fmoreno=4, pgonzalez=5, icastillo=6, mlopez=7, bserrano=8, rnavarro=9, lherrera=10, lruiz=11, jcampos=12, storres=13, rfuentes=14, cvega=15, plozano=16, mcastro=17)
    empleados = [
        ("EMP-001", "Ana",     "Martínez Ruiz",   "12345678A", "a.martinez@quimicasur.com", "600 123 456", "Almacén",       "Admin Almacén",        (today - timedelta(days=1825)).isoformat(), None, "indefinido", "completa", "activo",       3),
        ("EMP-002", "Antonio", "Jiménez Castro",  "78901234G", "a.jimenez@quimicasur.com",  "600 789 012", "Almacén",       "Operario Almacén",     (today - timedelta(days=400)).isoformat(),  None, "temporal",   "completa", "activo",       2),
        ("EMP-003", "Pedro",   "González Vega",   "23456789B", "p.gonzalez@quimicasur.com", "600 234 567", "Producción",    "Jefe Producción",      (today - timedelta(days=1200)).isoformat(), None, "indefinido", "completa", "activo",       5),
        ("EMP-004", "Felipe",  "Moreno Ramos",    "99887766X", "f.moreno@quimicasur.com",   "600 111 222", "Producción",    "Técnico Producción",   (today - timedelta(days=600)).isoformat(),  None, "temporal",   "completa", "activo",       4),
        ("EMP-005", "Miguel",  "López Torres",    "45678901D", "m.lopez@quimicasur.com",    "600 456 789", "Compras",       "Responsable Compras",  (today - timedelta(days=730)).isoformat(),  None, "indefinido", "completa", "activo",       7),
        ("EMP-006", "Isabel",  "Castillo Díaz",   "55443322Y", "i.castillo@quimicasur.com", "600 333 444", "Compras",       "Técnico Compras",      (today - timedelta(days=300)).isoformat(),  None, "temporal",   "completa", "activo",       6),
        ("EMP-007", "Rosa",    "Navarro Jiménez", "89012345H", "r.navarro@quimicasur.com",  "600 890 123", "Ventas",        "Jefe Comercial",       (today - timedelta(days=365)).isoformat(),  None, "indefinido", "completa", "activo",       9),
        ("EMP-008", "Beatriz", "Serrano Ortega",  "66554433Z", "b.serrano@quimicasur.com",  "600 555 666", "Ventas",        "Comercial",            (today - timedelta(days=200)).isoformat(),  None, "temporal",   "completa", "activo",       8),
        ("EMP-009", "Laura",   "Ruiz Sánchez",    "34567890C", "l.ruiz@quimicasur.com",     "600 345 678", "Calidad",       "Jefa de Calidad",      (today - timedelta(days=900)).isoformat(),  None, "indefinido", "completa", "activo",       11),
        ("EMP-010", "Lucía",   "Herrera Blanco",  "77665544W", "l.herrera@quimicasur.com",  "600 777 888", "Calidad",       "Técnica de Calidad",   (today - timedelta(days=450)).isoformat(),  None, "temporal",   "completa", "activo",       10),
        ("EMP-011", "Sara",    "Torres Navarro",  "56789012E", "s.torres@quimicasur.com",   "600 567 890", "RRHH",          "Responsable RRHH",     (today - timedelta(days=600)).isoformat(),  None, "indefinido", "completa", "activo",       13),
        ("EMP-012", "Javier",  "Campos Molina",   "88776655V", "j.campos@quimicasur.com",   "600 999 000", "RRHH",          "Técnico RRHH",         (today - timedelta(days=250)).isoformat(),  None, "temporal",   "completa", "activo",       12),
        ("EMP-013", "Carlos",  "Vega Moreno",     "67890123F", "c.vega@quimicasur.com",     "600 678 901", "Mantenimiento", "Jefe Mantenimiento",   (today - timedelta(days=500)).isoformat(),  None, "temporal",   "completa", "baja_temporal",15),
        ("EMP-014", "Roberto", "Fuentes Peña",    "11223344U", "r.fuentes@quimicasur.com",  "600 100 200", "Mantenimiento", "Técnico Mantenimiento",(today - timedelta(days=180)).isoformat(),  None, "temporal",   "completa", "activo",       14),
        ("EMP-015", "María",   "Castro Flores",   "22334455T", "m.castro@quimicasur.com",   "600 200 300", "Informes",      "Responsable Informes", (today - timedelta(days=800)).isoformat(),  None, "indefinido", "completa", "activo",       17),
        ("EMP-016", "Patricia","Lozano Gil",      "33445566S", "p.lozano@quimicasur.com",   "600 300 400", "Informes",      "Analista de Datos",    (today - timedelta(days=150)).isoformat(),  None, "temporal",   "completa", "activo",       16),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO empleados(codigo,nombre,apellidos,dni,email,telefono,departamento,cargo,fecha_alta,fecha_baja,tipo_contrato,jornada,estado,usuario_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        empleados,
    )

    # Equipos de mantenimiento
    equipos = [
        ("EQ-001", "Reactor de mezcla RM-500", "mezcladora", "INOX-Mix", "RM-500L", "SN-20210345", "Línea 1 - Producción", (today - timedelta(days=1000)).isoformat(), (today - timedelta(days=30)).isoformat(), (today + timedelta(days=60)).isoformat(), "operativo"),
        ("EQ-002", "Envasadora automática EA-200", "envasadora", "PackTech", "EA-200", "SN-20190876", "Línea 1 - Envasado", (today - timedelta(days=1500)).isoformat(), (today - timedelta(days=90)).isoformat(), (today + timedelta(days=30)).isoformat(), "operativo"),
        ("EQ-003", "Báscula industrial 2000kg", "bascula", "Mettler Toledo", "ICS669", "SN-20220123", "Zona entrada MP", (today - timedelta(days=700)).isoformat(), (today - timedelta(days=60)).isoformat(), (today + timedelta(days=120)).isoformat(), "operativo"),
        ("EQ-004", "Compresor aire 50L", "compresor", "Atlas Copco", "GX5-50", "SN-20180654", "Sala máquinas", (today - timedelta(days=2000)).isoformat(), (today - timedelta(days=120)).isoformat(), (today + timedelta(days=5)).isoformat(), "en_mantenimiento"),
        ("EQ-005", "Carretilla elevadora eléctrica", "carretilla", "Still", "RX20-16", "SN-20210987", "Almacén central", (today - timedelta(days=1100)).isoformat(), (today - timedelta(days=45)).isoformat(), (today + timedelta(days=75)).isoformat(), "operativo"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO equipos(codigo,nombre,tipo,marca,modelo,numero_serie,ubicacion,fecha_compra,fecha_ultima_revision,fecha_proxima_revision,estado) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        equipos,
    )

    # No conformidades
    ncs = [
        ("NC-2024-001", "Lote MP-0312 fragancia FG-44 no supera prueba olfativa", "Calidad", "alta", "abierta", None, None, "Rechazo de lote y solicitud de sustitución al proveedor", today.isoformat(), None, 4, 4),
        ("NC-2024-002", "Viscosidad fuera de rango en OF-2024-039 — Champú lavanda", "Producción", "media", "en_investigacion", None, None, "Ajuste de fórmula y repetición de análisis", (today - timedelta(days=2)).isoformat(), None, 4, 3),
        ("NC-2024-003", "Etiquetado incorrecto lote PT-2024-015", "Almacén", "baja", "resuelta", 14, None, "Reetiquetado manual del lote completo", (today - timedelta(days=5)).isoformat(), (today - timedelta(days=1)).isoformat(), 2, 2),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO no_conformidades(numero,descripcion,modulo,severidad,estado,producto_id,lote_id,accion_correctiva,fecha_apertura,fecha_cierre,responsable_id,creado_por) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        ncs,
    )

    # Movimientos recientes
    movs = []
    for i in range(15):
        d = today - timedelta(days=i // 3)
        tipo = ["entrada", "salida", "traspaso"][i % 3]
        prod_id = (i % 10) + 1
        movs.append((tipo, prod_id, None, [50, 100, 200, 500][i % 4],
                      "ZA-A-01" if tipo != "entrada" else None,
                      "ZA-A-02" if tipo == "traspaso" else "ZB-A-01" if tipo == "entrada" else None,
                      f"DOC-{1000+i}", 2, "Almacén", "",
                      datetime.combine(d, datetime.min.time()).isoformat()))
    conn.executemany(
        "INSERT OR IGNORE INTO movimientos(tipo,producto_id,lote_id,cantidad,ubicacion_origen,ubicacion_destino,referencia_doc,usuario_id,departamento,notas,fecha) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        movs,
    )

    # Logs recientes
    logs = [
        (2, "amartinez", "Registro entrada", "Almacén", "Entrada lote LT-2024-001 — 500 kg SLS", "192.168.1.45", "INFO"),
        (3, "pgonzalez", "OF completada", "Producción", "OF-2024-041 completada — 1980 kg Champú Argán", "192.168.1.67", "INFO"),
        (4, "lruiz", "No conformidad", "Calidad", "NC-2024-001 abierta — lote MP-0312 rechazado", "192.168.1.88", "WARN"),
        (1, "jgarcia", "Usuario creado", "Sistemas", "Nuevo usuario: m.torres@quimicasur.com", "192.168.1.2", "INFO"),
        (5, "mlopez", "OC enviada", "Compras", "OC-2024-001 enviada a QuímicaSur S.L.", "192.168.1.77", "INFO"),
        (6, "storres", "Vacaciones aprobadas", "RRHH", "Solicitud vacaciones EMP-006 aprobada", "192.168.1.91", "INFO"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO logs_actividad(usuario_id,username,accion,modulo,descripcion,ip,nivel) VALUES(?,?,?,?,?,?,?)",
        logs,
    )

    # Dispositivos
    dispositivos = [
        ("PC-ALM-01", "PC Almacén Principal", "pc", "Almacén — Zona A", "192.168.1.45", "AA:BB:CC:11:22:33", 2, "activo"),
        ("PC-PROD-01", "PC Producción", "pc", "Línea 1 — Producción", "192.168.1.67", "AA:BB:CC:44:55:66", 3, "activo"),
        ("TABLET-ALM-01", "Tablet Almacén 1", "tablet", "Almacén — Zona B", "192.168.1.72", "AA:BB:CC:77:88:99", 9, "activo"),
        ("QR-ALM-01", "Lector QR Entrada", "lector_qr", "Almacén — Entrada", "192.168.1.120", "BB:CC:DD:11:22:33", None, "activo"),
        ("QR-ALM-02", "Lector QR Salida", "lector_qr", "Almacén — Salida", "192.168.1.121", "BB:CC:DD:44:55:66", None, "activo"),
        ("IMP-ALM-01", "Impresora Etiquetas Almacén", "impresora", "Almacén — Expedición", "192.168.1.150", "CC:DD:EE:11:22:33", None, "activo"),
        ("PC-CAL-01", "PC Laboratorio Calidad", "pc", "Laboratorio Calidad", "192.168.1.88", "DD:EE:FF:11:22:33", 4, "activo"),
        ("PC-IT-01", "PC Administración IT", "pc", "Sala Servidores", "192.168.1.2", "EE:FF:00:11:22:33", 1, "activo"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO dispositivos(codigo,nombre,tipo,ubicacion,ip,mac,usuario_asignado,estado) VALUES(?,?,?,?,?,?,?,?)",
        dispositivos,
    )

    # Backups
    bk = []
    for i in range(10):
        d = today - timedelta(days=i)
        tipo = "completo" if i % 3 == 0 else "incremental"
        estado = "ok" if i != 5 else "warn"
        bk.append((tipo, f"{d}T03:00:00", round(800 + i * 12 + (0 if tipo == 'incremental' else 0), 1) if tipo == "completo" else round(100 + i * 5, 1), estado, f"/backups/ga_{d}_{tipo}.bak"))
    conn.executemany(
        "INSERT OR IGNORE INTO backups_registro(tipo,fecha,tamano_mb,estado,ruta) VALUES(?,?,?,?,?)",
        bk,
    )

    # Fichas de seguridad
    fds = [
        (10, "Ácido Cítrico", "77-92-9", "Irritante", json.dumps(["GHS07"]), json.dumps(["guantes nitrilo", "gafas protección"]), "15-25°C, lugar seco", "Incompatible con bases fuertes y oxidantes"),
        (11, "Hidróxido Sódico (NaOH)", "1310-73-2", "Corrosivo", json.dumps(["GHS05", "GHS07"]), json.dumps(["guantes PVC", "gafas herméticas", "delantal PVC", "botas"]), "Almacén separado. Zona ventilada.", "Incompatible con ácidos, aluminio, zinc"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO fichas_seguridad(producto_id,nombre_producto,numero_cas,clase_peligro,pictogramas,epi_requerido,temperatura_almacenamiento,incompatibilidades) VALUES(?,?,?,?,?,?,?,?)",
        fds,
    )

    # EPIs
    epis = [
        (1, "Guantes nitrilo talla L", "Par guantes nitrilo desechables", "L", (today - timedelta(days=90)).isoformat(), (today + timedelta(days=275)).isoformat(), "activo"),
        (1, "Gafas de seguridad", "Gafas policarbonato UV", None, (today - timedelta(days=365)).isoformat(), (today + timedelta(days=0)).isoformat(), "caducado"),
        (2, "Mascarilla FFP2", "Mascarilla protección respiratoria", None, (today - timedelta(days=30)).isoformat(), (today + timedelta(days=335)).isoformat(), "activo"),
        (3, "Bata laboratorio", "Bata algodón ignífugo talla M", "M", (today - timedelta(days=180)).isoformat(), (today + timedelta(days=185)).isoformat(), "activo"),
        (7, "Botas seguridad", "Botas punta acero talla 42", "42", (today - timedelta(days=270)).isoformat(), (today + timedelta(days=95)).isoformat(), "activo"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO epis_asignados(empleado_id,tipo_epi,descripcion,talla,fecha_entrega,proxima_revision,estado) VALUES(?,?,?,?,?,?,?)",
        epis,
    )


# ── Query helpers ─────────────────────────────────────────────────────────────

def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def fetchone(sql: str, params: tuple = ()) -> dict | None:
    with get_db() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    with get_db() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def scalar(sql: str, params: tuple = ()) -> Any:
    with get_db() as conn:
        row = conn.execute(sql, params).fetchone()
    return row[0] if row else None
