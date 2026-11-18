from oslo.db import get_connection

def agregar_producto(sku, nombre, categoria, precio_costo, precio_venta, stock, stock_minimo=5, codigo_barras=""):
    """Registra un nuevo producto tecnológico. Retorna (exito: bool, mensaje: str)."""
    sku = sku.strip().upper()
    nombre = nombre.strip()
    categoria = categoria.strip()
    codigo_barras = str(codigo_barras or "").strip() or None
    if not sku or not nombre or not categoria:
        return False, "SKU, Nombre y Categoría son obligatorios."
    if precio_costo < 0 or precio_venta < 0 or stock < 0 or stock_minimo < 0:
        return False, "Los valores numéricos no pueden ser negativos."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO productos (sku, codigo_barras, nombre, categoria, precio_costo, precio_venta, stock, stock_minimo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sku, codigo_barras, nombre, categoria, precio_costo, precio_venta, stock, stock_minimo))
        conn.commit()
        return True, f"Producto '{nombre}' ({sku}) registrado correctamente."
    except Exception as e:
        return False, f"Error al registrar producto (¿SKU duplicado?): {e}"
    finally:
        conn.close()

def eliminar_producto(producto_id):
    """Elimina un producto si no tiene historial asociado."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM productos WHERE id = ?', (producto_id,))
        conn.commit()
        return True, "Producto eliminado del catálogo."
    except Exception as e:
        return False, f"No se puede eliminar (puede tener movimientos asociados): {e}"
    finally:
        conn.close()

def listar_productos(filtro=""):
    """Lista productos con búsqueda opcional por SKU, nombre o categoría."""
    conn = get_connection()
    cursor = conn.cursor()
    if filtro.strip():
        like = f"%{filtro.strip()}%"
        cursor.execute('''
            SELECT * FROM productos 
            WHERE sku LIKE ? OR codigo_barras LIKE ? OR nombre LIKE ? OR categoria LIKE ?
            ORDER BY id DESC
        ''', (like, like, like, like))
    else:
        cursor.execute('SELECT * FROM productos ORDER BY id DESC')
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

def buscar_por_codigo_barras(codigo_barras):
    """Busca un producto por su código de barras exacto, preservando ceros iniciales."""
    codigo_barras = str(codigo_barras or "").strip()
    if not codigo_barras:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT * FROM productos WHERE codigo_barras = ?',
            (codigo_barras,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def verificar_stock_bajo():
    """Retorna productos cuyo stock esté igual o por debajo del mínimo."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM productos WHERE stock <= stock_minimo ORDER BY stock ASC')
    alertas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return alertas
