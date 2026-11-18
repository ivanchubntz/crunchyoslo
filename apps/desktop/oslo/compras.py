from oslo.db import get_connection

def listar_proveedores():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proveedores ORDER BY nombre ASC')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def agregar_proveedor(nombre, contacto="", telefono=""):
    if not nombre.strip():
        return False, "El nombre del proveedor es obligatorio."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO proveedores (nombre, contacto, telefono) VALUES (?, ?, ?)',
                       (nombre.strip(), contacto.strip(), telefono.strip()))
        conn.commit()
        return True, f"Proveedor '{nombre.strip()}' agregado."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def registrar_compra(proveedor_id, producto_id, cantidad, costo_unitario):
    if cantidad <= 0 or costo_unitario <= 0:
        return False, "La cantidad y el costo unitario deben ser mayores a cero."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nombre FROM productos WHERE id = ?', (producto_id,))
        prod = cursor.fetchone()
        if not prod:
            return False, "El producto seleccionado no existe."

        total = round(cantidad * costo_unitario, 2)

        cursor.execute('''
            INSERT INTO compras (proveedor_id, producto_id, cantidad, total)
            VALUES (?, ?, ?, ?)
        ''', (proveedor_id, producto_id, cantidad, total))

        cursor.execute('''
            UPDATE productos SET stock = stock + ?, precio_costo = ? WHERE id = ?
        ''', (cantidad, costo_unitario, producto_id))

        cursor.execute('''
            INSERT INTO transacciones (tipo, monto, descripcion)
            VALUES ('EGRESO', ?, ?)
        ''', (total, f"Compra: {cantidad}x {prod['nombre']}"))

        conn.commit()
        return True, f"Compra registrada por ${total:,.2f}. Stock incrementado en +{cantidad}."
    except Exception as e:
        conn.rollback()
        return False, f"Error en transacción de compra: {e}"
    finally:
        conn.close()

def editar_compra(compra_id, nuevo_proveedor_id, nueva_cantidad, nuevo_costo):
    """Actualiza una compra existente revirtiendo el impacto anterior y aplicando el nuevo."""
    if nueva_cantidad <= 0 or nuevo_costo <= 0:
        return False, "La cantidad y el costo unitario deben ser mayores a cero."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM compras WHERE id = ?', (compra_id,))
        compra_ant = cursor.fetchone()
        if not compra_ant:
            return False, "La compra seleccionada no existe."

        prod_id = compra_ant['producto_id']
        cant_ant = compra_ant['cantidad'] or 0
        total_ant = compra_ant['total'] or 0.0

        cursor.execute('SELECT stock, nombre FROM productos WHERE id = ?', (prod_id,))
        prod = cursor.fetchone()
        if not prod:
            return False, "El producto asociado ya no existe."

        if (prod['stock'] - cant_ant + nueva_cantidad) < 0:
            return False, "No se puede reducir tanto la cantidad porque parte de ese stock ya fue vendido."

        nuevo_total = round(nueva_cantidad * nuevo_costo, 2)
        diferencia_monto = round(nuevo_total - total_ant, 2)

        cursor.execute('''
            UPDATE productos SET stock = stock - ? + ?, precio_costo = ? WHERE id = ?
        ''', (cant_ant, nueva_cantidad, nuevo_costo, prod_id))

        cursor.execute('''
            UPDATE compras SET proveedor_id = ?, cantidad = ?, total = ? WHERE id = ?
        ''', (nuevo_proveedor_id, nueva_cantidad, nuevo_total, compra_id))

        if diferencia_monto > 0:
            cursor.execute('''
                INSERT INTO transacciones (tipo, monto, descripcion)
                VALUES ('EGRESO', ?, ?)
            ''', (diferencia_monto, f"Ajuste (+) Compra #{compra_id} ({prod['nombre']})"))
        elif diferencia_monto < 0:
            cursor.execute('''
                INSERT INTO transacciones (tipo, monto, descripcion)
                VALUES ('INGRESO', ?, ?)
            ''', (abs(diferencia_monto), f"Reembolso/Ajuste (-) Compra #{compra_id} ({prod['nombre']})"))

        conn.commit()
        return True, f"Compra #{compra_id} actualizada. Nuevo total: ${nuevo_total:,.2f}."
    except Exception as e:
        conn.rollback()
        return False, f"Error al editar compra: {e}"
    finally:
        conn.close()

def eliminar_compra(compra_id):
    """Elimina una compra, descuenta el stock que ingresó y registra el reembolso en caja."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM compras WHERE id = ?', (compra_id,))
        compra = cursor.fetchone()
        if not compra:
            return False, "La compra seleccionada no existe."

        prod_id = compra['producto_id']
        cant = compra['cantidad'] or 0
        total = compra['total'] or 0.0

        cursor.execute('SELECT stock, nombre FROM productos WHERE id = ?', (prod_id,))
        prod = cursor.fetchone()

        if prod:
            if prod['stock'] < cant:
                return False, f"No se puede eliminar: el stock actual de '{prod['nombre']}' ({prod['stock']}) es menor a la compra ({cant})."
            cursor.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cant, prod_id))
            nombre_prod = prod['nombre']
        else:
            nombre_prod = f"Prod ID {prod_id}"

        cursor.execute('DELETE FROM compras WHERE id = ?', (compra_id,))

        if total > 0:
            cursor.execute('''
                INSERT INTO transacciones (tipo, monto, descripcion)
                VALUES ('INGRESO', ?, ?)
            ''', (total, f"Anulación Compra #{compra_id} ({nombre_prod})"))

        conn.commit()
        return True, f"Compra #{compra_id} eliminada. Stock descontado (-{cant}) y caja ajustada."
    except Exception as e:
        conn.rollback()
        return False, f"Error al eliminar compra: {e}"
    finally:
        conn.close()

def listar_compras(limite=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.fecha, c.proveedor_id, c.producto_id, p.nombre AS producto, pr.nombre AS proveedor, c.cantidad, c.total
        FROM compras c
        LEFT JOIN productos p ON c.producto_id = p.id
        LEFT JOIN proveedores pr ON c.proveedor_id = pr.id
        ORDER BY c.id DESC LIMIT ?
    ''', (limite,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
