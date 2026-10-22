"""Retain eleven authenticated original source frames without reconstructing them."""
import hashlib

import pytest

from tests.ci_web37 import replay
from tests.ci_web37.native22_frames import FIXTURES, OriginalFrames


def test_all_eleven_retained_preimages_match_the_original_manifest_and_host():
    frames = replay.retained_native11()
    proof = OriginalFrames()
    assert len(frames) == 11
    for name, frame in frames.items():
        assert frame == (replay.ROOT / name).read_bytes()
        record = proof.manifest["helper_union"][name]
        assert len(frame) == record["bytes"]
        assert hashlib.sha256(frame).hexdigest() == record["raw_sha256"]
        git_lf = frame.replace(b"\r\n", b"\n")
        assert replay.original_native_helper(name, git_lf, frames) is frame
    assert not {"alembic.ini", "db_bootstrap.py"} & frames.keys()


def test_changed_git_byte_and_other_source_variant_are_refused():
    frames = replay.retained_native11()
    for name, frame in frames.items():
        git_lf = frame.replace(b"\r\n", b"\n")
        for bad in (bytes([git_lf[0] ^ 1]) + git_lf[1:], frame):
            with pytest.raises(ValueError, match="Git LF binding"):
                replay.original_native_helper(name, bad, frames)


def test_unknown_case_and_runtime_paths_have_no_original_helper_transport():
    frames = replay.retained_native11()
    for name in ("tests/unknown.py", "tests/Isolation.py", "db_bootstrap.py", "alembic.ini"):
        with pytest.raises(ValueError, match="eleven exact paths"):
            replay.original_native_helper(name, b"inert", frames)


def test_one_changed_archive_byte_is_refused(tmp_path):
    raw = (FIXTURES / "native11-retained-originals.zip").read_bytes()
    (tmp_path / "native11-retained-originals.zip").write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(ValueError, match="finite archive"):
        replay.retained_native11(tmp_path)


def test_missing_retained_originals_are_not_reconstructed(tmp_path):
    with pytest.raises(FileNotFoundError):
        replay.retained_native11(tmp_path)
