# Oslo para escritorio

Aplicación de caja e inventario para Windows, desarrollada con Python, Tkinter y SQLite.

## Requisitos

- Windows 10/11
- Python 3 con Tcl/Tk

Instala las dependencias desde esta carpeta:

```powershell
python -m pip install --user -r requirements.txt
```

Inicia la aplicación con `Iniciar Oslo.bat`.

## Lector móvil

La caja inicia un servicio local en el puerto `8765`. En **Punto de Venta**, elige **Conectar móvil** y escanea el QR desde la app móvil. Ambos dispositivos deben estar conectados a la misma red local.

Una lectura conocida selecciona el producto y muestra precio y existencias. Una lectura desconocida permite crear el producto con el código ya cargado. El código de barras se conserva separado del SKU. La venta solo modifica el stock y registra el ingreso cuando se confirma desde la caja.

Si el teléfono no conecta, confirma que está en la misma Wi-Fi, que la caja sigue abierta y que Windows permitió el acceso de Python en la red privada. También puedes escribir la dirección y la clave temporal que aparecen en la pantalla de vinculación.
