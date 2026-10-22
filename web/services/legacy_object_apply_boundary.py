"""Private operator files, stdlib only; no application/scanner/test imports.

Windows descriptor construction/readback follows the independently reviewed
QA33 two-principal boundary. Files may inherit exactly those two allow ACEs;
the directory itself must have a protected explicit DACL before any payload.
"""
import os
import stat


def _current_sid():
    import ctypes
    from ctypes import wintypes
    api, kernel = ctypes.WinDLL('advapi32', use_last_error=True), ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    api.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    api.GetTokenInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    api.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    token, size = wintypes.HANDLE(), wintypes.DWORD()
    if not api.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise OSError('private_identity_unavailable')
    try:
        api.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 1 <= size.value <= 65536:
            raise OSError('private_identity_unavailable')
        buffer = ctypes.create_string_buffer(size.value)
        if not api.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise OSError('private_identity_unavailable')
        output = wintypes.LPWSTR()
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not api.ConvertSidToStringSidW(sid, ctypes.byref(output)):
            raise OSError('private_identity_unavailable')
        try:
            return output.value
        finally:
            kernel.LocalFree(ctypes.cast(output, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)
from pathlib import Path


def _windows(path, *, create=False):
    import ctypes
    import struct
    from ctypes import wintypes

    sid = _current_sid()
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    pointer = ctypes.c_void_p
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(pointer), pointer]
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    api.GetSecurityDescriptorDacl.argtypes = [pointer, ctypes.POINTER(wintypes.BOOL), ctypes.POINTER(pointer), ctypes.POINTER(wintypes.BOOL)]
    api.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    api.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, pointer, pointer, pointer, pointer]
    api.SetNamedSecurityInfoW.restype = wintypes.DWORD
    api.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, pointer, pointer, ctypes.POINTER(pointer), pointer, ctypes.POINTER(pointer)]
    api.GetNamedSecurityInfoW.restype = wintypes.DWORD
    api.GetSecurityDescriptorControl.argtypes = [pointer, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    api.GetSecurityDescriptorControl.restype = wintypes.BOOL
    api.GetAclInformation.argtypes = [pointer, pointer, wintypes.DWORD, wintypes.DWORD]
    api.GetAclInformation.restype = wintypes.BOOL
    api.GetAce.argtypes = [pointer, wintypes.DWORD, ctypes.POINTER(pointer)]
    api.GetAce.restype = wintypes.BOOL
    api.ConvertSidToStringSidW.argtypes = [pointer, ctypes.POINTER(wintypes.LPWSTR)]
    api.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    descriptor, acl = pointer(), pointer()
    if create:
        if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                f'D:P(A;OICI;FA;;;{sid})(A;OICI;FA;;;SY)', 1, ctypes.byref(descriptor), None):
            raise OSError('private_boundary_unavailable')
        try:
            present, defaulted = wintypes.BOOL(), wintypes.BOOL()
            if (not api.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(acl), ctypes.byref(defaulted))
                    or not present or not acl or api.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, acl, None)):
                raise OSError('private_boundary_unavailable')
        finally:
            kernel.LocalFree(descriptor)
        descriptor, acl = pointer(), pointer()
    if api.GetNamedSecurityInfoW(str(path), 1, 4, None, None, ctypes.byref(acl), None, ctypes.byref(descriptor)):
        raise OSError('private_boundary_unavailable')
    try:
        control, revision, info = wintypes.WORD(), wintypes.DWORD(), (wintypes.DWORD * 3)()
        if (not acl or not api.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision))
                or not api.GetAclInformation(acl, info, ctypes.sizeof(info), 2) or info[0] != 2):
            raise OSError('private_boundary_unavailable')
        entries = []
        for index in range(info[0]):
            ace, name = pointer(), wintypes.LPWSTR()
            if not api.GetAce(acl, index, ctypes.byref(ace)):
                raise OSError('private_boundary_unavailable')
            kind, flags, size, mask = struct.unpack('<BBHI', ctypes.string_at(ace, 8))
            if size < 16 or not api.ConvertSidToStringSidW(pointer(ace.value + 8), ctypes.byref(name)):
                raise OSError('private_boundary_unavailable')
            try:
                entries.append((kind, flags, mask, name.value))
            finally:
                kernel.LocalFree(ctypes.cast(name, pointer))
        directory = path.is_dir()
        if ({row[3] for row in entries} != {sid, 'S-1-5-18'}
                or any(row[0] != 0 or row[2] != 0x1F01FF for row in entries)
                or directory and (control.value & 0x1004 != 0x1004 or any(row[1] != 3 for row in entries))
                or not directory and any(row[1] not in (0, 16) for row in entries)):
            raise OSError('private_boundary_unavailable')
    finally:
        kernel.LocalFree(descriptor)


def verify(path, *, directory=False):
    path = Path(path)
    if (not path.is_absolute() or any(part.is_symlink() or getattr(part, 'is_junction', lambda: False)()
            for part in (path, *path.parents)) or not path.exists()):
        raise OSError('private_boundary_unavailable')
    target = path if directory else path.parent
    if not target.is_dir():
        raise OSError('private_boundary_unavailable')
    for selected in ((target,) if directory else (target, path)):
        if os.name == 'nt':
            _windows(selected)
        elif (selected.stat().st_uid != os.getuid()
                or stat.S_IMODE(selected.stat().st_mode) != (0o700 if selected.is_dir() else 0o600)):
            raise OSError('private_boundary_unavailable')
    if not directory and (not path.is_file() or path.stat().st_nlink != 1):
        raise OSError('private_boundary_unavailable')


def create_private_directory(path):
    path = Path(path)
    if not path.is_absolute() or path.exists() or any(part.is_symlink() or getattr(part, 'is_junction', lambda: False)()
            for part in path.parents):
        raise OSError('fresh_private_directory_required')
    path.mkdir(mode=0o700)
    if os.name == 'nt':
        _windows(path, create=True)
    verify(path, directory=True)
    return path
