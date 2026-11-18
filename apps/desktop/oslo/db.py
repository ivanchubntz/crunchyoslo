import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'oslo.db')

def get_connection():
    """Establece y retorna una conexión a la base de datos SQLite con llaves foráneas activas."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _migrar_columnas_faltantes(cursor):
    """Agrega columnas nuevas si existe una base de datos de una versión anterior."""
    for tabla in ("ventas", "compras"):
        cursor.execute(f"PRAGMA table_info({tabla})")
        columnas = [col["name"] for col in cursor.fetchall()]
        if "producto_id" not in columnas:
            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN producto_id INTEGER REFERENCES productos(id)")
        if "cantidad" not in columnas:
            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN cantidad INTEGER DEFAULT 1")

def init_db():
    """Inicializa el esquema de base de datos, migra tablas antiguas e inserta registros base."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            codigo_barras TEXT UNIQUE,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            precio_costo REAL NOT NULL,
            precio_venta REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            contacto TEXT,
            telefono TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT,
            telefono TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total REAL NOT NULL,
            FOREIGN KEY (proveedor_id) REFERENCES proveedores (id),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT CHECK(tipo IN ('INGRESO', 'EGRESO')) NOT NULL,
            monto REAL NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Calendario de eventos y bloc de notas.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            hora TEXT DEFAULT '09:00',
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            completado INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            contenido TEXT NOT NULL,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    _migrar_columnas_faltantes(cursor)

    # Oslo did not have a dedicated barcode field. Keep SKU intact and
    # add an optional barcode so existing catalogs and records remain compatible.
    cursor.execute("PRAGMA table_info(productos)")
    columnas_productos = [col["name"] for col in cursor.fetchall()]
    if "codigo_barras" not in columnas_productos:
        cursor.execute("ALTER TABLE productos ADD COLUMN codigo_barras TEXT")
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_codigo_barras
        ON productos(codigo_barras)
        WHERE codigo_barras IS NOT NULL AND codigo_barras <> ''
    ''')

    cursor.execute("SELECT COUNT(*) as c FROM clientes")
    if cursor.fetchone()['c'] == 0:
        cursor.execute("INSERT INTO clientes (nombre, email, telefono) VALUES ('Consumidor Final', '', '')")

    conn.commit()
    conn.close()
