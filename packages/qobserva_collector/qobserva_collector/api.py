from __future__ import annotations

import os
from importlib import metadata
from typing import Any, Dict, Optional
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import load_config
from .db import Base, get_engine, SessionLocal
from .models import Run
from .schema import validate_event_dict
from .storage import (
    store_event_bundle, load_event_bundle,
    store_analysis_bundle, load_analysis_bundle,
)
from .analysis import compute_metrics_and_insights

def create_app() -> FastAPI:
    app = FastAPI(title="QObserva Collector", version="0.1.3")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=get_engine())

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _get_installed_version(dist_name: str) -> str:
        try:
            return metadata.version(dist_name)
        except metadata.PackageNotFoundError:
            return "unknown"

    def _dist_version_or_none(dist_name: str) -> str | None:
        try:
            return metadata.version(dist_name)
        except metadata.PackageNotFoundError:
            return None

    def _enrich_software_versions(ev: Dict[str, Any]) -> None:
        """
        Fill missing software.* version strings from this collector's environment.

        Client telemetry is preferred when present; this only backfills gaps so
        stored run artifacts and Run Details stay useful for older agents or sparse payloads.
        """
        sw = ev.get("software")
        if sw is None:
            sw = {}
            ev["software"] = sw
        if not isinstance(sw, dict):
            return
        for key, dist in (
            ("qobserva_version", "qobserva"),
            ("agent_version", "qobserva-agent"),
            ("collector_version", "qobserva-collector"),
        ):
            cur = sw.get(key)
            if cur is None or (isinstance(cur, str) and not cur.strip()):
                v = _dist_version_or_none(dist)
                if v:
                    sw[key] = v

    def auth(authorization: str | None = Header(default=None)):
        cfg = load_config()
        if not cfg.require_token:
            return True
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        token = authorization.split(" ", 1)[1].strip()
        if token != cfg.token:
            raise HTTPException(status_code=403, detail="Invalid token")
        return True

    @app.post("/v1/ingest/run-event")
    def ingest_run_event(event: Dict[str, Any], _auth: bool = Depends(auth), db: Session = Depends(get_db)):
        errs = validate_event_dict(event)
        if errs:
            raise HTTPException(status_code=400, detail={"errors": errs})

        _enrich_software_versions(event)

        run_id = event["run_id"]
        if db.query(Run).filter(Run.run_id == run_id).first():
            return {"accepted": True, "run_id": run_id, "duplicate": True}

        project = event.get("project", "default")
        backend = event.get("backend", {}) or {}
        exec_ = event.get("execution", {}) or {}

        artifact_ref = store_event_bundle(project, run_id, event)
        analysis = compute_metrics_and_insights(event)
        analysis_ref = store_analysis_bundle(project, run_id, analysis)

        rec = Run(
            run_id=run_id,
            event_id=event.get("event_id", ""),
            created_at=event.get("created_at", ""),
            project=project,
            provider=backend.get("provider", "unknown"),
            backend_name=backend.get("name", "unknown"),
            status=exec_.get("status", "unknown"),
            shots=int(exec_.get("shots") or 0),
            artifact_ref=artifact_ref,
            analysis_ref=analysis_ref,
        )
        db.add(rec)
        db.commit()

        return {"accepted": True, "run_id": run_id, "event_id": event.get("event_id")}

    @app.get("/v1/runs")
    def list_runs(
        project: str | None = None, 
        provider: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        algorithm: str | None = None,
        limit: int = 200,
        db: Session = Depends(get_db)
    ):
        q = db.query(Run)
        initial_count = q.count()
        
        if project:
            q = q.filter(Run.project == project)
        if provider:
            q = q.filter(Run.provider == provider)
        if status:
            q = q.filter(Run.status == status)
        if start_date:
            q = q.filter(Run.created_at >= start_date)
        if end_date:
            q = q.filter(Run.created_at <= end_date)
        
        rows = q.order_by(Run.id.desc()).limit(limit * 2 if algorithm else limit).all()  # Get more if filtering by algorithm
        
        # Filter by algorithm tag if provided (requires loading event bundles)
        if algorithm:
            filtered_rows = []
            for r in rows:
                try:
                    event = load_event_bundle(r.artifact_ref)
                    tags = event.get("tags", {})
                    if tags.get("algorithm") == algorithm:
                        filtered_rows.append(r)
                except Exception:
                    continue
            rows = filtered_rows[:limit]

        return [{
            "run_id": r.run_id,
            "event_id": r.event_id,
            "created_at": r.created_at,
            "project": r.project,
            "provider": r.provider,
            "backend_name": r.backend_name,
            "status": r.status,
            "shots": r.shots,
        } for r in rows]

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str, db: Session = Depends(get_db)):
        r = db.query(Run).filter(Run.run_id == run_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Not found")
        return load_event_bundle(r.artifact_ref)
    
    @app.get("/v1/runs/{project}/{run_id}/event")
    def get_run_event(project: str, run_id: str, db: Session = Depends(get_db)):
        """Get event data for a specific run."""
        r = db.query(Run).filter(Run.run_id == run_id, Run.project == project).first()
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")
        return load_event_bundle(r.artifact_ref)
    
    @app.get("/v1/runs/{project}/{run_id}/analysis")
    def get_run_analysis(project: str, run_id: str, db: Session = Depends(get_db)):
        """Get analysis data for a specific run."""
        r = db.query(Run).filter(Run.run_id == run_id, Run.project == project).first()
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")
        return load_analysis_bundle(r.analysis_ref)
    
    @app.get("/v1/health")
    def health():
        """Health check endpoint."""
        return {"status": "ok"}
    
    @app.get("/v1/settings")
    def get_settings():
        """Get QObserva settings including data directory."""
        cfg = load_config()
        return {
            "data_dir": cfg.data_dir,
            "data_dir_source": "QOBSERVA_DATA_DIR environment variable" if os.getenv("QOBSERVA_DATA_DIR") else "default (platform-specific user data directory)",
            "qobserva_version": _get_installed_version("qobserva"),
            "qobserva_agent_version": _get_installed_version("qobserva-agent"),
            "qobserva_collector_version": _get_installed_version("qobserva-collector"),
            "qobserva_local_version": _get_installed_version("qobserva-local"),
        }

    @app.get("/v1/runs/{run_id}/analysis")
    def get_run_analysis(run_id: str, db: Session = Depends(get_db)):
        r = db.query(Run).filter(Run.run_id == run_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Not found")
        return load_analysis_bundle(r.analysis_ref)

    @app.get("/v1/algorithms")
    def get_algorithms(
        limit: int = 1000,
        db: Session = Depends(get_db)
    ):
        """Get list of unique algorithms from runs that have algorithm tags."""
        algorithms = set()
        rows = db.query(Run).order_by(Run.id.desc()).limit(limit).all()
        
        for r in rows:
            try:
                event = load_event_bundle(r.artifact_ref)
                tags = event.get("tags", {})
                algo = tags.get("algorithm")
                if algo:
                    algorithms.add(algo)
            except Exception as e:
                print(f"  Error loading event for run {r.run_id}: {e}")
                continue
        
        # Return sorted list with counts
        algo_list = []
        for algo in sorted(algorithms):
            # Count runs for this algorithm
            count = 0
            for r in rows:
                try:
                    event = load_event_bundle(r.artifact_ref)
                    tags = event.get("tags", {})
                    if tags.get("algorithm") == algo:
                        count += 1
                except:
                    continue
            algo_list.append({"name": algo, "count": count})
        
        return {"algorithms": algo_list}

    return app
