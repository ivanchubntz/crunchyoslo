# Definición del producto

## Problema

Dar de alta productos y agregarlos a una venta con teclado es lento y propenso a errores. El teléfono ya tiene una cámara adecuada, pero el catálogo y la operación de caja deben permanecer en la computadora.

## Objetivo

El cajero escanea el código del producto con el teléfono. Si el artículo está en el catálogo, la caja lo selecciona y muestra precio y existencias. Si no está, la computadora permite registrarlo con el código leído ya completado.

El código de barras se almacena en un campo distinto del SKU para no confundir ambos valores y conservar los ceros iniciales. Durante el alta manual, se puede usar el código leído como SKU sugerido y editarlo antes de guardar.

## Personas y contexto

- **Cajero:** escanea artículos y ajusta cantidades desde la caja.
- **Administrador del comercio:** carga productos desconocidos y mantiene precios y códigos.

El MVP está pensado para una caja y un lector móvil conectados a la misma red local.

## Historias de usuario

- Como cajero, quiero vincular el móvil a la caja mediante un QR.
- Como cajero, quiero que un producto conocido quede seleccionado al escanearlo.
- Como cajero, quiero ver nombre, precio y stock antes de confirmar la venta.
- Como cajero, quiero que un código desconocido abra el alta sin perder la operación actual.
- Como administrador, quiero registrar los datos del producto junto con su código de barras.
- Como cajero, quiero poder seguir usando la caja si el teléfono se desconecta.

## Reglas del MVP

- Una lectura selecciona el producto; el cajero elige cliente y cantidad y confirma.
- El código de barras se guarda aparte del SKU como texto para preservar ceros iniciales.
- Un código informado debe ser único. Si ya está asignado, el sistema explica el conflicto.
- El alta conserva SKU, nombre, categoría, costo, precio de venta, stock y stock mínimo.
- Una lectura desconocida no descuenta stock ni registra ingresos.
- Al confirmar, se valida stock, se descuenta inventario y se registra el ingreso.
- Editar o anular una venta ajusta el stock y la caja de forma correspondiente.

## Criterios de aceptación

1. Un código existente selecciona el producto correcto y muestra precio y existencias.
2. El cajero puede elegir cliente y cantidad y confirmar la venta.
3. Un código nuevo abre el alta con ese código ya completado.
4. Guardar un producto lo agrega al catálogo y permite seleccionarlo en la venta.
5. Cancelar el alta no modifica el catálogo, el stock ni la caja.
6. No se puede vender más unidades que las disponibles.
7. El teléfono muestra el resultado de cada lectura y evita duplicados accidentales.
8. Si se pierde la conexión, la caja sigue disponible y el lector informa que está desconectado.

## Fuera de alcance

Facturación fiscal, procesamiento de tarjetas, inventario multi-sucursal, nube, sincronización entre dispositivos, promociones, devoluciones y gestión avanzada de impuestos.
