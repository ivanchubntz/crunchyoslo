from oslo.db import get_connection

def listar_clientes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes ORDER BY nombre ASC')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def agregar_cliente(nombre, email="", telefono=""):
    if not nombre.strip():
        return False, "El nombre del cliente es obligatorio."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO clientes (nombre, email, telefono) VALUES (?, ?, ?)',
                       (nombre.strip(), email.strip(), telefono.strip()))
        conn.commit()
        return True, f"Cliente '{nombre.strip()}' agregado."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def registrar_venta(cliente_id, producto_id, cantidad):
    if cantidad <= 0:
        return False, "La cantidad a vender debe ser mayor a cero."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT stock, precio_venta, nombre FROM productos WHERE id = ?', (producto_id,))
        producto = cursor.fetchone()
        if not producto:
            return False, "El producto seleccionado no existe."

        if producto['stock'] < cantidad:
            return False, f"Stock insuficiente para '{producto['nombre']}'. Disponible: {producto['stock']} uds."

        total = round(cantidad * producto['precio_venta'], 2)

        cursor.execute('''
            INSERT INTO ventas (cliente_id, producto_id, cantidad, total)
            VALUES (?, ?, ?, ?)
        ''', (cliente_id, producto_id, cantidad, total))

        cursor.execute('''
            UPDATE productos SET stock = stock - ? WHERE id = ?
        ''', (cantidad, producto_id))

        cursor.execute('''
            INSERT INTO transacciones (tipo, monto, descripcion)
            VALUES ('INGRESO', ?, ?)
        ''', (total, f"Venta: {cantidad}x {producto['nombre']}"))

        conn.commit()
        return True, f"Venta registrada con éxito por ${total:,.2f}."
    except Exception as e:
        conn.rollback()
        return False, f"Error en transacción de venta: {e}"
    finally:
        conn.close()

def editar_venta(venta_id, nuevo_cliente_id, nueva_cantidad):
    """Actualiza una venta revirtiendo el stock anterior y aplicando la nueva cantidad."""
    if nueva_cantidad <= 0:
        return False, "La cantidad debe ser mayor a cero."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,))
        venta_ant = cursor.fetchone()
        if not venta_ant:
            return False, "La venta seleccionada no existe."

        prod_id = venta_ant['producto_id']
        cant_ant = venta_ant['cantidad'] or 0
        total_ant = venta_ant['total'] or 0.0

        cursor.execute('SELECT stock, precio_venta, nombre FROM productos WHERE id = ?', (prod_id,))
        producto = cursor.fetchone()
        if not producto:
            return False, "El producto asociado ya no existe."

        stock_disponible_total = producto['stock'] + cant_ant
        if stock_disponible_total < nueva_cantidad:
            return False, f"Stock insuficiente para actualizar. Máximo disponible: {stock_disponible_total} uds."

        precio_unit = round(total_ant / cant_ant, 2) if cant_ant > 0 else producto['precio_venta']
        nuevo_total = round(nueva_cantidad * precio_unit, 2)
        diferencia_monto = round(nuevo_total - total_ant, 2)

        cursor.execute('UPDATE productos SET stock = stock + ? - ? WHERE id = ?', (cant_ant, nueva_cantidad, prod_id))

        cursor.execute('''
            UPDATE ventas SET cliente_id = ?, cantidad = ?, total = ? WHERE id = ?
        ''', (nuevo_cliente_id, nueva_cantidad, nuevo_total, venta_id))

        if diferencia_monto > 0:
            cursor.execute('''
                INSERT INTO transacciones (tipo, monto, descripcion)
                VALUES ('INGRESO', ?, ?)
            ''', (diferencia_monto, f"Ajuste (+) Venta #{venta_id} ({producto['nombre']})"))
        elif diferencia_monto < 0:
            cursor.execute('''
                INSERT INTO transacciones (tipo, monto, descripcion)
                VALUES ('EGRESO', ?, ?)
            ''', (abs(diferencia_monto), f"Devolución/Ajuste (-) Venta #{venta_id} ({producto['nombre']})"))

        conn.commit()
        return True, f"Venta #{venta_id} actualizada. Nuevo total: ${nuevo_total:,.2f}."
    except Exception as e:
        conn.rollback()
        return False, f"Error al editar venta: {e}"
    finally:
        conn.close()

def eliminar_venta(venta_id):
    """Anula/elimina una venta, devuelve las unidades al stock y registra el egreso de devolución."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,))
        venta = cursor.fetchone()
        if not venta:
            return False, "La venta seleccionada no existe."

        prod_id = venta['producto_id']
        cant = venta['cantidad'] or 0
        total = venta['total'] or 0.0

        cursor.execute('SELECT nombre FROM productos WHERE id = ?', (prod_id,))
        prod = cursor.fetchone()

        if prod:
            cursor.execute('UPDATE productos SET stock = stock + ? WHERE id = ?', (cant, prod_id))
            nombre_prod = prod['nombre']
        else:
            nombre_prod = f"Prod ID {prod_id}"

        cursor.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))

        if total > 0:
            cursor.execute('''
                INSERT INTO transacciones (tipo, monto, descripcion)
                VALUES ('EGRESO', ?, ?)
            ''', (total, f"Anulación Venta #{venta_id} ({nombre_prod})"))

        conn.commit()
        return True, f"Venta #{venta_id} eliminada. Stock devuelto (+{cant}) y caja ajustada."
    except Exception as e:
        conn.rollback()
        return False, f"Error al eliminar venta: {e}"
    finally:
        conn.close()

def listar_ventas(limite=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.id, v.fecha, v.cliente_id, v.producto_id, p.nombre AS producto, c.nombre AS cliente, v.cantidad, v.total
        FROM ventas v
        LEFT JOIN productos p ON v.producto_id = p.id
        LEFT JOIN clientes c ON v.cliente_id = c.id
        ORDER BY v.id DESC LIMIT ?
    ''', (limite,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
