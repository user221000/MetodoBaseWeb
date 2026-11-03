"""Explicit original PG inputs in private namespaces; no serial globals patch.

The phase rows come from the real isolated original validator. Only those input
aliases differ; every original consumer/helper and lease function keeps its
CodeType, source filename, defaults, marks and complete assertion body.
"""
from __future__ import annotations

import ast
import importlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import CodeType, FunctionType, ModuleType

import pytest
from _pytest.assertion.rewrite import rewrite_asserts

from tests.ci_web41 import legacy_pg_unit_capsule as capsule

ROOT = Path(__file__).resolve().parents[2]
PYTEST_REWRITE_PIN = ("9.1.1", 47740, "17f1eefbd1c2fe5326cb7592ff3af92a773582cf9d01727b09d3ab864906ee50")
CONSUMERS = (
    "tests/test_ci_web37_pg_lease.py",
    "tests/test_ci_web37_pg_qa_uuid_budget.py",
    "tests/test_ci_web37_pg_r24_witness.py",
)
PINS = {'tests/test_ci_web37_pg_lease.py': {'bytes': 2864,
                                     'sha256': 'af3467944936a6a5a2dae31da5ef22455af3a83820fe15670c47a4ea22b4893d',
                                     'Git_blob': 'f5267c5f5f243e99112aeff8e69b67fbc751e078'},
 'tests/test_ci_web37_pg_qa_uuid_budget.py': {'bytes': 4366,
                                              'sha256': 'fe1eccc037bd53f89cd21ec4d3d71313cf3d4d8ec679e846d0c7227d396ddc83',
                                              'Git_blob': '1efc22a29e28f0c4b68893281bdcc3264037f4a2'},
 'tests/test_ci_web37_pg_r24_witness.py': {'bytes': 2735,
                                           'sha256': 'fd6f0cc1da6c397a270940b09623186eac229fdea346b58a0ae896912eb36eed',
                                           'Git_blob': '0cbb664f6e9675724b9c14a0a3ae12e61ed6a546'},
 'tests/ci_web37/pg_lease.py': {'bytes': 4824,
                                'sha256': 'c7e874cbe8e2e1a3b5effa7829efac6cdffa1372e0e8793db3d46b97e11720aa',
                                'Git_blob': '68ead1a66843d0b04b3195ac81f1d9684a0f39f4'},
 'tests/ci_web37/pg_plan.py': {'bytes': 2188,
                               'sha256': '65880565fbf83c5ec783fef772d0eb38ff481da40a0c0f6a618a63cb2531868b',
                               'Git_blob': 'ace6ebebeee4751eccc114cfe37db7218ff8f5c1'},
 'tests/ci_web37/run_postgres.py': {'bytes': 14522,
                                    'sha256': '42ca8d1f2b178ebfb39a13f38fc8aa407efbe4a885fae5fc8667be487b6d144f',
                                    'Git_blob': '53e4d0527c2e3abbd1a606e75641dfefec8a48ce'},
 'tests/account37_qa_pg_fixtures.py': {'bytes': 5455,
                                       'sha256': '65ec40b662b6447d1075dbbb20d3f1c48230290d40d0828e492afcc67ea2b8e7',
                                       'Git_blob': '2bec49bc3e7b4b3494b116d569958d303cc68884'},
 'tests/account37_qa_pg_controls.py': {'bytes': 9946,
                                       'sha256': '55bb9adca44a98b7b8ed1c495bba4b10c87d3d69d8705fc5a7ab23b0f19bfd78',
                                       'Git_blob': '380937e6d93df886f95c18186dfa00a4377d0720'},
 'tests/integration_security_account37_peer.py': {'bytes': 3630,
                                                  'sha256': '74813bf0b2f9d4c3f12ead95b8db7b1fc931cdd9bddc40289e0936a46e4c73e1',
                                                  'Git_blob': 'b865b94bb8ccf41433ad1514a288c51be8cf8de4'},
 'tests/ci_web37/fixtures/pg-r24-e256-witnesses.jsonl.RAW': {'bytes': 6219,
                                                             'sha256': '85f453b29045917d40b0748c02cd30737536624c1c793817440e32ee28b53dc8',
                                                             'Git_blob': '13b1fc885bbb5f3745f956c4dbee3d25a4f51440'}}
