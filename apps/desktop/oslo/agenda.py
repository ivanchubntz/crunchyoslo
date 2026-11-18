from oslo.db import get_connection

# --- EVENTOS DE CALENDARIO ---
def agregar_evento(fecha, hora, tipo, titulo, descripcion=""):
    if not fecha.strip() or not titulo.strip():
        return False, "La fecha y el título del evento son obligatorios."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO eventos (fecha, hora, tipo, titulo, descripcion, completado)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (fecha.strip(), hora.strip() or "09:00", tipo.strip(), titulo.strip(), descripcion.strip()))
        conn.commit()
        return True, f"Evento '{titulo.strip()}' agendado para el {fecha.strip()}."
    except Exception as e:
        return False, f"Error al agendar evento: {e}"
    finally:
        conn.close()

def listar_eventos(filtro_fecha=""):
    conn = get_connection()
    cursor = conn.cursor()
    if filtro_fecha.strip():
        cursor.execute('''
            SELECT * FROM eventos WHERE fecha LIKE ?
            ORDER BY completado ASC, fecha ASC, hora ASC
        ''', (f"%{filtro_fecha.strip()}%",))
    else:
        cursor.execute('SELECT * FROM eventos ORDER BY completado ASC, fecha ASC, hora ASC')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def alternar_estado_evento(evento_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE eventos SET completado = CASE WHEN completado = 1 THEN 0 ELSE 1 END WHERE id = ?', (evento_id,))
        conn.commit()
        return True, "Estado del evento actualizado."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def eliminar_evento(evento_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM eventos WHERE id = ?', (evento_id,))
        conn.commit()
        return True, "Evento eliminado del calendario."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

# --- BLOC DE NOTAS ---
def guardar_nota(titulo, contenido, nota_id=None):
    if not titulo.strip():
        return False, "El título de la nota es obligatorio."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if nota_id:
            cursor.execute('''
                UPDATE notas SET titulo = ?, contenido = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (titulo.strip(), contenido.strip(), nota_id))
            msg = "Nota actualizada correctamente."
        else:
            cursor.execute('''
                INSERT INTO notas (titulo, contenido) VALUES (?, ?)
            ''', (titulo.strip(), contenido.strip()))
            msg = "Nueva nota guardada."
        conn.commit()
        return True, msg
    except Exception as e:
        return False, f"Error al guardar nota: {e}"
    finally:
        conn.close()

def listar_notas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notas ORDER BY fecha_actualizacion DESC, id DESC')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def eliminar_nota(nota_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM notas WHERE id = ?', (nota_id,))
        conn.commit()
        return True, "Nota eliminada."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()
