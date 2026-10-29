"""Explicit parent inputs for 83 unchanged historical assertions.

The current Docker/lock child is tested separately.  Only the two named parent
reads are transported; CodeType objects and all original rejection bodies stay
identical.  This helper never changes the original modules or their globals.
"""
from __future__ import annotations

import __future__
import ast
import functools
import hashlib
import importlib
import json
import os
from pathlib import Path
from types import CodeType, FunctionType

import pytest

from tests.ci_image57 import authority, context

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "0c11713751c33782f1316b219da7fd543b576bdf"
MODULES = {
    "tests.test_security_container37_portable_peer": {
        "sha256": "d40ab3a3212b234ef88f170486694adf39a3100767af3f1947c1bf89750d8698",
        "blob": "e881525ad35a1eef6f04c94751af69b32b089d4b", "bytes": 282,
        "companion": "tests.test_current39_container_parent40", "count": 40,
        "reads": ("Dockerfile", "requirements-container-apt-metadata.lock"),
    },
    "tests.test_security_docker72_portability_peer": {
        "sha256": "d6be5cd777bb39cc80a10c1ed0fdbaf2fee08f4304234103274cba74df510393",
        "blob": "fafe20b8e5556d3bb7e6d7d82ae7f15d945e7f94", "bytes": 10676,
        "companion": "tests.test_current39_docker_parent25", "count": 25,
        "reads": ("Dockerfile", "requirements-container-apt-metadata.lock"),
    },
    "tests.test_ci_web37_bandit_registry": {
        "sha256": "1da5902930d66893c1e82c943c5c95a68dce07b62082d2e6aa86ebdb89e0adfd",
        "blob": "c98e58171e22679e21df28a6a7efb4562d87135b", "bytes": 6658,
        "companion": "tests.test_current39_bandit_parent18", "count": 18,
        "reads": ("Dockerfile",),
    },
}


def authenticated_module(name):
    pin = MODULES[name]
    module = importlib.import_module(name)
    path = ROOT / (name.replace(".", "/") + ".py")
    if Path(module.__file__).resolve() != path.resolve():
        raise ValueError("Historical assertion module path differs")
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    if b"\r" in lf or (b"\r\n" in raw and b"\n" in raw.replace(b"\r\n", b"")):
        raise ValueError("Historical assertion module has mixed framing")
    blob = hashlib.sha1(b"blob " + str(len(lf)).encode() + b"\0" + lf,
                        usedforsecurity=False).hexdigest()
    if len(lf) != pin["bytes"] or hashlib.sha256(lf).hexdigest() != pin["sha256"] or blob != pin["blob"]:
        raise ValueError("Historical assertion module is not the approved Git source")
    if pin["count"] == 40:
        provider = (ROOT / "tests/ci_web37/container_peer_portable.py").read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(provider).hexdigest() != "d7043950bbc61dcbfe056a071738435f7472a8af7e7e9a7efbc32078ec32de32":
            raise ValueError("Original portable assertion provider differs")
        raw = (ROOT / "tests/ci_web37/fixtures/container37-inputs-peer40.py.RAW").read_bytes()
        if hashlib.sha256(raw).hexdigest() != "1eb22aa94088334d12a202ca2376d7da0b5e566795b0cefd765be4b5b679f76e":
            raise ValueError("Original forty assertion RAW differs")
        reference = compile(raw, str(ROOT / "tests/test_security_container37_inputs_peer.py"), "exec",
                            flags=__future__.annotations.compiler_flag, dont_inherit=True)
    else:
        tree = ast.parse(raw, filename=str(path))
        from _pytest.assertion.rewrite import AssertionRewritingHook, rewrite_asserts
        if isinstance(module.__loader__, AssertionRewritingHook):
            # Match pytest's ordinary assertion instrumentation from the same
            # authenticated source; never transform or replace the assertions.
            rewrite_asserts(tree, raw, str(path), module.__loader__.config)
        reference = compile(tree, str(path), "exec", dont_inherit=True)
    codes = {value.co_name: value for value in reference.co_consts if isinstance(value, CodeType)}
    actual = {label: value for label, value in vars(module).items() if label.startswith("test_")}
    if (set(actual) != {label for label in codes if label.startswith("test_")}
            or any(not isinstance(value, FunctionType) or value.__code__ != codes[label]
                   for label, value in actual.items())):
        raise ValueError("Historical assertion CodeType or inventory differs")
    return module


class ParentRoot(os.PathLike):
    """Keep original cwd/support reads; redirect only named authenticated files."""
    def __init__(self, root, reads):
        self.root = Path(root)
        self.reads = frozenset(reads)
        self.files = None

    def __fspath__(self):
        return str(self.root)

    def __eq__(self, other):
        return self.root == Path(other) if isinstance(other, (str, os.PathLike)) else False

    def __truediv__(self, name):
        if name not in self.reads:
            return self.root / name
        if self.files is None:
            raise ValueError("Historical parent input accessed before authenticated setup")
        return self.files[name]

    def prepare(self, directory):
        manifest = context.json_object(authority.raw("container-inputs.json.RAW"))
        payloads = {name: (self.root / name).read_bytes() for name in manifest["candidate_files"]}
        parent, transition = context.native_parent_payloads(payloads)
        self.files = {}
        for name in self.reads:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(parent[name])
            self.files[name] = path
        record = {"scope": "historical_parent_inputs_only_not_current_child_acceptance",
                  "parent_authority_sha256": hashlib.sha256(authority.raw("container-inputs.json.RAW")).hexdigest(),
                  "transported_inputs": {name: manifest["candidate_files"][name] for name in sorted(self.reads)},
                  "actual_source_transition": transition}
        (directory / "transport.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf8")


