"""Opt-in child guard, inherited by exact current33 runner descendants only."""
import os
import importlib.util
import sys
from pathlib import Path

if os.environ.get('CI33_LEASE_DIRECTORY'):
    path=Path(__file__).resolve().parents[1]/'resource_guard.py'
    spec=importlib.util.spec_from_file_location('resource_guard',path)
    module=importlib.util.module_from_spec(spec);sys.modules['resource_guard']=module
    spec.loader.exec_module(module);module.install()
