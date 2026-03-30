from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text
from .db import Base

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[str] = mapped_column(String(64), index=True)
    project: Mapped[str] = mapped_column(String(200), index=True)

    provider: Mapped[str] = mapped_column(String(64), index=True)
    backend_name: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    shots: Mapped[int] = mapped_column(Integer)

    artifact_ref: Mapped[str] = mapped_column(Text)
    analysis_ref: Mapped[str] = mapped_column(Text)
