# Arquitectura

## Componentes

- **Caja de escritorio:** aplicación Python/Tkinter para ventas, compras, clientes, inventario y finanzas.
- **Base local:** SQLite en `apps/desktop/data/oslo.db`, creada al iniciar la aplicación.
- **Puente local:** servidor HTTP de Python en el puerto `8765`; recibe lecturas y las envía a la interfaz de escritorio mediante una cola entre hilos.
- **Lector móvil:** Expo/React Native; usa la cámara para leer códigos y solo conserva los datos de vinculación.

## Vinculación y lectura

1. La caja crea una clave aleatoria y muestra un QR con la dirección local, el puerto y la clave.
2. El móvil lee el QR, comprueba el servicio y guarda la vinculación localmente.
3. El teléfono envía cada código a `POST /api/scan` junto con la clave de sesión.
4. El servicio valida la clave y el formato, consulta el catálogo y entrega el código a la caja.
5. La caja selecciona el producto o permite dar de alta uno nuevo.

El vínculo solo dura mientras la sesión de escritorio está abierta. Al reiniciar la caja se genera otra clave. El servicio no confirma cobros y no debe exponerse a Internet ni reenviarse desde el router.

## Datos

```text
productos: sku, codigo_barras, nombre, categoria, precio_costo,
           precio_venta, stock, stock_minimo
ventas:    cliente_id, producto_id, cantidad, fecha, total
transacciones: tipo, monto, descripcion, fecha
```

El código de barras es texto opcional, único cuando está informado, y separado del SKU. Esto conserva ceros iniciales. Confirmar una venta descuenta stock y registra el ingreso financiero.

## Límites actuales

- Una lectura selecciona un producto; todavía no arma una cesta de varios artículos.
- Un código desconocido abre un formulario con el código y los campos del catálogo.
- La venta solo se registra cuando el cajero la confirma en la computadora.
- El servicio usa HTTP dentro de la red local. La clave aleatoria limita quién puede enviar lecturas; utiliza una red confiable.
- Si el Firewall bloquea la conexión, permite Python en la red privada. No abras el puerto a Internet.
- La aplicación móvil utiliza Expo Camera y Expo SDK 58.
