"""Finite311 AST transport with authenticated helpers and private hooks."""
from __future__ import annotations

import __future__
import ast
import builtins
import copy
import hashlib
from pathlib import Path
import sys
from types import FunctionType

import pytest

from tests.ci_web39 import bandit_review, native_parent_inputs

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("def f(value):\n    return value + 1\n",
           "async def f(value):\n    return value\n", "class C:\n    value = 1\n")


def field_shape(node, modern):
    node = copy.deepcopy(node)
    for item in ast.walk(node):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            fields = tuple(name for name in item._fields if name != "type_params")
            item._fields = (*fields, "type_params") if modern else fields
            if modern:
                item.type_params = []
            elif hasattr(item, "type_params"):
                del item.type_params
    return node


@pytest.mark.parametrize("source", SOURCES)
def test_native_and_both_explicit_field_shapes_have_the_identical312_dump(source):
    original = ast.parse(source)
    before = ast.dump(original, include_attributes=False)
    expected = ast.dump(field_shape(original, True), include_attributes=False)
    assert bandit_review.ast_text(original) == expected
    assert bandit_review.ast_text(field_shape(original, False)) == expected
    assert bandit_review.ast_text(field_shape(original, True)) == expected
    assert ast.dump(original, include_attributes=False) == before


@pytest.mark.parametrize("source", SOURCES)
@pytest.mark.parametrize("fault", ["nonempty", "not-list", "unknown-field", "attribute-outside-fieldset"])
def test_only_the_absent_empty_field_is_compatible_and_every_other_definition_shape_rejects(source, fault):
    tree = field_shape(ast.parse(source), True)
    node = next(value for value in ast.walk(tree)
                if isinstance(value, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    if fault == "nonempty":
        node.type_params = [ast.Name(id="T", ctx=ast.Load())]
    elif fault == "not-list":
        node.type_params = ()
    elif fault == "unknown-field":
        node._fields = (*node._fields, "unreviewed")
        node.unreviewed = []
    else:
        node._fields = tuple(name for name in node._fields if name != "type_params")
    with pytest.raises(ValueError):
        bandit_review.ast_text(tree)


def matcher_frame(tmp_path):
    source = ROOT / "tests/security_bandit22_contract_peer.py"
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == native_parent_inputs.PARENT_MATCHER_SHA256
    path = tmp_path / "tests/security_bandit22_contract_peer.py"
    path.parent.mkdir()
    path.write_bytes(raw)
    namespace = {"__file__": str(path), "__name__": "ci_web37_bandit22_literal_matcher"}
    code = compile(raw, str(path), "exec", flags=__future__.annotations.compiler_flag, dont_inherit=True)
    return path, raw, namespace, code


def test_parent_exec_uses_only_private_ast_and_keeps_all_global_objects_intact(tmp_path):
    _path, _raw, namespace, code = matcher_frame(tmp_path)
    before = (builtins.exec, builtins.__import__, ast.dump, sys.modules["ast"])
    native_parent_inputs.parent22_exec(code, namespace)
    assert (builtins.exec, builtins.__import__, ast.dump, sys.modules["ast"]) == before
    assert namespace["__builtins__"] is not vars(builtins)
    assert isinstance(namespace["ast"], native_parent_inputs.ParentAst)
    assert namespace["ast"].walk is ast.walk
    tree = ast.parse(SOURCES[0])
    assert namespace["ast"].dump(tree, include_attributes=False) == bandit_review.ast_text(tree)
    assert ast.dump(namespace["ast"].parse(SOURCES[0]), include_attributes=True) == ast.dump(tree, include_attributes=True)
    assert namespace["ast"]._parse is bandit_review.ast_parse
    importer = namespace["__builtins__"]["__import__"]
    assert importer("hashlib", namespace, namespace) is sys.modules["hashlib"]
    assert importer("ast", namespace, namespace, ("walk",), 0) is ast
    assert importer("ast", {}, {}, (), 0) is ast


@pytest.mark.parametrize("fault", ["namespace", "file", "body", "code", "code-file", "extra-global", "extra-args"])
def test_parent_exec_rejects_every_undeclared_code_frame_before_any_execution(tmp_path, fault):
    path, raw, namespace, code = matcher_frame(tmp_path)
    args = ()
    if fault == "namespace":
        namespace["__name__"] = "unreviewed"
    elif fault == "file":
        namespace["__file__"] = str(tmp_path / "wrong.py")
    elif fault == "body":
        path.write_bytes(raw + b"\n# changed\n")
    elif fault == "code":
        code = compile("raise AssertionError('must not execute')", str(path), "exec")
    elif fault == "code-file":
        code = compile(raw, "unreviewed-file", "exec", flags=__future__.annotations.compiler_flag, dont_inherit=True)
    elif fault == "extra-global":
        namespace["unreviewed"] = True
    else:
        args = ({},)
    with pytest.raises(ValueError):
        native_parent_inputs.parent22_exec(code, namespace, *args)


def test_parent_registry_keeps_its_original_code_and_changes_only_private_exec_lookup():
    from tests.ci_web37.bandit_registry import apply_registry
    original = apply_registry.__globals__.copy()
    current = native_parent_inputs.parent22_registry(apply_registry)
    assert current.__code__ is apply_registry.__code__
    assert current.__globals__ is not apply_registry.__globals__
    assert current.__globals__["exec"] is native_parent_inputs.parent22_exec
    assert apply_registry.__globals__ == original
    assert all(current.__globals__[name] is value for name, value in original.items() if name != "exec")


@pytest.mark.parametrize("options", [{"include_attributes": True}, {"annotate_fields": False}])
def test_parent_ast_facade_rejects_undeclared_dump_options(options):
    with pytest.raises(ValueError):
        native_parent_inputs.ParentAst().dump(ast.parse(SOURCES[0]), **options)


@pytest.mark.parametrize("fault", ["ast-text-code", "ast-parse-code", "globals", "file", "module", "pin"])
def test_parent_ast_facade_authenticates_its_new_dependency_before_using_any_helper(monkeypatch, fault):
    assert isinstance(native_parent_inputs.ParentAst(), native_parent_inputs.ParentAst)
    if fault in {"ast-text-code", "ast-parse-code"}:
        name = "ast_text" if fault == "ast-text-code" else "ast_parse"
        function = FunctionType((lambda *args, **kwargs: "unreviewed").__code__, vars(bandit_review), name)
        monkeypatch.setattr(bandit_review, name, function)
    elif fault == "globals":
        function = bandit_review.ast_text
        clone = FunctionType(function.__code__, dict(function.__globals__), function.__name__)
        monkeypatch.setattr(bandit_review, "ast_text", clone)
    elif fault == "file":
        monkeypatch.setattr(bandit_review, "__file__", str(ROOT / "unreviewed.py"))
    elif fault == "module":
        monkeypatch.setattr(bandit_review, "__name__", "unreviewed")
    else:
        monkeypatch.setattr(native_parent_inputs, "PARENT_AST_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="Current parent AST helper"):
        native_parent_inputs.ParentAst()