_SNAPSHOT = pytest.StashKey()


def trusted_source(path, limit):
    """Bounded stable code read; installed tool files may use cache hardlinks."""
    import builtins as canonical_builtins
    import os as canonical_os
    import stat as canonical_stat

    before = path.lstat()
    if (not canonical_stat.S_ISREG(before.st_mode) or path.is_symlink()
            or getattr(before, "st_file_attributes", 0) & 1024 or not 0 <= before.st_size <= limit):
        raise ValueError("A trusted compiler/source file differs")
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
    with canonical_builtins.open(path, "rb") as stream:
        opened = canonical_os.fstat(stream.fileno())
        raw = stream.read(limit + 1)
        finished = canonical_os.fstat(stream.fileno())
    if (identity(before) != identity(path.lstat()) or identity(opened) != identity(finished)
            or identity(before)[:4] != identity(opened)[:4]
            or canonical_os.name != "nt" and identity(before) != identity(opened)
            or len(raw) != before.st_size):
        raise ValueError("A trusted compiler/source file changed")
    return raw


def canonical_imports(namespace, raw):
    """Use local canonical imports before touching any provider import alias."""
    import ast as canonical_ast
    import builtins as canonical_builtins
    import importlib as canonical_importlib

    if namespace.get("__builtins__") is not canonical_builtins and namespace.get("__builtins__") is not vars(canonical_builtins):
        raise ValueError("A provider canonical builtins binding differs")
    for node in canonical_ast.parse(raw).body:
        if (not isinstance(node, (canonical_ast.Import, canonical_ast.ImportFrom))
                or isinstance(node, canonical_ast.ImportFrom) and node.module == "__future__"):
            continue
        for alias in node.names:
            if isinstance(node, canonical_ast.Import):
                key = alias.asname or alias.name.split(".")[0]
                expected = canonical_importlib.import_module(alias.name if alias.asname else key)
            else:
                key = alias.asname or alias.name
                package = canonical_importlib.import_module(node.module)
                expected = getattr(package, alias.name, None)
                if expected is None:
                    expected = canonical_importlib.import_module(node.module + "." + alias.name)
            if namespace.get(key) is not expected:
                raise ValueError("A provider canonical import binding differs")


def validate_imports():
    """Trusted checkout and canonical stdlib/pytest runtime are prerequisites."""
    import importlib as canonical_importlib
    from pathlib import Path as CanonicalPath

    # First protect this provider, then the unchanged capsule used by its APIs.
    canonical_imports(globals(), trusted_source(CanonicalPath(__file__), 98304))
    original = canonical_importlib.import_module("tests.ci_web41.legacy_pg_unit_capsule")
    canonical_imports(vars(original), trusted_source(CanonicalPath(original.__file__), 98304))


