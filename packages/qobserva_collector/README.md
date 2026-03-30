# qobserva-collector

**Local ingestion service for QObserva:** FastAPI server that accepts run events, validates them against the QObserva schema, and stores metadata and artifacts (SQLite + filesystem).

> ⚠️ **Beta:** This package is in beta. APIs may change.

## Install

```bash
pip install qobserva-collector
```

## Quick start

```bash
qobserva-collector serve --host 127.0.0.1 --port 8080
```

Events are validated with the bundled JSON Schema; data is written to a local directory (configurable). Use with `qobserva-agent` and `qobserva-local` for the full stack.

- **Full docs:** [qobserva.com](https://qobserva.com) · [Documentation](https://qobserva.com/docs.html)
- **Repo:** [GitHub — BuildersArk/qobserva](https://github.com/BuildersArk/qobserva)
- **Issues / Support:** [GitHub Issues](https://github.com/BuildersArk/qobserva/issues)
