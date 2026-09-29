# Báscula

App web para la báscula de cocina Bluetooth **Silvergear Smart Food Scale** (modelo 4454): cuenta calorías pesando de verdad, con recetas ajustadas a tus calorías, menú semanal, lista de la compra compartida y escáner de códigos de barras.

## Cómo usarla
1. Instala **Bluefy** (gratis en la App Store). Safari no permite Bluetooth.
2. Abre en Bluefy la dirección de GitHub Pages de este repositorio.
3. Enciende la báscula, cierra la app Silvergear Fit y pulsa **Conectar**.

Dentro de la app, el botón **?** abre la guía de uso completa.

## Datos
Los datos se guardan en el móvil. Con la copia en GitHub (Ajustes) se guardan también en un repositorio **privado** aparte, nunca en este.

## Protocolo de la báscula
Servicio BLE `0xFFB0`, notificaciones en `0xFFB2`. Tramas de 20 bytes: `AC 40` cabecera · byte 3 `01` positivo / `81` negativo · byte 4 unidad · bytes 5-7 peso en mg (big-endian) · penúltimo `A6` · último = suma de los bytes 3 a 19 mod 256.

Productos: [Open Food Facts](https://openfoodfacts.org) (ODbL).
