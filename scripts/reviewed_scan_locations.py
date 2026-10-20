"""Finite, byte-pinned classifications of independently reviewed scan locations.

The data is not a pattern allowlist. Changing any file byte, physical line,
rule, scanner version or configuration leaves a finding blocking. Scanner
Match/Secret/Line fields are never evidence for a classification.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
import zlib
from pathlib import Path, PurePosixPath

_REVIEW_DATA_PATH = "scripts/data/reviewed_scan_locations_v3.zip"
_REVIEW_DATA_DIGEST = "000a1c7afbc1847e7489459bef68b20bbaeaa387e227abe05c7b2073383fbaa4"
_REVIEW_MEMBER = "reviewed-locations.json"
_LIMIT = 16 * 1024 * 1024
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_RULE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


def _invalid() -> None:
    raise RuntimeError("Reviewed scanner location registry is invalid; output withheld") from None


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _digest(value: object) -> bool:
    return isinstance(value, str) and _HEX.fullmatch(value) is not None


def _canonical(value: object) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= 1024
        and not any(ord(char) < 32 for char in value)
        and "\\" not in value and ":" not in value
        and not PurePosixPath(value).is_absolute()
        and all(part not in {"", ".", ".."} for part in value.split("/")))


class ReviewedLocations:
    """A validated registry with per-scan caches, never process-global caches."""

    def __init__(self, snapshot: Path, source_hashes: dict[str, str], files: dict):
        self.snapshot = snapshot
        self.source_hashes = source_hashes
        self.files = files
        self.checked: dict[str, dict[int, str] | None] = {}

    def classify(self, item: dict, name: str) -> dict | None:
        record = self.files.get(name)
        start, end, rule = item.get("StartLine"), item.get("EndLine"), item.get("RuleID")
        if (record is None or type(start) is not int or type(end) is not int
                or start != end or not isinstance(rule, str)):
            return None
        pin = record["lines"].get((start, rule))
        if pin is None or self.source_hashes.get(name) != record["source_digest"]:
            return None
        if name not in self.checked:
            verified = None
            try:
                target = self.snapshot / name
                if target.is_symlink() or not target.resolve().is_relative_to(self.snapshot):
                    return None
                content = target.read_bytes()
                if hashlib.sha256(content).hexdigest() == record["scanner_digest"]:
                    content.decode("utf-8", errors="strict")
                    numbers = {number for number, _ in record["lines"]}
                    verified = {number: hashlib.sha256(line).hexdigest()
                        for number, line in enumerate(content.split(b"\n"), 1)
                        if number in numbers}
            except (OSError, UnicodeError):
                pass
            self.checked[name] = verified
        physical = self.checked[name]
        if physical is None or physical.get(start) != pin:
            return None
        return {"file": name, "line": start, "rule": rule,
            "file_sha256": record["source_digest"], "physical_line_sha256": pin,
            "reason": "finite independently reviewed non-credential evidence; registry v3"}


def load_reviewed_locations(snapshot: Path, source_hashes: dict[str, str],
                            version: str) -> ReviewedLocations:
    """Load only copied, anchored data; missing data disables classifications.

    A present but invalid registry/configuration aborts the scan. Absent data
    cannot suppress a finding. Limits apply before decompression or parsing.
    """
    path = snapshot / _REVIEW_DATA_PATH
    if not path.exists():
        return ReviewedLocations(snapshot, source_hashes, {})
    try:
        if path.is_symlink() or path.stat().st_size > _LIMIT:
            _invalid()
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != _REVIEW_DATA_DIGEST:
            _invalid()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if len(members) != 1:
                _invalid()
            member = members[0]
            if (member.filename != _REVIEW_MEMBER or member.file_size > _LIMIT
                    or member.compress_size > _LIMIT or member.flag_bits & 1
                    or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}):
                _invalid()
            raw = archive.read(member)
        if len(raw) > _LIMIT:
            _invalid()
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
            parse_constant=lambda _: _invalid())
        if (type(data) is not dict or set(data) != {"schema", "version", "config_digest", "files"}
                or type(data["schema"]) is not int or data["schema"] != 1
                or data["version"] != "8.30.1" or version != "8.30.1"
                or not _digest(data["config_digest"])
                or type(data["files"]) is not list or not 0 < len(data["files"]) <= 2000):
            _invalid()
        config = snapshot / ".gitleaks.toml"
        if (config.is_symlink() or source_hashes.get(".gitleaks.toml") != data["config_digest"]
                or hashlib.sha256(config.read_bytes()).hexdigest() != data["config_digest"]):
            _invalid()
        files = {}
        total = 0
        for record in data["files"]:
            if (type(record) is not dict
                    or set(record) != {"path", "source_digest", "scanner_digest", "lines"}
                    or not _canonical(record["path"]) or record["path"] in files
                    or not _digest(record["source_digest"]) or not _digest(record["scanner_digest"])
                    or type(record["lines"]) is not list or not record["lines"]):
                _invalid()
            lines = {}
            for line in record["lines"]:
                if (type(line) is not dict or set(line) != {"number", "digest", "rules"}
                        or type(line["number"]) is not int or not 0 < line["number"] <= 2_000_000
                        or not _digest(line["digest"]) or type(line["rules"]) is not list
                        or not line["rules"] or len(line["rules"]) > 128):
                    _invalid()
                for rule in line["rules"]:
                    if (not isinstance(rule, str) or _RULE.fullmatch(rule) is None
                            or (line["number"], rule) in lines):
                        _invalid()
                    lines[line["number"], rule] = line["digest"]
                    total += 1
                    if total > 100_000:
                        _invalid()
            files[record["path"]] = {"source_digest": record["source_digest"],
                "scanner_digest": record["scanner_digest"], "lines": lines}
        return ReviewedLocations(snapshot, source_hashes, files)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError,
            zipfile.BadZipFile, zlib.error, EOFError):
        _invalid()
