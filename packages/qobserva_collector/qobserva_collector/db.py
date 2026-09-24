from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session
from .config import load_config

class Base(DeclarativeBase):
    pass

_engines: dict[str, Engine] = {}

def get_engine() -> Engine:
    """
    Engine for the currently configured data dir.

    Resolved on each call (and cached per path) rather than at import time, so the
    tables created by create_app() and the sessions used by requests always point
    at the same database even if QOBSERVA_DATA_DIR is set after import.
    """
    cfg = load_config()
    db_path = os.path.join(cfg.data_dir, "qobserva.sqlite3")
    engine = _engines.get(db_path)
    if engine is None:
        os.makedirs(cfg.data_dir, exist_ok=True)
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        _engines[db_path] = engine
    return engine

def SessionLocal() -> Session:
    return Session(bind=get_engine(), autoflush=False)
