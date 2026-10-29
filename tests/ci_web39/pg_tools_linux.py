"""Linux identity for the exact PG tool child, retained through ordinary wait.

Only a pidfd opened for the direct, unreaped Popen child can attest closure.
The executable is supplied to Popen as an absolute, hash-bound path without a
shell; /proc/exe additionally corroborates it when the short child is still live.
A fast --list child may already be a zombie. That absence is recorded explicitly
and never presented as a live executable observation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import select
import subprocess
import sys


def tool_hashes(directory, *, verify_versions=False):
    """Bind client bytes; the preceding signed apt step establishes provenance.

    Version output is only a version check. It does not authenticate a package.
    """
    directory = Path(directory).resolve(strict=True)
    if sys.platform != "linux" or directory != Path("/usr/lib/postgresql/17/bin"):
        raise ValueError("The Linux39 tools require the exact CI PG17 directory")
    result = {}
    for name in ("pg_dump", "pg_restore"):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("An exact regular PG client executable is required")
        # The cluster bootstrap checks versions once before admitting any
        # tool. Authority refresh inside the observation window only hashes
        # files; it must not launch an extra --version child or connection.
        if verify_versions:
            version = subprocess.check_output([str(path), "--version"], text=True).split()
            if len(version) < 3 or version[2] != "17.11":
                raise ValueError("The Linux39 client version differs from the signed17.11 package")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def require_direct_spawn(kwargs):
    """An executable override or pre-exec callback cannot change trusted argv."""
    if (kwargs.get("creationflags", 0) != 0 or kwargs.get("shell", False)
            or kwargs.get("executable") is not None or kwargs.get("preexec_fn") is not None):
        raise ValueError("Linux PG child requires exact direct argv without shell, executable override or preexec callback")


def native(process):
    """Open a kernel handle before the child is reaped; never adopt another PID."""
    if sys.platform != "linux" or not hasattr(os, "pidfd_open") or process.returncode is not None:
        raise ValueError("An unreaped direct Linux Popen child with pidfd support is required")
    if hasattr(process, "_pg39_pidfd"):
        raise ValueError("The PG child already has an identity handle")
    if not isinstance(process.args, list) or not process.args or not Path(process.args[0]).is_absolute():
        raise ValueError("Exact absolute PG Popen argv required")
    handle = os.pidfd_open(process.pid, 0)
    try:
        root = Path("/proc") / str(process.pid)
        status = (root / "stat").read_text(encoding="ascii")
        if int(status.split(" ", 1)[0]) != process.pid:
            raise ValueError("The direct PG child process identity differs")
        fields = status[status.rindex(")") + 2:].split()
        executable = Path(process.args[0]).resolve(strict=True)
        try:
            observed = (root / "exe").resolve(strict=True)
        except FileNotFoundError:
            # The child remains unreaped and pidfd-bound. Only a zombie may
            # lack /proc/exe; a live child without identity fails closed.
            if fields[0] != "Z":
                raise ValueError("A live PG child has no executable observation") from None
            observed = None
        if observed is not None and observed != executable:
            raise ValueError("The observed PG child executable differs from its trusted spawn")
        identity = {"pid": process.pid, "start_ticks": int(fields[19]),
                    "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip(),
                    "executable": str(executable), "executable_observed_while_alive": observed is not None,
                    "executable_authority": "absolute_hash_bound_direct_Popen_no_shell",
                    "kernel_handle": "original_pidfd_before_reap"}
        process._pg39_pidfd = handle
        process._pg39_identity = dict(identity)
        return identity
    except BaseException:
        os.close(handle)
        raise


def signalled(process, timeout_ms=0):
    handle = getattr(process, "_pg39_pidfd", None)
    if type(handle) is not int or handle < 0:
        raise ValueError("The original PG child pidfd is required")
    poller = select.poll()
    poller.register(handle, select.POLLIN)
    events = poller.poll(timeout_ms)
    if any(flags & (select.POLLERR | select.POLLNVAL) for _, flags in events):
        raise ValueError("The original PG child pidfd became invalid")
    return any(flags & select.POLLIN for _, flags in events)


def confirm_closed(process, identity):
    if (getattr(process, "_pg39_identity", None) != identity or process.pid != identity.get("pid")
            or type(process.returncode) is not int or not signalled(process)):
        raise ValueError("The same direct PG child lacks ordinary wait and signalled original pidfd")
    return {"schema": "owned-Popen-original-pidfd-closure-v1", "pid": process.pid,
            "start_ticks": identity["start_ticks"], "boot_id": identity["boot_id"],
            "exit_code": process.returncode, "original_pidfd_signalled": True,
            "executable_observed_while_alive": identity["executable_observed_while_alive"],
            "executable_authority": identity["executable_authority"],
            "post_exit_process_identity_query_performed": False}


def release(process):
    handle = getattr(process, "_pg39_pidfd", None)
    if handle is not None:
        if not signalled(process):
            raise ValueError("Cannot release the original pidfd of a live PG child")
        os.close(handle)
        process._pg39_pidfd = None
