"""Independent finite Docker/native input review; no compiler or package install."""
import ast
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.ci_web37 import container_inputs as subject
from tests.test_security_container37_extras_peer import parsed_requirements

ROOT = Path(__file__).resolve().parents[1]
NATIVE = "72c44a1834d7bd9803b4b8846c6c87e85a53bfd3"
FROZEN = "8c7089ea702083d64bba6b747a37bfd2e825e998"
MANIFEST = json.loads((ROOT / "tests/ci_web37/container-inputs.json").read_bytes())
SPEC = importlib.util.spec_from_file_location("independent_native_recipe", ROOT / "runtime-source/expat-sec10/rebuild_pyexpat.py")
RECIPE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECIPE)


def git(source, name):
    return subprocess.check_output(["git", "--no-replace-objects", "show", source + ":" + name], cwd=ROOT)


def test_nine_native_inputs_are_exact_original_git_bytes_and_historical54_is_retained():
    names = [name for name in MANIFEST["source_files"] if name != "Dockerfile"]
    assert len(names) == 9
    for name in names:
        assert (ROOT / name).read_bytes() == git(NATIVE, name)
    assert RECIPE.pins()["runtime_metadata_expected_distributions"] == 54
    assert json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes())["distributions"]["google-auth"] == "2.62.0"


def test_main_current_web_lock_and_all_requirement_blocks_are_preserved():
    web = (ROOT / "requirements_web.lock").read_bytes()
    assert web == git("cd423", "requirements_web.lock")
    values = parsed_requirements(web)
    container = parsed_requirements((ROOT / "requirements-container.lock").read_bytes())
    assert len(values) == 57 and len(container) == 56
    assert {name: version for name, version in values.items() if name != "psycopg2-binary"} == container
    historical = parsed_requirements(git(NATIVE, "requirements-container.lock"))
    assert len(historical) == 53
    assert set(container) - set(historical) == {"google-auth", "pyasn1", "pyasn1-modules"}
    assert all(container[name] == version for name, version in historical.items())


def test_historical33_verifiers_are_not_retargeted_and_base_tools_stay_pinned():
    diff = subprocess.check_output(["git", "diff", "--name-only", "cd423", FROZEN, "--", "tests/ci_google33"], cwd=ROOT)
    assert not diff
    assert "pip==26.2.1" in (ROOT / "requirements-container-bootstrap.lock").read_text()
    assert "setuptools==84.0.0" in (ROOT / "requirements-container-build.lock").read_text()
    assert "psycopg2==2.9.13" in (ROOT / "requirements-container-psycopg.lock").read_text()
    assert "--hash=sha256:d36784fc2dae69523ba4b79c7d1d1b4d6e83e87836874f111262f4db940b16a6" in (ROOT / "requirements-container-psycopg.lock").read_text()


def test_docker_has_only_the_three_declared_finite_deltas_from_native_recipe():
    original = git(NATIVE, "Dockerfile").decode()
    current = (ROOT / "Dockerfile").read_text(encoding="utf8")
    count = json.loads((ROOT / "runtime-source/container37-contract.json").read_bytes())["runtime_distribution_count"]
    assert type(count) is int and count == 57
    copy = "COPY runtime-source/container37-contract.json /usr/local/share/metodobase/container37-contract.json\n\n"
    assert current.count(copy) == 1
    current = current.replace(copy, "")
    comment = re.search(r"^# Expected current37 runtime inventory: .+$", current, re.MULTILINE)
    assert comment
    current = current.replace(comment[0], "# Expected runtime inventory: 54 application distributions; the previous 55 included pip.")
    new = "expected=json.loads(Path('/usr/local/share/metodobase/container37-contract.json').read_text()); normalize=lambda n:re.sub('[-_.]+','-',n).lower(); actual={normalize(n):v for n,v in rows}; assert type(expected['runtime_distribution_count']) is int and expected['runtime_distribution_count']==57 and len(rows)==57 and actual==expected['distributions'] and "
    assert current.count(new) == 1
    current = current.replace(new, "assert len(rows)==54 and ")
    assert current.count("import importlib.util as u,importlib.metadata as m,json,re;") == 1
    current = current.replace("import importlib.util as u,importlib.metadata as m,json,re;", "import importlib.util as u,importlib.metadata as m,json;")
    assert current == original


@pytest.fixture
def input_copy(tmp_path, monkeypatch):
    for name in [*MANIFEST["candidate_files"], "requirements_web.lock", "tests/ci_web37/container-inputs.json"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    # Read only existing Git objects. No init/index/worktree mutation occurs.
    shutil.copyfile(ROOT / ".git", tmp_path / ".git")
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    return tmp_path


def test_unchanged_complete_finite_input_copy_is_accepted(input_copy):
    result = subject.verify()
    assert result["container_inputs"] == 12
    assert result["runtime_distribution_count"] == 57
    assert result["current_image_built"] is False


@pytest.mark.parametrize("name", sorted(MANIFEST["candidate_files"]))
def test_each_of_the_twelve_critical_inputs_rejects_one_byte_tampering(input_copy, name):
    target = input_copy / name
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError):
        subject.verify()


@pytest.mark.parametrize("other", ["google_auth", "GOOGLE-AUTH", "google.auth", "google--auth"])
def test_extra_bearing_requirement_cannot_hide_a_canonical_duplicate(other):
    raw = ("google-auth[pyjwt]==2.62.0 \\\n    --hash=sha256:" + "0" * 64 + "\n" + other + "==2.62.0 \\\n    --hash=sha256:" + "1" * 64 + "\n").encode()
    with pytest.raises(ValueError, match="Duplicate canonical"):
        subject.lock_blocks(raw)


