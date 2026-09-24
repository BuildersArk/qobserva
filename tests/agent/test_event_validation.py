from __future__ import annotations

import pytest
from qobserva.schema import validate_event_dict

def test_schema_validation_reports_missing_required_fields():
    errs = validate_event_dict({"hello": "world"})
    assert errs
