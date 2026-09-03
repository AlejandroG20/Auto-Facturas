# Auto-Facturas

Auto-Facturas envía automáticamente las pulsaciones necesarias para procesar rangos consecutivos de facturas en Hotel, Restaurante, Cafetería y Albergue.

## Guía rápida

### Qué necesitas

- Un ordenador Windows con Python instalado.
- Fortune4 abierto y preparado en su pantalla inicial habitual.
- No utilizar el teclado ni cambiar de ventana mientras se procesan las facturas.

Auto-Facturas envía pulsaciones, pero no comprueba el resultado contable final. Al terminar, revisa Fortune4.

### Preparar el programa por primera vez

1. Abre PowerShell en la carpeta de Auto-Facturas.
2. Ejecuta estos comandos, uno detrás de otro:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Solo es necesario hacerlo la primera vez. Si falta algún componente, el lanzador mostrará estas instrucciones y esperará antes de cerrarse.

### Cómo abrirlo

La forma más sencilla es hacer doble clic en `iniciar.bat`. El lanzador funciona aunque la carpeta del proyecto contenga espacios.

También puedes abrirlo desde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.main
```

### Cómo procesar un rango

1. Abre Fortune4 y prepara la pantalla habitual.
2. Selecciona la caja.
3. Escribe la primera factura.
4. Escribe la última factura.
5. Revisa el total. La primera y la última también están incluidas.
6. En Hotel o Albergue, selecciona el tipo de facturas.
7. Pulsa **Iniciar**.
8. Durante la cuenta atrás de cinco segundos, selecciona Fortune4.
9. No toques el teclado ni cambies de ventana durante el proceso.

Ejemplo:

```text
Caja: Hotel
Factura inicial: 260002
Factura final: 260005
Total: 4 facturas
```

Se procesarán `260002`, `260003`, `260004` y `260005`. Ambos extremos están incluidos. Las referencias se escriben como `FRA 260002`, con espacio.

### Pausar, continuar y detener

- Pulsa `Ñ` o el botón **Pausar** para detener temporalmente el avance.
- Pulsa **Continuar** y utiliza la nueva cuenta atrás para volver a Fortune4.
- Pulsa **Detener** para cancelar definitivamente. No se enviarán más pulsaciones.
- También puedes llevar el ratón a la esquina superior izquierda para activar la parada de seguridad.

La pausa conserva el punto exacto del proceso. Una pulsación que ya se envió no puede deshacerse.

### Aviso de factura contabilizada

Hotel y Albergue ofrecen tres opciones:

- **Facturas antiguas**: normalmente muestran el aviso.
- **Facturas modernas**: normalmente no muestran el aviso.
- **Detección automática**: comprueba cada factura y decide qué hacer.

Estas opciones nunca envían una confirmación a ciegas. El programa comprueba el aviso antes de aceptarlo y confirma que desapareció. Si encuentra una ventana que no reconoce, se detiene para evitar errores.

### Recuperar la última configuración

**Recuperar última configuración** rellena la caja, el rango y las opciones usadas anteriormente. No inicia ni reanuda el proceso. Si intentas iniciar exactamente el mismo rango, la aplicación te avisará porque podrían repetirse facturas.

### Guía de uso

La guía se muestra automáticamente al principio y está siempre disponible desde **Guía de uso** cuando no hay un proceso activo. Puedes desactivar o volver a activar su apertura automática mediante la casilla **No mostrar automáticamente al iniciar**. Cerrar la guía nunca inicia facturas.

### Problemas frecuentes

**El botón Iniciar está desactivado**

Cierra primero la guía de bienvenida o espera a que termine el proceso actual.

**El total muestra una raya**

Comprueba que ambos campos contienen números y que la última factura no es menor que la primera.

**El programa se detuvo porque no reconoce una ventana**

Revisa qué muestra Fortune4, vuelve a su pantalla habitual e inicia de nuevo cuando sea seguro.

**El lanzador indica que faltan componentes**

Sigue los comandos que aparecen en la ventana. Esta permanecerá abierta para que puedas leerlos.

**La tecla Ñ no pausa**

En algunos equipos puede ser necesario abrir la aplicación con permisos suficientes para registrar la tecla global.

## Información técnica

### Estructura

```text
src/main.py                 Entrada de la aplicación
src/gui/app.py              Ventana, guía y cola de mensajes
src/gui/model.py            Estados y validaciones de la interfaz
src/core/runner.py          Ejecución en segundo plano
src/core/utils.py           Pausas, parada y acciones seguras
src/core/persistence.py     Configuración local
src/core/notice.py          Coordinación del aviso contabilizado
src/core/window_detection.py Detección de ventanas Win32
src/flow/                   Secuencias independientes por caja
tests/                      Pruebas simuladas
```

### Dependencias y comandos

Las dependencias están declaradas en `requirements.txt`: CustomTkinter, PyAutoGUI, keyboard y PyInstaller.

Comprobar sintaxis y ejecutar las pruebas:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan simulaciones y no envían pulsaciones reales.

### Configuración y logs

Los datos se guardan fuera del repositorio:

```text
%LOCALAPPDATA%\Auto-Facturas\config.json
%LOCALAPPDATA%\Auto-Facturas\logs\
```

El botón **Limpiar pantalla** vacía únicamente el panel visible. Nunca borra el archivo de log. Las configuraciones antiguas que no contienen el modo del aviso siguen siendo compatibles.

### Detección del aviso

La ventana activa y sus controles se leen mediante Win32, sin coordenadas fijas. La comparación tolera mayúsculas, acentos, espacios duplicados y saltos de línea, pero rechaza mensajes diferentes.

Si Fortune4 no expone el texto en el PC del hotel, hará falta incorporar una plantilla visual pequeña a partir de la captura original. No debe compararse la pantalla completa.

### Crear el ejecutable

```powershell
.\.venv\Scripts\pyinstaller.exe --clean Auto-Facturas.spec
```

El resultado queda en `dist\Auto-Facturas.exe`. Debe validarse en el ordenador del hotel con Fortune4 disponible, sin utilizar facturas reales, comprobando escalado, permisos de la tecla global, parada de seguridad y detección del aviso.