def compiler_reference():
    """Authenticate the pinned installed compiler, without executing its source."""
    import base64
    import sys
    from importlib.metadata import distribution

    validate_imports()
    official = importlib.import_module("_pytest.assertion.rewrite")
    package = distribution("pytest")
    entry = next(item for item in package.files if str(item) == "_pytest/assertion/rewrite.py")
    path = Path(package.locate_file(entry)).absolute()
    roots = (Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve())
    if (package.version != PYTEST_REWRITE_PIN[0] or Path(official.__file__).absolute() != path
            or not any(path.resolve().is_relative_to(root) for root in roots)
            or entry.size != PYTEST_REWRITE_PIN[1] or entry.hash.mode != "sha256"):
        raise ValueError("The official pytest compiler provenance differs")
    raw = trusted_source(path, PYTEST_REWRITE_PIN[1])
    if (len(raw), capsule.digest(raw)) != PYTEST_REWRITE_PIN[1:] or base64.urlsafe_b64encode(bytes.fromhex(PYTEST_REWRITE_PIN[2])).decode().rstrip("=") != entry.hash.value:
        raise ValueError("The official pytest compiler source differs")
    canonical_imports(vars(official), raw)
    tree = ast.parse(raw)
    code = compile(raw, str(path), "exec", dont_inherit=True)
    references = {item.co_name: item for item in code.co_consts if isinstance(item, CodeType)}
    canonical_builtins = importlib.import_module("builtins")
    def check(function, reference):
        if (not isinstance(function, FunctionType) or function.__code__ != reference
                or function.__globals__ is not vars(official)
                or function.__builtins__ is not vars(canonical_builtins)
                or any(name != str(path) for name in _filenames(function.__code__))):
            raise ValueError("The official pytest compiler CodeType or namespace differs")
    check(official.rewrite_asserts, references["rewrite_asserts"])
    if rewrite_asserts is not official.rewrite_asserts or not same_typed(official.rewrite_asserts.__defaults__, (None, None)):
        raise ValueError("The official pytest compiler entry binding differs")
    node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AssertionRewriter")
    value = official.AssertionRewriter
    methods = {item.co_name: item for item in references[node.name].co_consts if isinstance(item, CodeType)}
    if (type(value) is not type or value.__module__ != official.__name__ or value.__bases__ != (ast.NodeVisitor,)
            or len(methods) != 22 or set(vars(value)) - set(methods) - {"__module__", "__doc__", "__dict__", "__weakref__"}):
        raise ValueError("The official pytest compiler class differs")
    for method in node.body:
        if isinstance(method, ast.FunctionDef):
            function = vars(value).get(method.name)
            if method.decorator_list:
                if [ast.unparse(item) for item in method.decorator_list] != ["staticmethod"] or type(function) is not staticmethod:
                    raise ValueError("The official pytest compiler method descriptor differs")
                function = function.__func__
            check(function, methods[method.name])
    return official.rewrite_asserts


def source_payloads(repository):
    """All ten inputs are admitted before namespace construction or row reuse."""
    repository = capsule.directory(repository)
    return {name: capsule.pinned(repository / name, pin, eol=True) for name, pin in PINS.items()}


def _expression(node):
    """The original marks use literals, one fixed date and finite timedelta."""
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        pass
    if isinstance(node, ast.Name) and node.id == "NOW":
        return datetime(2026, 10, 20, tzinfo=UTC)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "timedelta"
            and not node.args and all(item.arg in {"hours", "seconds"} for item in node.keywords)):
        return timedelta(**{item.arg: ast.literal_eval(item.value) for item in node.keywords})
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "isoformat"
            and not node.args and not node.keywords):
        value = _expression(node.func.value)
        if type(value) is datetime:
            return value.isoformat()
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range"
            and len(node.args) == 1 and not node.keywords and ast.literal_eval(node.args[0]) == 6):
        return range(6)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        left, right = _expression(node.left), _expression(node.right)
        if type(left) is datetime and type(right) is timedelta:
            return left + right if isinstance(node.op, ast.Add) else left - right
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)
            and ast.literal_eval(node.left) == "0" and ast.literal_eval(node.right) == 64):
        return "0" * 64
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_expression(item) for item in node.elts]
        return values if isinstance(node, ast.List) else tuple(values)
    if isinstance(node, ast.Dict):
        return {_expression(key): _expression(value) for key, value in zip(node.keys, node.values, strict=True)}
    raise ValueError("An original finite mark expression differs")


def _filenames(code):
    return (code.co_filename, *(name for item in code.co_consts if isinstance(item, CodeType)
                               for name in _filenames(item)))


