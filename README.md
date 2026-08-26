# Auto-Facturas

Automatización de teclado en Python para procesar rangos consecutivos de
facturas en cuatro cajas: Hotel, Restaurante, Cafetería y Albergue.

## Instalación en Windows

Desde PowerShell, dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecución

Ejecuta siempre el programa desde la carpeta raíz:

```powershell
python -m src.main
```

Después:

1. Selecciona la caja.
2. Introduce la factura inicial y final (ambas incluidas).
3. Cambia a la ventana del programa durante la cuenta atrás de 5 segundos.
4. No uses el teclado mientras se ejecuta la secuencia.

Cada acción espera 2 segundos. La referencia se escribe como `FRA583`, sin
espacios ni pulsaciones intermedias.

## Seguridad

- Pulsa `H` para solicitar una parada controlada.
- Mueve el ratón rápidamente a la esquina superior izquierda para activar el
  FailSafe de PyAutoGUI.
- También puedes usar `Ctrl+C` desde la consola.

## Logs

Cada sesión crea un archivo independiente en `logs/` con el formato:

```text
facturas_YYYYMMDD_HHMMSS.txt
```

El log registra la caja, el rango, cada factura y todas las acciones enviadas.

## Estructura

```text
Auto-Facturas/
├── logs/
├── src/
│   ├── core/
│   │   ├── logs.py
│   │   └── utils.py
│   ├── flow/
│   │   ├── hotel.py
│   │   ├── restaurante.py
│   │   ├── cafeteria.py
│   │   └── albergue.py
│   └── main.py
├── .gitignore
├── README.md
└── requirements.txt
```

Cada caja tiene un flujo separado para permitir cambios independientes.
