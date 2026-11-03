"""Current41 source bindings for original Node programs and ordered criteria.

Historical descriptors/programs stay byte-identical. Current inputs have their
own finite uniform-text manifest; this does not rename current results as RAW39
or native browser acceptance. Every old assertion remains required.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from tests.ci_web39.run_web import execute, write
from tests.ci_web38.reports import node_cases
from tests.ci_web37.node_current import validate, validate_additional

ROOT = Path(__file__).resolve().parents[2]
BINDING_PATH = "tests/ci_web41/node-bindings41.json"
BINDING_SHA256 = "aaa66ccfdfeacedd8fdc6a5a7a5e07d168bb71cc42acc062185c3fa7bfdbb4b7"
SOURCE_SCOPE = "current41-uniform-text-inputs-original-Node-programs-explicit-contract-adapters"
DESCRIPTORS = {
    "legacy51": ("docs/implementation/20261018-evolution/SESION_NAVEGADOR_R31_CI_MAP.json", "b99a11eece0b4859b685a5dbf786378df03da9b3eb5f2db595f0de9509768695"),
    "current13": ("tests/ci_web39/node-current39.json", "7873681f21031e82f824c6172ab19a25c521cdb5a7ba9f5c6e4e11c4872bb9a1"),
    "additional8": ("tests/ci_web39/node-routines-onboarding39.json", "d24e6adf221ade25f84282b64afa705bf0a1c8fd8646c0ff40096e5698365036"),
    "new38": ("tests/ci_web39/node-new38-current39.json", "8d6c78ffd0bb465c44aa897fd95cafe737625a3a55b49567a8e1bac33b9faf8d"),
    "privacy3": ("tests/ci_web39/node-privacy39.json", "b1bce5c85b4bdb9d2aaa9ba86aa9c2a8a5df1a3d69cef88e30caf593af9b6a0d"),
    "original38": ("tests/ci_web38/node-new38.json", "b3a583ab6c704cfb77bd46af0127bdabd07ea36e0a92416c6597401df2f9c04c"),
}


def canonical(raw: bytes) -> bytes:
    text = raw.replace(b"\r\n", b"\n")
    if b"\r" in text or raw not in (text, text.replace(b"\n", b"\r\n")):
        raise ValueError("Only uniform LF/CRLF text transport is admitted")
    return text


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate Node41 contract field")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def _descriptor(root: Path, key: str):
    name, expected = DESCRIPTORS[key]
    raw = canonical((root / name).read_bytes())
    if digest(raw) != expected:
        raise ValueError("An authenticated historical Node descriptor differs")
    return _json(raw)


def require_sources(root: Path = ROOT):
    raw = canonical((root / BINDING_PATH).read_bytes())
    if digest(raw) != BINDING_SHA256:
        raise ValueError("The finite current41 Node binding manifest differs")
    value = _json(raw)
    if value["schema"] != "current41-node-bindings-v1" or value["source_scope"] != SOURCE_SCOPE:
        raise ValueError("The current41 Node source scope differs")
    if value["normative_obligations"] != {"legacy51": 865, "current13": 147, "additional8": 94, "new38": 38, "privacy3": 48}:
        raise ValueError("A normative Node obligation was removed or relabelled")
    observed_names = set()
    for pattern in value["source_patterns"]:
        observed_names.update(p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file())
    if observed_names != set(value["input_files"]):
        raise ValueError("The complete current41 Node input set differs")
    for name, pin in value["input_files"].items():
        source = (root / name).read_bytes()
        if pin["framing"] == "uniform_lf":
            source = canonical(source)
        elif pin["framing"] != "raw":
            raise ValueError("An undeclared Node41 source frame was used")
        if len(source) != pin["bytes"] or digest(source) != pin["sha256"]:
            raise ValueError("A current41 Node direct/transitive source differs: " + name)
    for key in DESCRIPTORS:
        _descriptor(root, key)
    original_additional = _descriptor(root, "additional8")
    transitions = value["program_transitions"]
    if (len(transitions) != 3 or value["current_executed_additional_criteria"] != 96 or
            [row["kind"] for row in transitions] != ["additional_product", "additional_product", "registration_fixture"]):
        raise ValueError("The three reviewed Node program transitions differ")
    for row in transitions:
        source = canonical((root / row["script"]).read_bytes())
        historical = (root / row["historical_fixture"]).read_bytes()
        if row["kind"] == "registration_fixture":
            entry = _descriptor(root, "original38")["phases"]["node-password38"]
            original_pin = entry["input_files"][row["script"]]["sha256"]
        else:
            entry = next(item for item in original_additional["commands"] if item["script"] == row["script"])
            original_pin = original_additional["input_files"][row["script"]]["sha256"]
        original_labels = entry["expected_cases"]
        current_labels = [row["criterion_renames"].get(label, label) for label in original_labels]
        if (digest(historical) != row["historical_sha256"] or
                row["historical_sha256"] != original_pin or
                digest(source) != row["current_canonical_lf_sha256"] or
                len(set(row["current_expected_cases"])) != len(row["current_expected_cases"]) or
                set(row["current_expected_cases"]) != set(current_labels + row["added_criteria"]) or
                row["historical_PASS_claim"] is not False):
            raise ValueError("A historical94 to current96 criterion bridge differs")
    # Old descriptor RAW checksums may describe uniform Windows text; this
    # authenticates both physical transports against the same literal program.
    def same_original(source, expected):
        text = canonical(source)
        return expected in {digest(text), digest(text.replace(b"\n", b"\r\n"))}
    for key in ("current13", "additional8", "privacy3"):
        descriptor = _descriptor(root, key)
        for name, pin in descriptor["input_files"].items():
            if not name.startswith("tests/"):
                continue
            if any(row["script"] == name for row in transitions):
                continue
            source = (root / name).read_bytes()
            if (name.endswith(".RAW") and digest(source) != pin["sha256"]) or (
                    not name.endswith(".RAW") and not same_original(source, pin["sha256"])):
                raise ValueError("An original Node program/fixture differs: " + name)
    for phase in _descriptor(root, "original38")["phases"].values():
        for name, pin in phase["input_files"].items():
            if any(row["script"] == name for row in transitions):
                continue
            if name.startswith("tests/") and not same_original((root / name).read_bytes(), pin["sha256"]):
                raise ValueError("An original38 program differs: " + name)
    return value


def _argv(script: str, preloader: str, extra=()):
    executable = shutil.which("node")
    if not executable:
        raise ValueError("An explicit usable Node executable on process PATH is required")
    loaders = ["tests/ci_web41/node_adapter.cjs"]
    if preloader not in loaders:
        loaders.append(preloader)
    return [executable, *(part for loader in loaders for part in ("--require", str(ROOT / loader))), script, *extra]


def _adapter_receipt(report, adapter):
    evidence = report.get("current41_adapter", {})
    for field in ("script", "original_canonical_lf_sha256", "input_compiled_canonical_lf_sha256", "output_compiled_canonical_lf_sha256", "criterion_renames", "allowed_assertion_changes"):
        if evidence.get(field) != adapter[field]:
            raise ValueError("A finite current41 adapter receipt differs")
    if (evidence.get("historical_PASS_claim") is not False or
            type(evidence.get("assertions_preserved")) is not int or
            evidence["assertions_preserved"] != adapter["assertion_count"]):
        raise ValueError("A current41 assertion parity receipt differs")


def _receipt(private: Path, name: str, results, bindings, **extra):
    require_sources()
    write(private / (name + "-observation.json"), results)
    return {"accepted": all(row["exit"] == 0 and row["exact_normative_labels"] for row in results),
            "commands": len(results), "executions": sum(row["cases"] for row in results),
            "source_scope": SOURCE_SCOPE, "direct_transitive_bound_sources": len(bindings["input_files"]),
            "historical_RAW39_PASS_claim": False, "native_browser_executed": False,
            "DOM_transport_doubles_only": True, **extra}


def node_gate(private, environment):
    bindings = require_sources()
    mapping = _descriptor(ROOT, "legacy51")
    commands = mapping["current_commands"]
    if len(commands) != 51 or len(mapping["case_obligations"]) != 865:
        raise ValueError("The original51 command/obligation inventory differs")
    results = []
    adapters = _json(canonical((ROOT / "tests/ci_web41/node-adapters41.json").read_bytes()))["rules"]
    for index, entry in enumerate(commands):
        script = entry["argv"][1]
        if digest(canonical((ROOT / script).read_bytes())) != entry["source_sha256"]:
            raise ValueError("An original51 current companion program differs")
        path = private / ("node-" + str(index + 1) + ".private.json")
        adapter = next((rule for rule in adapters if entry["argv"][2:] == [Path(rule["script"]).stem]), None)
        code = execute(_argv(script, "tests/ci_web41/node_adapter.cjs", entry["argv"][2:]), ROOT, environment, path, timeout=300)
        passed, valid = 0, False
        if code == 0:
            try:
                report = _json(path.read_bytes())
                names = [row["name"] for row in entry["expected_cases"]]
                if adapter:
                    names = [adapter["criterion_renames"].get(name, name) for name in names]
                    _adapter_receipt(report, adapter)
                elif "current41_adapter" in report:
                    raise ValueError("An undeclared Node41 command was adapted")
                passed = node_cases(report, names)
                valid = True
            except (ValueError, TypeError):
                pass
        results.append({"command": entry["key"], "exit": code, "cases": passed, "exact_normative_labels": valid})
    return _receipt(private, "node", results, bindings, normative_obligations=865)


def current_node_gate(private, environment):
    bindings = require_sources()
    mapping = _descriptor(ROOT, "current13")
    commands = mapping["commands"]
    if len(commands) != 13 or mapping["executions"] != 147 or sum(len(e["expected_cases"]) for e in commands) != 147:
        raise ValueError("The original current13 criteria differ")
    results = []
    for index, entry in enumerate(commands):
        path = private / ("node-current-" + str(index + 1) + ".private.json")
        code = execute(_argv(entry["script"], "tests/e2e/ci_web37_offline.cjs"), ROOT, environment, path, timeout=300)
        passed, valid = 0, False
        if code == 0:
            try:
                passed = validate(path.read_bytes(), entry)
                valid = True
            except (ValueError, TypeError):
                pass
        results.append({"command": entry["script"], "exit": code, "cases": passed, "exact_normative_labels": valid})
    return _receipt(private, "node-current", results, bindings, normative_obligations=147, legacy51_cases_repeated=0)


def additional_node_gate(private, environment):
    from core.routine_catalog import get_routine_program
    bindings = require_sources()
    mapping = _descriptor(ROOT, "additional8")
    commands = mapping["commands"]
    if len(commands) != 8 or mapping["executions"] != 94 or sum(len(e["expected_cases"]) for e in commands) != 94:
        raise ValueError("The original routine/onboarding criteria differ")
    trace = []
    for entry in commands:
        transition = next((row for row in bindings["program_transitions"] if row["script"] == entry["script"]), None)
        if transition:
            trace.extend({"script": entry["script"], "historical_criterion": label,
                          "current_criterion": transition["criterion_renames"].get(label, label)}
                         for label in entry["expected_cases"])
            entry["expected_cases"] = transition["current_expected_cases"]
    if sum(len(e["expected_cases"]) for e in commands) != 96:
        raise ValueError("The current96 routine/onboarding criteria differ")
    catalogue = private / "current-generic-catalogue.json"
    write(catalogue, {"version": 1, "scope": "gym", "program": get_routine_program()})
    environment = dict(environment, ROUTINE_CATALOG_FIXTURE=str(catalogue))
    environment.pop("ROUTINES_AUTH_GUARD_SOURCE", None)
    results = []
    adapters = _json(canonical((ROOT / "tests/ci_web41/node-adapters41.json").read_bytes()))["rules"]
    for index, entry in enumerate(commands):
        path = private / ("node-additional-" + str(index + 1) + ".private.json")
        code = execute(_argv(entry["script"], "tests/e2e/ci_web37_offline.cjs"), ROOT, environment, path, timeout=300)
        passed, valid = 0, False
        if code == 0:
            try:
                adapter = next((row for row in adapters if row["script"] == entry["script"]), None)
                if adapter:
                    _adapter_receipt(_json(path.read_bytes()), adapter)
                passed = validate_additional(path.read_bytes(), entry, ROOT)
                valid = True
            except (ValueError, TypeError):
                pass
        results.append({"command": entry["script"], "exit": code, "cases": passed, "exact_normative_labels": valid})
    return _receipt(private, "node-additional", results, bindings, normative_obligations=94,
                    current_executed_criteria=96, historical_changed_program_PASS_claim=False,
                    changed_program_criterion_trace=trace, source_bound_counter_pair=2)


def new_node_gate(private, environment, phase):
    bindings = require_sources()
    original = _descriptor(ROOT, "original38")
    mapping = _descriptor(ROOT, "new38")
    if phase not in {"node-product38", "node-password38"}:
        raise ValueError("An undeclared original38 phase was requested")
    entry, historical = mapping["phases"][phase], original["phases"][phase]
    if any(entry[name] != historical[name] for name in entry if name != "input_files"):
        raise ValueError("An original38 program or ordered assertion inventory differs")
    expected = {"node-product38": 13, "node-password38": 25}[phase]
    if entry["cases"] != expected or len(entry["expected_cases"]) != expected:
        raise ValueError("An original38 phase criterion was removed")
    path = private / (phase + ".private.json")
    code = execute(_argv(entry["script"], entry["preloader"]), ROOT, environment, path, timeout=300)
    passed, valid = 0, False
    if code == 0:
        try:
            passed = node_cases(_json(path.read_bytes()), entry["expected_cases"])
            valid = True
        except (ValueError, TypeError):
            pass
    results = [{"phase": phase, "exit": code, "cases": passed, "exact_normative_labels": valid}]
    return _receipt(private, phase, results, bindings, normative_obligations=expected, original38_program_pins=mapping["original38_program_pins"][phase])


def privacy_node_gate(private, environment):
    bindings = require_sources()
    mapping = _descriptor(ROOT, "privacy3")
    commands = mapping["commands"]
    if (len(commands) != 3 or mapping["executions"] != 48 or
            [len(e["expected_cases"]) for e in commands] != [15, 19, 14]):
        raise ValueError("The original privacy39 ordered criteria differ")
    results = []
    for index, entry in enumerate(commands):
        path = private / ("node-privacy39-" + str(index + 1) + ".private.json")
        code = execute(_argv(entry["script"], mapping["preloader"]), ROOT, environment, path, timeout=300)
        passed, valid = 0, False
        if code == 0:
            try:
                passed = node_cases(_json(path.read_bytes()), entry["expected_cases"])
                valid = True
            except (ValueError, TypeError):
                pass
        results.append({"script": entry["script"], "exit": code, "cases": passed, "exact_normative_labels": valid})
    return _receipt(private, "node-privacy39", results, bindings, normative_obligations=48)
