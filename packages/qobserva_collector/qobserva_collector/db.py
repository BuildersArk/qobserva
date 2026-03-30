from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import load_config

class Base(DeclarativeBase):
    pass

def get_engine():
    cfg = load_config()
    os.makedirs(cfg.data_dir, exist_ok=True)
    db_path = os.path.join(cfg.data_dir, "qobserva.sqlite3")
    return create_engine(f"sqlite:///{db_path}", future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
