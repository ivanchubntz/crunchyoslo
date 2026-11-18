# Oslo

Sistema local de ventas e inventario con una aplicación de escritorio y un lector móvil de códigos de barras. El teléfono usa su cámara para escanear productos; el catálogo y la caja permanecen en la computadora.

## Funciones

- Punto de venta con selección de cliente, cantidad y confirmación de cada venta.
- Catálogo con SKU, código de barras, precios y control de existencias.
- Lectura de códigos desde un teléfono conectado a la caja por la red local.
- Selección del producto cuando el código ya existe y alta manual cuando es nuevo.
- Compras, proveedores, finanzas, calendario y notas en la aplicación de escritorio.
- Base de datos SQLite local. No requiere una cuenta ni un servicio en la nube.

## Estructura

```text
apps/
  desktop/       Aplicación de caja Python/Tkinter y servicio local
  mobile/        Lector móvil Expo para Android e iOS
docs/            Alcance del producto y arquitectura
```

## Requisitos

- Windows 10/11 y Python 3 con Tcl/Tk para la aplicación de escritorio.
- Node.js 22.13 o posterior y npm para la aplicación móvil.
- Teléfono con Expo Go compatible con Expo SDK 58, o una compilación de desarrollo.

## Inicio rápido

### 1. Preparar la caja de escritorio

Desde `apps/desktop`, instala las dependencias y abre la aplicación:

```powershell
python -m pip install --user -r requirements.txt
```

Luego ejecuta `Iniciar Oslo.bat` desde el Explorador de archivos.

### 2. Iniciar el lector móvil

Desde `apps/mobile`:

```powershell
npm install
npm start
```

Abre Expo Go en el teléfono y escanea el QR que muestra Expo en la terminal o el navegador. Para generar o volver a mostrar el QR de desarrollo, deja el servidor iniciado con `npm start`; Expo lo presenta automáticamente. Si el QR no aparece o la conexión quedó en caché, detén el servidor y ejecuta:

```powershell
npm start -- --clear
```

El teléfono y la computadora deben estar en la misma red Wi-Fi. Permite Node.js en el Firewall de Windows para redes privadas si Windows lo solicita.

### 3. Vincular el lector con la caja

Con la aplicación de escritorio abierta, entra en **Punto de Venta → Conectar móvil**. Escanea desde el teléfono el QR de vinculación que aparece en la computadora. Los dos dispositivos deben permanecer en la misma red local.

## Uso de los códigos

Al escanear un código conocido, la caja selecciona el producto y muestra precio y existencias. Un código nuevo abre el alta manual con el código ya completado. Ninguna venta se registra ni descuenta stock hasta que el cajero la confirma en la computadora.

## Datos y red

La base de datos se crea localmente dentro de `apps/desktop/data/` y se excluye del control de versiones. La clave de vinculación cambia cada vez que se inicia la caja. El puente de red solo debe usarse en una red local confiable; no abras sus puertos a Internet ni los reenvíes desde el router.

Consulta [la guía de escritorio](apps/desktop/README.md), [la guía móvil](apps/mobile/README.md), [la definición del producto](docs/PRODUCT.md) y [la arquitectura](docs/ARCHITECTURE.md).

## Licencia

Pendiente de definir antes de publicar el repositorio.
