#!/usr/bin/env python3
"""Malformed API power requests must not turn PenGuru on."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from service import Handler

scheduler=SimpleNamespace(set_enabled=Mock(return_value={"enabled":True}))
controller=SimpleNamespace(scheduler=scheduler)
handler=object.__new__(Handler)
handler.controller=controller
identity={"app_id":"org.nuxel.PenGuru","session_id":"12345678"}
for value in ("false", "true", 0, 1, None, [], {}):
    response=handler._dispatch(identity,{"op":"set_enabled","enabled":value})
    assert response["error"]=="invalid_enabled", (value,response)
    scheduler.set_enabled.assert_not_called()
for value in (False,True):
    response=handler._dispatch(identity,{"op":"set_enabled","enabled":value})
    assert response["ok"] is True
    scheduler.set_enabled.assert_called_with(value)
print("PenGuru strict power-control API input validation: PASS")
