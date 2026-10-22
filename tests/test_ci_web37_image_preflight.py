"""Reject unsuitable guest facts without opening SSH or starting any VM."""
import pytest

from tests.ci_web37.image_guest_preflight import CACHE_ID, validate_guest


def facts():
    return {"system": "Linux", "machine": "x86_64", "free_bytes": 4 * 1024**3,
            "mem_available_KiB": 1500 * 1024, "running_containers": [], "cached_native_image_id": CACHE_ID}


def test_only_an_idle_guest_with_exact_reviewed_native_cache_passes_the_resource_probe():
    assert validate_guest(facts()) == facts()


@pytest.mark.parametrize("key,value", [("free_bytes", 2499 * 1024**2), ("mem_available_KiB", 1024**2-1),
                                      ("mem_available_KiB", True), ("running_containers", ["foreign-container"]),
                                      ("cached_native_image_id", "unreviewed-cache"), ("machine", "aarch64")])
def test_resource_cache_or_other_running_work_remains_blocking(key, value):
    value_map = facts()
    value_map[key] = value
    with pytest.raises(ValueError):
        validate_guest(value_map)
