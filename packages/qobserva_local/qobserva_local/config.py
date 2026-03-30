from __future__ import annotations

import os
from dataclasses import dataclass
from platformdirs import user_data_dir

@dataclass(frozen=True)
class LocalStackConfig:
    data_dir: str
    collector_host: str
    collector_port: int
    ui_host: str
    ui_port: int

def load_config() -> LocalStackConfig:
    data_dir = os.getenv("QOBSERVA_DATA_DIR") or user_data_dir("qobserva", "qobserva")
    collector_host = os.getenv("QOBSERVA_COLLECTOR_HOST", "127.0.0.1")
    collector_port = int(os.getenv("QOBSERVA_COLLECTOR_PORT", "8080"))
    ui_host = os.getenv("QOBSERVA_UI_HOST", "127.0.0.1")
    ui_port = int(os.getenv("QOBSERVA_UI_PORT", "3000"))  # React dashboard port
    return LocalStackConfig(
        data_dir=data_dir,
        collector_host=collector_host,
        collector_port=collector_port,
        ui_host=ui_host,
        ui_port=ui_port,
    )