def clone_function_namespace(function, parent, cache):
    original = function.__globals__
    key = id(original)
    if key not in cache:
        cloned = dict(original, ROOT=parent)
        cache[key] = cloned
        for name, value in original.items():
            if isinstance(value, FunctionType) and value.__globals__ is original:
                current = FunctionType(value.__code__, cloned, value.__name__, value.__defaults__, value.__closure__)
                functools.update_wrapper(current, value)
                current.__kwdefaults__ = value.__kwdefaults__
                current.__annotations__ = value.__annotations__.copy()
                cloned[name] = current
    cloned = cache[key]
    value = cloned.get(function.__name__)
    if not isinstance(value, FunctionType) or value.__code__ is not function.__code__:
        value = FunctionType(function.__code__, cloned, function.__name__, function.__defaults__, function.__closure__)
        functools.update_wrapper(value, function)
        value.__kwdefaults__ = function.__kwdefaults__
        value.__annotations__ = function.__annotations__.copy()
        cloned[function.__name__] = value
    return value


def install(namespace, name):
    original = authenticated_module(name)
    pin = MODULES[name]
    if namespace["__name__"] != pin["companion"]:
        raise ValueError("Historical assertions require their exact named companion")
    parent = ParentRoot(ROOT, pin["reads"])
    cache = {}
    exported = {}
    for label, value in vars(original).items():
        if label.startswith("test_") and isinstance(value, FunctionType):
            exported[label] = clone_function_namespace(value, parent, cache)
    namespace.update(exported)
    if name == "tests.test_security_container37_portable_peer":
        value = original.input_copy
        marker = value._fixture_function_marker
        function = clone_function_namespace(value._get_wrapped_function(), parent, cache)
        namespace["input_copy"] = pytest.fixture(scope=marker.scope, params=marker.params,
            autouse=marker.autouse, ids=marker.ids, name=marker.name)(function)
        namespace["original_expat_source"] = original.original_expat_source

    @pytest.fixture(scope="module", autouse=True)
    def authenticated_parent_inputs(tmp_path_factory):
        directory = tmp_path_factory.mktemp("native-parent-" + str(pin["count"]))
        parent.prepare(directory)
        return directory

    namespace["authenticated_parent_inputs"] = authenticated_parent_inputs
    namespace["PARENT_TRANSPORT"] = parent
    namespace["ORIGINAL_ASSERTIONS"] = original


