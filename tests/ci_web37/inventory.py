"""Inert inventory of discovered tests and transitive migration fixture targets.

This records review inputs. It never resolves a missing target by treating it
as current, and never changes selection or converts a failed test to a skip.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = "20261020_account_security"


class Inventory:
    def __init__(self, root=ROOT):
        self.root = root
        self.cache = {}

    def module(self, name):
        if name not in self.cache:
            path = self.root / (name.replace(".", "/") + ".py")
            if not path.is_file():
                self.cache[name] = None
            else:
                raw = path.read_bytes()
                tree = ast.parse(raw)
                definitions = {node.name: node for node in tree.body
                               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
                imports = {}
                constants = {}
                for node in tree.body:
                    if isinstance(node, ast.ImportFrom) and node.module:
                        for alias in node.names:
                            imports[alias.asname or alias.name] = (node.module, alias.name)
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                constants[target.id] = node.value
                self.cache[name] = {"path": path.relative_to(self.root).as_posix(), "tree": tree,
                    "sha256_LF": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
                    "definitions": definitions, "imports": imports, "constants": constants}
        return self.cache[name]

    def binding(self, module, name, seen=()):
        key = (module, name)
        if key in seen or not module.startswith(("tests.", "conftest")):
            return None
        value = self.module(module)
        if value is None:
            return None
        if name in value["definitions"]:
            return module, value["definitions"][name]
        if name in value["imports"]:
            target, exported = value["imports"][name]
            return self.binding(target, exported, (*seen, key))
        return None

    def constant(self, module, node, seen=()):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            key = (module, node.id)
            if key in seen:
                return None
            value = self.module(module)
            if node.id in value["constants"]:
                return self.constant(module, value["constants"][node.id], (*seen, key))
            if node.id in value["imports"]:
                target, exported = value["imports"][node.id]
                if self.module(target):
                    return self.constant(target, ast.Name(id=exported), (*seen, key))
        return None

    @staticmethod
    def fixture(node):
        return any(isinstance(value.func if isinstance(value, ast.Call) else value, ast.Attribute)
                   and (value.func if isinstance(value, ast.Call) else value).attr == "fixture"
                   for value in getattr(node, "decorator_list", []))

    def graph(self, module, fixture, seen=()):
        binding = self.binding(module, fixture)
        if binding is None:
            binding = self.binding("conftest", fixture)
        if binding is None:
            return []
        owner, node = binding
        key = (owner, node.name)
        if key in seen or not self.fixture(node):
            return []
        result = []
        migrations = []
        for call in [value for value in ast.walk(node) if isinstance(value, ast.Call)]:
            name = call.func.id if isinstance(call.func, ast.Name) else ""
            if name == "run_migration":
                args = [self.constant(owner, arg) for arg in call.args]
                if "--revision" in args:
                    index = args.index("--revision") + 1
                    target = args[index] if index < len(args) else None
                    migrations.append(target if isinstance(target, str) else "UNRESOLVED_EXPLICIT_TARGET")
                else:
                    migrations.append("DYNAMIC_HEAD_WITHOUT_REVISION_ARGUMENT")
        source = self.module(owner)
        result.append({"module": owner, "fixture": node.name, "source_sha256_LF": source["sha256_LF"],
            "migration_targets": migrations})
        for arg in node.args.args:
            result.extend(self.graph(owner, arg.arg, (*seen, key)))
        return result

    def discovered(self):
        listing = subprocess.check_output(["git", "ls-files", "-z", "tests"], cwd=self.root).split(b"\0")
        modules = sorted(raw.decode("utf8") for raw in listing if raw and
                         Path(raw.decode("utf8")).match("test_*.py") and
                         not Path(raw.decode("utf8")).name.startswith("test_desktop") and
                         Path(raw.decode("utf8")).name != "test_login_desktop.py")
        rows = []
        for path in modules:
            module = path.removesuffix(".py").replace("/", ".")
            value = self.module(module)
            tests = [node for node in value["tree"].body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                     and (node.name.startswith("test_") or node.name.startswith("Test"))]
            fixture_names = set()
            for node in tests:
                functions = [node] if isinstance(node, ast.FunctionDef) else [
                    method for method in node.body if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")]
                for function in functions:
                    fixture_names.update(arg.arg for arg in function.args.args if arg.arg != "self")
            providers = {(entry["module"], entry["fixture"]): entry
                         for fixture in sorted(fixture_names) for entry in self.graph(module, fixture)}
            targets = {target for entry in providers.values() for target in entry["migration_targets"]}
            old = sorted(target for target in targets if target.startswith("2026") and target != CURRENT)
            rows.append({"module": module, "source_sha256_LF": value["sha256_LF"],
                "local_test_definitions_or_classes": len(tests),
                "fixture_providers": list(providers.values()), "older_explicit_targets": old,
                "requires_fixture_review": bool(old or "UNRESOLVED_EXPLICIT_TARGET" in targets)})
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = Inventory().discovered()
    result = {"status": "static_review_input_not_runtime_acceptance", "expected_current_revision": CURRENT,
        "modules": rows, "modules_requiring_fixture_review": [row["module"] for row in rows
                                                               if row["requires_fixture_review"]]}
    with args.output.open("x", encoding="utf8") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(json.dumps({"discovered_web_modules": len(rows),
                      "modules_requiring_fixture_review": result["modules_requiring_fixture_review"]}))


if __name__ == "__main__":
    main()
