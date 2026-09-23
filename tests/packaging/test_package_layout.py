"""Guards against the `qobserva` and `qobserva-agent` distributions overwriting each other."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

PACKAGES = Path(__file__).resolve().parents[2] / "packages"

def _pyproject(pkg: str) -> dict:
    return tomllib.loads((PACKAGES / pkg / "pyproject.toml").read_text(encoding="utf-8"))

def _files(pkg_dir: Path) -> set[str]:
    return {p.relative_to(pkg_dir).as_posix() for p in pkg_dir.rglob("*.py")}

def test_shared_init_is_identical_in_both_distributions():
    meta = (PACKAGES / "qobserva" / "qobserva" / "__init__.py").read_bytes().replace(b"\r\n", b"\n")
    agent = (PACKAGES / "qobserva_agent" / "qobserva" / "__init__.py").read_bytes().replace(b"\r\n", b"\n")
    assert meta == agent

def test_no_other_module_is_shipped_by_both_distributions():
    meta = _files(PACKAGES / "qobserva" / "qobserva")
    agent = _files(PACKAGES / "qobserva_agent" / "qobserva")
    assert meta & agent == {"__init__.py"}

def test_console_scripts_are_unique_across_distributions():
    seen: dict[str, str] = {}
    for pkg in ("qobserva", "qobserva_agent", "qobserva_collector", "qobserva_local"):
        for script in _pyproject(pkg).get("project", {}).get("scripts", {}):
            assert script not in seen, f"{script} declared by both {seen[script]} and {pkg}"
            seen[script] = pkg
    assert seen["qobserva"] == "qobserva"

def test_meta_package_pins_matching_component_versions():
    deps = _pyproject("qobserva")["project"]["dependencies"]
    for pkg in ("qobserva_agent", "qobserva_collector", "qobserva_local"):
        project = _pyproject(pkg)["project"]
        assert f"{project['name']}>={project['version']}" in deps
