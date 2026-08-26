from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def setup_logger() -> tuple[logging.Logger, Path]:
    """Configura la salida por consola y crea un archivo de log por ejecución."""
    project_root = Path(__file__).resolve().parents[2]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_path = logs_dir / f"facturas_{datetime.now():%Y%m%d_%H%M%S}.txt"
    logger = logging.getLogger("auto_facturas")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger, log_path