# Exact original collection; source0c117, collected before any companion substitution.
CASE_NAMES = {'tests.test_ci_web37_bandit_registry': ('test_only_two_finite_source_universes_match_with_an_explicit_test_approval[captured_main_raw]',
                                         'test_only_two_finite_source_universes_match_with_an_explicit_test_approval[authenticated_git_lf]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[pending]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[expired]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[future]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[root-review]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[tool]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[context]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[missing]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[duplicate]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[span]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[source]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[matcher]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[caller]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[mixed-framing]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[occurrence-id]',
                                         'test_no_approval_applies_after_authority_context_multiset_or_source_changes[extra-binding]',
                                         'test_current39_schema_dependency_cannot_inherit_the_original37_approval'),
 'tests.test_security_container37_portable_peer': ('test_nine_native_inputs_are_exact_original_git_bytes_and_historical54_is_retained',
                                                   'test_main_current_web_lock_and_all_requirement_blocks_are_preserved',
                                                   'test_historical33_verifiers_are_not_retargeted_and_base_tools_stay_pinned',
                                                   'test_docker_has_only_the_three_declared_finite_deltas_from_native_recipe',
                                                   'test_unchanged_complete_finite_input_copy_is_accepted',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[Dockerfile]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[requirements-container-apt-metadata.lock]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[requirements-container-bootstrap.lock]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[requirements-container-build.lock]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[requirements-container-psycopg.lock]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[requirements-container.lock]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[runtime-source/container37-contract.json]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[runtime-source/expat-sec10/.gitattributes]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[runtime-source/expat-sec10/13c5f63.patch]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[runtime-source/expat-sec10/CONTRATO.md]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[runtime-source/expat-sec10/rebuild_pyexpat.py]',
                                                   'test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering[runtime-source/expat-sec10/source-pins.json]',
                                                   'test_extra_bearing_requirement_cannot_hide_a_canonical_duplicate[google_auth]',
                                                   'test_extra_bearing_requirement_cannot_hide_a_canonical_duplicate[GOOGLE-AUTH]',
                                                   'test_extra_bearing_requirement_cannot_hide_a_canonical_duplicate[google.auth]',
                                                   'test_extra_bearing_requirement_cannot_hide_a_canonical_duplicate[google--auth]',
                                                   'test_compiler_trace_is_exact_four_real_calls_and_one_link_not_a_build_execution',
                                                   'test_compiler_attestation_rejects_incomplete_or_ambiguous_traces[missing-call]',
                                                   'test_compiler_attestation_rejects_incomplete_or_ambiguous_traces[extra-call]',
                                                   'test_compiler_attestation_rejects_incomplete_or_ambiguous_traces[missing-hidden]',
                                                   'test_compiler_attestation_rejects_incomplete_or_ambiguous_traces[wrong-output]',
                                                   'test_compiler_attestation_rejects_incomplete_or_ambiguous_traces[missing-object]',
                                                   'test_new_ELF_cannot_expand_the_original_base_export_surface[exported0]',
                                                   'test_new_ELF_cannot_expand_the_original_base_export_surface[exported1]',
                                                   'test_new_ELF_cannot_expand_the_original_base_export_surface[exported2]',
                                                   'test_every_inline_python_fragment_parses_and_runtime_does_not_copy_build_tools',
                                                   'test_exact_five_line_capacity_backport_changes_only_the_pinned_source_bytes',
                                                   'test_native_patch_rejects_counterfeit_context_or_even_rehashed_modified_guard[different-operator]',
                                                   'test_native_patch_rejects_counterfeit_context_or_even_rehashed_modified_guard[missing-guard]',
                                                   'test_native_patch_rejects_counterfeit_context_or_even_rehashed_modified_guard[duplicate-anchor]',
                                                   'test_native_patch_rejects_counterfeit_context_or_even_rehashed_modified_guard[wrong-original-hash]',
                                                   'test_native_patch_rejects_counterfeit_context_or_even_rehashed_modified_guard[wrong-result-hash]',
                                                   'test_missing_or_ambiguous_base_visibility_never_enters_the_compile_trace[-O2]',
                                                   'test_missing_or_ambiguous_base_visibility_never_enters_the_compile_trace[-fvisibility=default]',
                                                   'test_missing_or_ambiguous_base_visibility_never_enters_the_compile_trace[-fvisibility=hidden '
                                                   '-fvisibility=hidden]'),
 'tests.test_security_docker72_portability_peer': ('test_all_twenty_one_object_frames_match_the_original_git_objects_without_import',
                                                   'test_original_peer_raw_is_the_complete_historical_source_with_declared_eol_only',
                                                   'test_all_twelve_candidate_inputs_remain_the_exact_approved_bytes',
                                                   'test_additional_unreviewed_archive_framing_is_rejected_before_authority[deflated]',
                                                   'test_additional_unreviewed_archive_framing_is_rejected_before_authority[uppercase-oid]',
                                                   'test_additional_unreviewed_archive_framing_is_rejected_before_authority[signed-size]',
                                                   'test_additional_unreviewed_archive_framing_is_rejected_before_authority[many-records]',
                                                   'test_additional_unreviewed_archive_framing_is_rejected_before_authority[huge-object]',
                                                   'test_additional_unreviewed_archive_framing_is_rejected_before_authority[huge-fixture]',
                                                   'test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority[]',
                                                   'test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority[/Dockerfile]',
                                                   'test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority[Dockerfile/]',
                                                   'test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority[runtime-source\\\\expat-sec10]',
                                                   'test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority[runtime-source/./expat-sec10]',
                                                   'test_absolute_empty_backslash_and_ambiguous_declared_paths_are_not_authority[Dockerfile\\x00extra]',
                                                   'test_source_pin_both_identities_and_finite_inventory_are_enforced[false-blob]',
                                                   'test_source_pin_both_identities_and_finite_inventory_are_enforced[false-raw-sha]',
                                                   'test_source_pin_both_identities_and_finite_inventory_are_enforced[missing-source]',
                                                   'test_source_pin_both_identities_and_finite_inventory_are_enforced[extra-source]',
                                                   'test_historical33_tree_comparison_rejects_file_and_inventory_drift[changed-byte]',
                                                   'test_historical33_tree_comparison_rejects_file_and_inventory_drift[missing-file]',
                                                   'test_historical33_tree_comparison_rejects_file_and_inventory_drift[added-file]',
                                                   'test_historical33_tree_comparison_rejects_file_and_inventory_drift[renamed-file]',
                                                   'test_historical33_bytecode_cache_is_not_mistaken_for_a_source_file',
                                                   'test_literal_companion57_runs_in_a_new_tree_without_git_repository_or_child_transport')}


def require_parent_companions(identities, originals=None):
    originals = set(MODULES) if originals is None else set(originals)
    if not originals or not originals <= MODULES.keys():
        raise ValueError("An exact historical companion subset is required")
    scopes = set(MODULES) | {pin["companion"] for pin in MODULES.values()}
    selected = [tuple(row) for row in identities if row[0] in scopes]
    required = {(MODULES[module]["companion"], case) for module in originals for case in CASE_NAMES[module]}
    if len(selected) != len(required) or set(selected) != required:
        raise ValueError("All required original parent assertions need their exact current39 companion identities")
    return len(required)
