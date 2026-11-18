from oslo.db import get_connection

def registrar_transaccion(tipo, monto, descripcion):
    if monto <= 0 or not descripcion.strip():
        return False, "Monto positivo y descripción son requeridos."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO transacciones (tipo, monto, descripcion)
            VALUES (?, ?, ?)
        ''', (tipo, round(monto, 2), descripcion.strip()))
        conn.commit()
        return True, "Movimiento financiero registrado."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def obtener_balance():
    """Retorna (ingresos, egresos, balance, valor_inventario)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE tipo = 'INGRESO'")
    ingresos = float(cursor.fetchone()['total'])

    cursor.execute("SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE tipo = 'EGRESO'")
    egresos = float(cursor.fetchone()['total'])

    cursor.execute("SELECT COALESCE(SUM(stock * precio_costo), 0) as val FROM productos")
    valor_inv = float(cursor.fetchone()['val'])

    conn.close()
    return ingresos, egresos, (ingresos - egresos), valor_inv

def listar_transacciones(limite=100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transacciones ORDER BY id DESC LIMIT ?', (limite,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
