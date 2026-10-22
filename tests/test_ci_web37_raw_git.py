"""Real Git export attributes cannot substitute bytes for authenticated blobs."""
import hashlib
import subprocess

from tests.ci_web37.raw_git import raw_blobs


def test_export_substitution_and_crlf_filters_cannot_change_original_blob(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    git = lambda *argv: subprocess.check_output(["git", "--no-replace-objects", *argv], cwd=repository)
    git("init", "--quiet")
    git("config", "core.autocrlf", "true")
    (repository / ".gitattributes").write_bytes(b"*.py text eol=crlf export-subst\n")
    original = b"# $Format:%H$\nvalue = 1\n"
    (repository / "source.py").write_bytes(original)
    git("add", "--", ".gitattributes", "source.py")
    git("-c", "user.name=CI web synthetic control", "-c", "user.email=ci-web@example.invalid",
        "commit", "--quiet", "-m", "Synthetic original source")
    oid = git("rev-parse", "HEAD:source.py").decode().strip()
    archive = git("archive", "--format=tar", "HEAD", "--", "source.py")
    assert b"$Format:%H$" not in archive
    result = list(raw_blobs(repository, {"source.py": (oid, "100644")}))
    assert result == [("source.py", original, oid, "100644")]
    assert hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original,
                        usedforsecurity=False).hexdigest() == oid
