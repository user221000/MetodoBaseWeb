"""The rejected R24 RAW trace must retain both baseline1 and actual race6."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from tests.ci_web37.pg_plan import phases
from tests.ci_web37.run_postgres import require_witnesses

RAW = Path(__file__).with_name("ci_web37") / "fixtures/pg-r24-e256-witnesses.jsonl.RAW"
RAW_SHA256 = "85f453b29045917d40b0748c02cd30737536624c1c793817440e32ee28b53dc8"


@pytest.fixture
def trace():
    raw = RAW.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA256
    return [json.loads(line) for line in raw.splitlines()]


def write_trace(tmp_path, rows):
    path = tmp_path / "witnesses.jsonl"
    path.write_bytes(b"\n".join(json.dumps(row).encode() for row in rows) + b"\n")
    return path


def race():
    return next(row for row in phases() if row["key"] == "legacy-r24-race")


def test_the_original_rejected_trace_preserves_all_six_actual37_witnesses(tmp_path):
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == RAW_SHA256
    assert require_witnesses(RAW, race()) == 6


@pytest.mark.parametrize("fault", ["baseline6", "criterion1", "all1", "missing", "extra", "test", "stage", "kind", "boolean_pool"])
def test_the_R24_trace_cannot_omit_or_relabel_the_baseline_or_race_engine(tmp_path, trace, fault):
    if fault == "baseline6":
        trace[0]["value"]["pool_size"] = 6
    elif fault == "criterion1":
        trace[1]["value"]["pool_size"] = 1
    elif fault == "all1":
        for row in trace:
            row["value"]["pool_size"] = 1
    elif fault == "missing":
        trace.pop()
    elif fault == "extra":
        trace.append(copy.deepcopy(trace[-1]))
    elif fault == "test":
        trace[0]["test"] = trace[0]["test"].replace("test_account_NOWAIT", "test_unrelated")
    elif fault == "stage":
        trace[0]["test"] = trace[0]["test"].replace("(setup)", "(teardown)")
    elif fault == "kind":
        trace[0]["kind"] = "unreviewed"
    else:
        trace[0]["value"]["pool_size"] = True
    with pytest.raises(ValueError):
        require_witnesses(write_trace(tmp_path, trace), race())


@pytest.mark.parametrize("index", range(6))
def test_baseline_and_race_rows_keep_the_same_restricted_role_contract(tmp_path, trace, index):
    trace[index]["value"]["role_flags4"][0] = True
    with pytest.raises(ValueError):
        require_witnesses(write_trace(tmp_path, trace), race())


def test_every_other_phase_still_rejects_pool6(tmp_path, trace):
    phase = next(row for row in phases() if row["key"] == "legacy-member-services")
    with pytest.raises(ValueError):
        require_witnesses(write_trace(tmp_path, [trace[1]]), phase)
    assert require_witnesses(write_trace(tmp_path, [trace[0]]), phase) == 1
