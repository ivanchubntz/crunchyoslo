# Oslo para móvil

Lector Expo para vincular el teléfono con la caja y leer códigos de barras con la cámara. El catálogo, los clientes y las ventas se guardan en la computadora.

## Requisitos

- Node.js 22.13 o posterior
- Expo Go compatible con Expo SDK 58, o una compilación de desarrollo
- Teléfono y computadora en la misma red Wi-Fi

## Instalar e iniciar

Desde esta carpeta:

```powershell
npm install
npm start
```

Expo muestra automáticamente en la terminal o el navegador el QR para abrir la app. Escanéalo con Expo Go. Para regenerar el QR y limpiar la caché de desarrollo, detén el servidor con `Ctrl+C` y ejecuta:

```powershell
npm start -- --clear
```

## Vincular con la caja

Abre la caja en la computadora, ve a **Punto de Venta → Conectar móvil** y escanea el QR de vinculación que aparece en la computadora. Si no puedes usar la cámara para vincular, ingresa manualmente la dirección y la clave temporal.

La app solicita acceso a la cámara y guarda la vinculación en el almacenamiento local del teléfono. **Cambiar caja** borra la vinculación guardada.

La comunicación con la caja utiliza HTTP en la red local. No expongas el puerto `8765` a Internet ni lo reenvíes desde el router. En iOS, acepta el permiso para encontrar dispositivos en la red local.
