"""Observe actual native pytest subreports without changing their execution."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from _pytest.reports import TestReport
from _pytest.subtests import SubtestReport

from tests.ci_web39 import subtest_reports as contract

observer = None


class Observer:
    def __init__(self, value, sha256, worker):
        self.value, self.worker = value, worker
        self.mapping, self.active, self.closed = {}, {}, set()
        self.issues = []
        self.sequence = self.subtests = 0
        self.output = contract.exclusive_output(Path(value["output"]) / (worker + ".jsonl"))
        self.record({"event": "header", "schema": contract.SCHEMA, "worker": worker,
                     "run_id": value["run_id"], "contract_sha256": sha256, "binding": value["binding"]})

    def record(self, value):
        self.sequence += 1
        self.output.write(contract.canonical({"sequence": self.sequence, **value}) + b"\n")
        self.output.flush()
        os.fsync(self.output.fileno())

    def collection(self, items):
        self.mapping = {item.nodeid: contract.item_identity(item) for item in items}
        actual = list(self.mapping.values())
        contract.require(len(self.mapping) == len(items) and len(actual) == len(set(map(tuple, actual)))
                         and set(map(tuple, actual)) == set(map(tuple, self.value["expected"])), "runtime main collection differs")
        self.record({"event": "collection", "main_count": len(items), "oracle_sha256": self.value["oracle_sha256"]})

    def start(self, item):
        node = item.nodeid
        if node not in self.mapping or node in self.active or node in self.closed:
            self.issues.append("duplicate_or_foreign_start")
            return
        self.active[node] = {"phases": [], "subtests": 0, "reports": {}}

    def report(self, report):
        node = report.nodeid
        state = self.active.get(node)
        if state is None:
            self.issues.append("report_without_active_owner")
            return
        if type(report) is SubtestReport:
            if id(report) in state["reports"]:
                self.issues.append("duplicate_subtest_report_object")
                return
            state["reports"][id(report)] = report
            context = report.context._to_json()
            valid = (type(context) is dict and set(context) == {"msg", "kwargs"}
                     and (context["msg"] is None or type(context["msg"]) is str)
                     and type(context["kwargs"]) is dict
                     and all(type(key) is str and type(value) is str for key, value in context["kwargs"].items()))
            if not valid:
                self.issues.append("invalid_native_subtest_context")
                return
            state["subtests"] += 1
            self.subtests += 1
            self.record({"event": "subtest", "nodeid": node, "identity": self.mapping[node],
                         "report_class": contract.SUBTEST_CLASS, "when": report.when, "outcome": report.outcome,
                         "ordinal": state["subtests"], "context_sha256": contract.digest(context)})
            return
        if type(report) is not TestReport:
            self.issues.append("unknown_main_report_type")
            return
        state["phases"].append({"when": report.when, "outcome": report.outcome})
        if report.when == "teardown":
            self.record({"event": "owner_closed", "nodeid": node, "identity": self.mapping[node],
                         "phases": state["phases"], "subtests": state["subtests"],
                         "lifecycle_complete": contract.canonical(state["phases"]) == contract.canonical(contract.PHASES)})
            del self.active[node]
            self.closed.add(node)

    def finish(self, exitstatus):
        if self.active:
            self.issues.append("owners_still_active")
        try:
            unchanged = contract.canonical(contract.current_binding()) == contract.canonical(self.value["binding"])
        except Exception:  # noqa: BLE001 -- preserve rejection and ordinary fixture closure
            unchanged = False
        self.record({"event": "footer", "prior_events": self.sequence, "exitstatus": int(exitstatus),
                     "owners": len(self.closed), "subtests": self.subtests, "issues": self.issues,
                     "binding_unchanged": unchanged})
        self.output.close()


def pytest_addoption(parser):
    group = parser.getgroup("current39-native-subtests")
    group.addoption("--web39-subtest-contract", type=Path)
    group.addoption("--web39-subtest-contract-sha256")


def pytest_configure(config):
    global observer
    observer = None
    path = config.getoption("web39_subtest_contract")
    sha256 = config.getoption("web39_subtest_contract_sha256")
    if path is None and sha256 is None:
        return
    if path is None or sha256 is None:
        raise pytest.UsageError("Both explicit current39 subtest contract options are required")
    try:
        value = contract.read_contract(path, sha256)
        worker_input = getattr(config, "workerinput", None)
        if worker_input is not None:
            worker = worker_input["workerid"]
        elif config.getoption("numprocesses", default=0):
            # The xdist controller receives already serialized reports; workers
            # own the original typed evidence and are never counted twice.
            contract.require(value["workers"] == ["gw0", "gw1"], "xdist actor contract differs")
            return
        else:
            worker = "controller"
        contract.require(worker in value["workers"], "unapproved or restarted worker")
        observer = Observer(value, sha256, worker)
    except (ValueError, OSError, KeyError) as error:
        raise pytest.UsageError(str(error)) from error


def pytest_collection_finish(session):
    if observer is not None:
        observer.collection(session.items)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    if observer is not None:
        observer.start(item)


def pytest_runtest_logreport(report):
    if observer is not None:
        observer.report(report)


def pytest_sessionfinish(session, exitstatus):
    if observer is not None:
        observer.finish(exitstatus)


def pytest_unconfigure(config):
    if observer is not None and not observer.output.closed:
        observer.output.close()
