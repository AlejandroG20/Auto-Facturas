# Auto-Facturas

Aplicación de escritorio para ejecutar secuencias de teclado sobre rangos consecutivos de facturas en Hotel, Restaurante, Cafetería y Albergue.

## Instalación en Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No se instalan dependencias automáticamente. Si `iniciar.bat` detecta que falta el entorno o una dependencia, muestra los comandos necesarios.

## Ejecución

Haz doble clic en `iniciar.bat` o ejecuta:

```powershell
.\.venv\Scripts\python.exe -m src.main
```

1. Abre y prepara el programa de facturación.
2. Selecciona la caja e introduce el rango inclusivo.
3. Revisa el total y pulsa **Iniciar**.
4. Durante los 5 segundos de cuenta atrás, selecciona la ventana de facturación.
5. No escribas ni cambies de ventana mientras se ejecuta.

Cada acción conserva la espera existente de 2 segundos. Las referencias se escriben como `FRA 260002`, con espacio.

## Controles y seguridad

- `Ñ`: pausa o continúa al soltar la tecla. La tecla se suprime y no se escribe en la otra aplicación.
- **Pausar**: detiene el avance; **Continuar** ofrece 5 segundos para volver a la otra ventana.
- **Detener**: cancela definitivamente, incluso durante una pausa o cuenta atrás.
- Esquina superior izquierda del ratón: FailSafe de PyAutoGUI, también comprobado antes de texto enviado mediante `keyboard`.

La pausa conserva la factura, el paso, la posición dentro del texto y el tiempo pendiente. Una pulsación que ya fue enviada no puede deshacerse. El progreso significa que la secuencia de teclado terminó; no confirma que la factura haya sido verificada por el programa externo.

## Última configuración y guía

La caja y el rango se guardan al solicitar un inicio válido. **Última configuración** solo rellena los campos: no inicia ni reanuda el trabajo y puede repetir facturas de una ejecución interrumpida.

La guía aparece al iniciar salvo que se marque **No mostrar al iniciar**, y siempre está disponible en **Ayuda → Guía de uso**.

Los datos locales se guardan fuera del repositorio:

```text
%LOCALAPPDATA%\Auto-Facturas\config.json
%LOCALAPPDATA%\Auto-Facturas\logs\
```

Los archivos inexistentes, dañados o incompatibles se ignoran de forma segura.

## Pruebas seguras

Las pruebas usan mocks y no envían pulsaciones reales:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Crear el ejecutable

```powershell
.\.venv\Scripts\pyinstaller.exe --clean Auto-Facturas.spec
```

El resultado queda en `dist\Auto-Facturas.exe`. El `.spec` incluye los recursos de CustomTkinter. El ejecutable debe validarse en un Windows con el programa de facturación disponible, comprobando permisos del atajo global, escalado, FailSafe y las cuatro cajas; nunca con facturas reales.

## Estructura principal

```text
src/main.py              Entrada de la interfaz
src/gui/app.py           Ventana, guía y cola de eventos
src/core/runner.py       Hilo y ciclo de ejecución
src/core/utils.py        pausas, parada y acciones seguras
src/core/persistence.py  configuración local
src/flow/                secuencias independientes por caja
tests/test_core.py       pruebas simuladas
```

## Aviso de factura contabilizada

Los flujos de **Hotel** y **Albergue** comprueban automáticamente el aviso de factura contabilizada después de las confirmaciones iniciales y antes de continuar con `F12`. El selector ofrece tres modos:

- **Facturas antiguas**: úsalo cuando esperas que aparezca el aviso.
- **Facturas modernas**: úsalo cuando normalmente no aparece. Si aparece inesperadamente, también se detecta y acepta.
- **Detección automática**: comprueba cada factura sin presuponer el resultado.

El modo indica el comportamiento esperado, pero nunca provoca una confirmación a ciegas. El aviso solo se acepta cuando la ventana activa y su mensaje coinciden; después se comprueba que haya desaparecido. Si se reconoce `REPFAC`, el flujo sigue sin enviar un `Enter` adicional. Ante una pantalla desconocida o un aviso que no se cierra, la automatización se detiene y registra el motivo.

Aviso observado:

- Título: `Fortune4 para Windows - Green Software (RED)`
- Mensaje: `Factura contabilizada, no deben modificarse datos económicos`
- Botón: `Aceptar`
- Título de la ventana normal del proceso: `Repeticion de Facturas - REPFAC`

#### Método de detección

La detección actual utiliza Win32 para leer la ventana activa y sus controles, sin coordenadas fijas. Normaliza mayúsculas, acentos, espacios duplicados y saltos de línea, pero no acepta mensajes diferentes.

Si Fortune4 no expone el texto de sus controles en el PC del hotel, será necesaria la captura original para añadir la detección visual secundaria. Debe proporcionarse una captura sin recortar; a partir de ella se guardará en recursos una plantilla pequeña de una zona estable del mensaje o del botón `Aceptar`, nunca una comparación de la pantalla completa. La plantilla aún no se incluye porque la captura no estaba disponible en el adjunto recibido.

#### Registro

Genera mensajes claros como:

```text
HOTEL | Factura 260001 | Aviso de factura contabilizada detectado y aceptado
HOTEL | Factura 260002 | Aviso no mostrado; continúa el flujo normal
ALBERGUE | Factura 260003 | Pantalla desconocida; automatización detenida
```

#### Seguridad y pruebas

- No enviar nunca la confirmación adicional sin detectar previamente el aviso.
- Respetar la pausa con `Ñ`, la detención y el FailSafe existentes.
- No cambiar las secuencias actuales de Hotel y Albergue que no estén relacionadas con este aviso.
- Las pruebas automatizadas usan detectores y pulsaciones simuladas; no abren Fortune4 ni emiten facturas reales.
- Cubren aviso presente, aviso ausente, pantalla desconocida, aviso distinto, cierre fallido, pausa, parada y aparición inesperada en modo **Facturas modernas**.