def compiler_fixture():
    compiler = SimpleNamespace(compiler_so=["cc", "-fPIC"], linker_so=["cc", "-shared"])
    sources = [Path("/private/source") / (str(index) + ".c") for index in range(4)]
    objects = ["/private/objects/" + str(index) + ".o" for index in range(4)]
    artifact = Path("/private/output/pyexpat.so")
    flags = ["-g0", "-ffile-prefix-map=/private=.", "-fvisibility=hidden"]
    commands = [compiler.compiler_so + ["-c", str(source), "-o", obj] + flags for source, obj in zip(sources, objects)]
    commands += [compiler.linker_so + objects + ["-lm", "-o", str(artifact)]]
    return commands, sources, objects, artifact, compiler, flags


def test_compiler_trace_is_exact_four_real_calls_and_one_link_not_a_build_execution():
    RECIPE.require_compiler_trace(*compiler_fixture())
    called = []
    compiler = SimpleNamespace(call=lambda command, **kwargs: called.append((command, kwargs)) or "delegated")
    trace = RECIPE.record_compiler_calls(compiler)
    args = ["cc", "-c", "source.c"]
    assert compiler.call(args, dry_run=True) == "delegated"
    args.append("later")
    assert trace == [["cc", "-c", "source.c"]]
    assert called[0][0] is args and called[0][1] == {"dry_run": True}


@pytest.mark.parametrize("change", ["missing-call", "extra-call", "missing-hidden", "wrong-output", "missing-object"])
def test_compiler_attestation_rejects_incomplete_or_ambiguous_traces(change):
    values = compiler_fixture()
    commands = values[0]
    if change == "missing-call":
        commands.pop(0)
    elif change == "extra-call":
        commands.append(["cc", "unreviewed"])
    elif change == "missing-hidden":
        commands[0].remove("-fvisibility=hidden")
    elif change == "wrong-output":
        commands[0][commands[0].index("-o") + 1] = "other.o"
    else:
        commands[-1].remove(values[2][0])
    with pytest.raises(AssertionError):
        RECIPE.require_compiler_trace(*values)


@pytest.mark.parametrize("exported", [["PyInit_pyexpat", "XML_ParseBuffer"], [], ["Other"]])
def test_new_ELF_cannot_expand_the_original_base_export_surface(exported):
    with pytest.raises(AssertionError):
        RECIPE.require_base_exports(["PyInit_pyexpat"], exported)


def test_every_inline_python_fragment_parses_and_runtime_does_not_copy_build_tools():
    docker = (ROOT / "Dockerfile").read_text(encoding="utf8")
    snippets = re.findall(r'python -c "([^"\n]+)"', docker)
    assert len(snippets) >= 6
    for snippet in snippets:
        ast.parse(snippet)
    runtime = docker.split("FROM native-runtime AS runtime", 1)[1]
    assert "/opt/psycopg-build-tools" not in runtime
    assert "COPY --from=psycopg-build /opt" not in docker
    assert "COPY --from=expat-build /expat-output/pyexpat.cpython-312-x86_64-linux-gnu.so" in runtime
    assert "USER appuser" in runtime


@pytest.fixture(scope="module")
def original_expat_source():
    archive = Path("F:/MetodoBaseWeb-linux-lab-20261019/evidence/sca-native-triage31-20261019/primary/Python-3.12.15.tar.xz")
    lock = RECIPE.pins()
    selected = RECIPE.source_files(archive, lock)
    assert len(selected) == 31
    return selected["Modules/expat/xmlparse.c"], (ROOT / "runtime-source/expat-sec10/13c5f63.patch").read_bytes(), lock


def test_exact_five_line_capacity_backport_changes_only_the_pinned_source_bytes(original_expat_source):
    original, patch, lock = original_expat_source
    fixed = RECIPE.backport(original, patch, lock)
    assert hashlib.sha256(fixed).hexdigest() == lock["source_after_sha256"]
    assert fixed == original.replace(RECIPE.ANCHOR.encode(), (RECIPE.INSERT + RECIPE.ANCHOR).encode())


@pytest.mark.parametrize("change", ["different-operator", "missing-guard", "duplicate-anchor", "wrong-original-hash", "wrong-result-hash"])
def test_native_patch_rejects_counterfeit_context_or_even_rehashed_modified_guard(original_expat_source, change):
    original, patch, source_lock = original_expat_source
    lock = dict(source_lock)
    if change == "different-operator":
        patch = patch.replace(b"len > EXPAT_SAFE", b"len >= EXPAT_SAFE")
        lock["patch_sha256"] = hashlib.sha256(patch).hexdigest()
    elif change == "missing-guard":
        patch = patch.replace(b"+    return XML_STATUS_ERROR;\n", b"")
        lock["patch_sha256"] = hashlib.sha256(patch).hexdigest()
    elif change == "duplicate-anchor":
        original += RECIPE.ANCHOR.encode()
        lock["source_before_sha256"] = hashlib.sha256(original).hexdigest()
    elif change == "wrong-original-hash":
        lock["source_before_sha256"] = "0" * 64
    else:
        lock["source_after_sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        RECIPE.backport(original, patch, lock)


@pytest.mark.parametrize("flags", ["-O2", "-fvisibility=default", "-fvisibility=hidden -fvisibility=hidden"])
def test_missing_or_ambiguous_base_visibility_never_enters_the_compile_trace(flags):
    with pytest.raises(AssertionError):
        RECIPE.module_visibility({"PY_STDMODULE_CFLAGS": flags, "PY_CFLAGS_NODIST": "-fvisibility=hidden"})
