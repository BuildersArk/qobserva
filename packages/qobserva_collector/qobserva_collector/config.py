from __future__ import annotations

import os
from dataclasses import dataclass
from platformdirs import user_data_dir

@dataclass(frozen=True)
class CollectorConfig:
    data_dir: str
    require_token: bool
    token: str | None

def load_config() -> CollectorConfig:
    data_dir = os.getenv("QOBSERVA_DATA_DIR") or user_data_dir("qobserva", "qobserva")
    token = os.getenv("QOBSERVA_LOCAL_TOKEN")
    return CollectorConfig(
        data_dir=data_dir,
        require_token=bool(token),
        token=token,
    )