def same_typed(actual, expected):
    """Preserve the typed oracle; Python/Mark equality merges bool/int/float."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is pytest.Mark:
        # Parametrization caches are pytest-derived state. Public mark inputs
        # retain exact recursive types and values, including all parameter rows.
        return (same_typed(actual.name, expected.name) and same_typed(actual.args, expected.args)
                and same_typed(actual.kwargs, expected.kwargs))
    if type(expected) is dict:
        return len(actual) == len(expected) and all(
            any(same_typed(key, other) and same_typed(value, actual[other]) for other in actual)
            for key, value in expected.items())
    if type(expected) in (tuple, list):
        return len(actual) == len(expected) and all(same_typed(left, right) for left, right in zip(actual, expected, strict=True))
    if type(expected) in (set, frozenset):
        return len(actual) == len(expected) and all(any(same_typed(left, right) for left in actual) for right in expected)
    if type(expected) is range:
        return (actual.start, actual.stop, actual.step) == (expected.start, expected.stop, expected.step)
    if type(expected) is datetime:
        return actual == expected and actual.tzinfo is expected.tzinfo and actual.fold == expected.fold
    if type(expected) in (type(None), bool, int, float, str, bytes) or isinstance(expected, Path):
        return actual == expected
    return actual is expected


def _function(value, references, node, module, path):
    fixture = hasattr(value, "_get_wrapped_function")
    function = value._get_wrapped_function() if fixture else value
    defaults = tuple(_expression(item) for item in node.args.defaults) or None
    kwdefaults = {item.arg: _expression(default) for item, default in
                  zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True) if default is not None} or None
    if (not isinstance(function, FunctionType) or function.__code__ not in references
            or any(name != str(path) for name in _filenames(function.__code__))
            or function.__globals__ is not vars(module) or function.__closure__ is not None
            or function.__builtins__ is not vars(importlib.import_module("builtins"))
            or not same_typed(function.__defaults__, defaults) or not same_typed(function.__kwdefaults__, kwdefaults)
            or not same_typed(function.__annotations__, {}) or function.__name__ != node.name
            or function.__qualname__ != node.name or function.__module__ != module.__name__):
        raise ValueError("An original consumer CodeType, filename, namespace or defaults differs")
    expected_marks, fixture_options = [], None
    for decorator in node.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        target = call.func if call else decorator
        name = ast.unparse(target)
        args = [_expression(item) for item in call.args] if call else []
        kwargs = {item.arg: _expression(item.value) for item in call.keywords} if call else {}
        if name == "pytest.mark.parametrize":
            # Derive reference data directly, without calling the mutable mark
            # factory whose result is being authenticated.
            expected_marks.append(pytest.Mark("parametrize", tuple(args), kwargs, _ispytest=True))
        elif name == "pytest.fixture" and not args and fixture_options is None:
            fixture_options = {"scope": "function", "params": None, "autouse": False, "ids": None, "name": None, **kwargs}
        else:
            raise ValueError("An original consumer decorator differs")
    expected_attributes = {"pytestmark": expected_marks} if expected_marks else {}
    if not same_typed(function.__dict__, expected_attributes) or fixture != (fixture_options is not None):
        raise ValueError("An original consumer marker or function attributes differs")
    if fixture and not same_typed(vars(value._fixture_function_marker), fixture_options):
        raise ValueError("An original consumer fixture scope or parameters differs")
    return function


def authenticated_module(repository, relative, payloads):
    """Check loaded objects against whole pinned source, including filename."""
    path = repository / relative
    module = importlib.import_module(relative[:-3].replace("/", "."))
    if Path(module.__file__) != path or module.__name__ != relative[:-3].replace("/", "."):
        raise ValueError("An original consumer module path differs")
    raw = payloads[relative]
    tree = ast.parse(raw)
    compiled = compile(raw, str(path), "exec", dont_inherit=True)
    functions = {item.co_name: [item] for item in compiled.co_consts if isinstance(item, CodeType)}
    # Pytest imports test modules through its authenticated-source assertion
    # compiler. Admit that precise compilation as well as --assert=plain.
    if relative in CONSUMERS:
        rewritten = ast.parse(raw)
        compiler_reference()(rewritten, raw, str(path))
        for item in compile(rewritten, str(path), "exec", dont_inherit=True).co_consts:
            if isinstance(item, CodeType) and item.co_name in functions:
                functions[item.co_name].append(item)
    # run_postgres owns a CLI with deliberate bootstrap effects. Authenticate
    # only the original pure witness callable used here; never execute its CLI.
    runner = relative == "tests/ci_web37/run_postgres.py"
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and (not runner or node.name == "require_witnesses"):
            _function(getattr(module, node.name, None), functions[node.name], node, module, path)
        elif not runner and isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            for alias in node.names:
                if isinstance(node, ast.Import):
                    key = alias.asname or alias.name.split(".")[0]
                    expected = importlib.import_module(alias.name if alias.asname else key)
                else:
                    key = alias.asname or alias.name
                    expected = getattr(importlib.import_module(node.module), alias.name)
                if vars(module).get(key) is not expected:
                    raise ValueError("An original consumer import alias differs")
        elif not runner and isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name == "ROOT":
                expected = repository
            elif name == "RAW":
                expected = repository / "tests/ci_web37/fixtures/pg-r24-e256-witnesses.jsonl.RAW"
            elif name == "NOW":
                expected = datetime(2026, 10, 20, tzinfo=UTC)
            else:
                expected = ast.literal_eval(node.value)
            if not same_typed(vars(module).get(name), expected):
                raise ValueError("An original consumer constant differs")
    if runner and module.json is not json:
        raise ValueError("The original witness JSON alias differs")
    return module


def clone_function(original, namespace):
    value = FunctionType(original.__code__, namespace, original.__name__, original.__defaults__, original.__closure__)
    value.__kwdefaults__ = deepcopy(original.__kwdefaults__)
    value.__annotations__ = deepcopy(original.__annotations__)
    value.__dict__.update(deepcopy(original.__dict__))
    value.__module__, value.__qualname__, value.__doc__ = original.__module__, original.__qualname__, original.__doc__
    return value


def clone_module(original):
    result = ModuleType(original.__name__)
    result.__dict__.update({key: deepcopy(value) if type(value) in (dict, list, set) and key != "__builtins__" else value
                            for key, value in vars(original).items()})
    for name, value in vars(original).items():
        if isinstance(value, FunctionType) and value.__module__ == original.__name__:
            vars(result)[name] = clone_function(value, vars(result))
    return result


def clone_inputs(original, *, repository=ROOT, snapshot=None):
    """Retain bodies/fixtures; supply historical data via private aliases only."""
    validate_imports()
    repository = capsule.directory(repository)
    relative = Path(original.__file__).relative_to(repository).as_posix()
    if relative not in CONSUMERS:
        raise ValueError("An explicit original PG consumer is required")
    before = source_payloads(repository)
    lease = authenticated_module(repository, "tests/ci_web37/pg_lease.py", before)
    authenticated_module(repository, "tests/ci_web37/pg_plan.py", before)
    authenticated_module(repository, "tests/ci_web37/run_postgres.py", before)
    if authenticated_module(repository, relative, before) is not original:
        raise ValueError("The original consumer module identity differs")
    if snapshot is not None and type(snapshot) is not capsule.Snapshot:
        raise ValueError("Only an actual isolated child Snapshot may be shared")
    state = {"snapshot": snapshot}
    def phases():
        validate_imports()
        source_payloads(repository)
        if state["snapshot"] is None:
            raise ValueError("The explicit historical PG input fixture has not run")
        return capsule.historical_phase_rows(repository, None, snapshot=state["snapshot"])
    private_lease = clone_module(lease)
    private_lease.phases = phases
    result = clone_module(original)
    if "pg_lease" in vars(result):
        result.pg_lease = private_lease
    if "phases" in vars(result):
        result.phases = phases
    if snapshot is None:
        @pytest.fixture(autouse=True)
        def historical_pg_input(request, tmp_path_factory):
            cached = request.config.stash.get(_SNAPSHOT, None)
            if cached is None:
                private = tmp_path_factory.mktemp("legacy-pg-consumer-inputs") / "capsule"
                cached = capsule.snapshot(repository, private)
                request.config.stash[_SNAPSHOT] = cached
            state["snapshot"] = cached
            try:
                phases()  # Validate on every consumer, without caching mutable rows.
                yield
            finally:
                state["snapshot"] = None
        result._web41_historical_pg_input = historical_pg_input
    if source_payloads(repository) != before:
        raise ValueError("Original PG consumer inputs changed during construction")
    return result, {"module": original.__name__, "original_source_unmodified": True,
                    "validation_scope": "original_CodeTypes_with_explicit_isolated_historical_phase_inputs",
                    "original_assertions_retained": {CONSUMERS[0]: 7, CONSUMERS[1]: 21, CONSUMERS[2]: 4}[relative],
                    "mutable_rows_cached": False, "shared_receipt_only": "Snapshot"}
