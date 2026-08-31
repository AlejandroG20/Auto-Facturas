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
