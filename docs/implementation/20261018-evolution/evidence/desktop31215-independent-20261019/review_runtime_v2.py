"""Independent runtime-binary origin, effective83 package/SCA binding and Qt checks.

Reads the retained immutable Astral python-build-standalone release archive and
metadata. No network lookup, package installation, SCA rerun or Setup execution.
"""
import ctypes
from ctypes import wintypes
from copy import deepcopy
import platform
import re
import tarfile
from run_bundle51 import *

PROVENANCE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-python31215-windows-provenance-20261019')
ASSET=PROVENANCE/'cpython-3.12.15+20261013-x86_64-pc-windows-msvc-install_only.tar.gz'
RUNTIME=PROVENANCE/'runtime/python'
EVI=Path(r'F:/MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence')
BUNDLE=ROOT/'dist/MetodoBase'
ARCHIVE_SHA='bbc902d4d187ac4914915bf538196a064b49109a33a104965b5164ced5b80a1e'
CHECKSUMS_SHA='6f1da4ab940bfca4471b0816828f16942a149de31e7ac4745e90902d5e7d3ebd'
RELEASE_SHA='c1f6ddad5fea9a2a9e90d88b4c215ec221948f5aedb64a826e07b034c31d0741'
checks={}
def check(name,condition,details=None):
    checks[name]={'ok':bool(condition),'details':details}
    print(name+': '+('PASS' if condition else 'FAIL'),flush=True)
    assert condition,name
def canonical_name(name):return re.sub(r'[-_.]+','-',name).lower()
def inventory(directory):
    return {path.relative_to(directory).as_posix():sha(path.read_bytes()) for path in sorted(directory.rglob('*')) if path.is_file()}
def binary_version(path):
    library=ctypes.WinDLL('version',use_last_error=True)
    library.GetFileVersionInfoSizeW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(wintypes.DWORD)]
    library.GetFileVersionInfoSizeW.restype=wintypes.DWORD
    library.GetFileVersionInfoW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID]
    library.GetFileVersionInfoW.restype=wintypes.BOOL
    library.VerQueryValueW.argtypes=[wintypes.LPCVOID,wintypes.LPCWSTR,ctypes.POINTER(wintypes.LPVOID),ctypes.POINTER(wintypes.UINT)]
    library.VerQueryValueW.restype=wintypes.BOOL
    unused=wintypes.DWORD();size=library.GetFileVersionInfoSizeW(str(path),ctypes.byref(unused));assert size
    buffer=ctypes.create_string_buffer(size)
    assert library.GetFileVersionInfoW(str(path),0,size,buffer)
    pointer=wintypes.LPVOID();length=wintypes.UINT()
    assert library.VerQueryValueW(buffer,'\\',ctypes.byref(pointer),ctypes.byref(length))
    values=ctypes.cast(pointer,ctypes.POINTER(wintypes.DWORD))
    assert values[0]==0xFEEF04BD and length.value>=52
    return [values[2]>>16,values[2]&65535,values[3]>>16,values[3]&65535]

before=packages('runtime-v2-before')
bundle_before=inventory(BUNDLE)
source_before={name:sha((ROOT/name).read_bytes()) for name in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if name}
try:
    release_raw=(PROVENANCE/'release-20261013.raw.json').read_bytes()
    checksums_raw=(PROVENANCE/'SHA256SUMS').read_bytes()
    check('retained_release_and_checksum_bytes_pinned',sha(release_raw)==RELEASE_SHA and sha(checksums_raw)==CHECKSUMS_SHA,
          {'release_sha256':sha(release_raw),'checksums_sha256':sha(checksums_raw)})
    release=json.loads(release_raw)
    asset=next(item for item in release['assets'] if item['name']==ASSET.name)
    check('immutable_release_selected_exact_unstripped_asset',release['id']==412262826 and release['immutable'] is True
          and asset['id']==638902133 and asset['size']==46390009 and asset['digest']=='sha256:'+ARCHIVE_SHA,
          {'release_id':release['id'],'asset_id':asset['id'],'immutable':release['immutable'],'archive_name':ASSET.name})
    checksum_lines=checksums_raw.decode('utf8').splitlines()
    matches=[line.split() for line in checksum_lines if line.split() and line.split()[-1].lstrip('*')==ASSET.name]
    check('archive_exact_checksum_and_API_digest',len(matches)==1 and matches[0][0]==ARCHIVE_SHA
          and ASSET.stat().st_size==asset['size'] and sha(ASSET.read_bytes())==ARCHIVE_SHA,
          {'bytes':ASSET.stat().st_size,'sha256':ARCHIVE_SHA,'same_provider_checksum_and_API_not_independent_signature':True})
    with tarfile.open(ASSET,'r:gz') as archive:
        members=archive.getmembers()
        regular=[member for member in members if member.isfile()]
        names=[member.name for member in regular]
        safe=all(not member.issym() and not member.islnk() and (member.isdir() or member.isfile())
                 and ((member.name=='python' and member.isdir()) or member.name.startswith('python/'))
                 and '..' not in Path(member.name).parts for member in members)
        check('archive_paths_types_and_unique_regular_members',safe and len(names)==len(set(names)) and len(names)==len({name.casefold() for name in names}),
              {'regular_members':len(regular),'total_members':len(members),'no_extraction_by_this_review':True})
        selected={}
        for relative in ['python.exe','python312.dll','python3.dll','DLLs/_ssl.pyd','DLLs/_hashlib.pyd',
                         'DLLs/pyexpat.pyd','DLLs/libssl-3-x64.dll','DLLs/libcrypto-3-x64.dll']:
            stream=archive.extractfile('python/'+relative);assert stream is not None
            value=stream.read();actual=(RUNTIME/relative).read_bytes()
            selected[relative]={'archive_sha256':sha(value),'extracted_sha256':sha(actual),'bytes':len(value)}
        check('all_selected_runtime_core_TLS_expat_binaries_equal_archive',all(v['archive_sha256']==v['extracted_sha256'] for v in selected.values()),selected)
    observed=json.loads(subprocess.check_output([sys.executable,'-I','-S','-c',
       'import json,sys,platform,ssl,pyexpat;print(json.dumps(dict(version=platform.python_version(),base_prefix=sys.base_prefix,base_executable=sys._base_executable,architecture=platform.machine(),openssl=ssl.OPENSSL_VERSION,expat=pyexpat.EXPAT_VERSION)))']))
    check('actual_review_and_package_runtime_is_authenticated_31215',observed['version']=='3.12.15' and observed['architecture']=='AMD64'
          and Path(observed['base_prefix']).resolve()==RUNTIME.resolve() and sha(Path(observed['base_executable']).read_bytes())==selected['python.exe']['archive_sha256'],observed)
    check('actual_runtime_OpenSSL_and_Expat_versions',observed['openssl']=='OpenSSL 3.5.9 29 Sep 2026' and observed['expat']=='expat_2.8.5',
          {'openssl':observed['openssl'],'expat':observed['expat'],'scope':'Actual CPython extension runtime inspection, not a native CVE audit.'})
    included={}
    for relative in ['python312.dll','_ssl.pyd','_hashlib.pyd','pyexpat.pyd','libssl-3-x64.dll','libcrypto-3-x64.dll']:
        original=relative if relative=='python312.dll' else 'DLLs/'+relative
        path=BUNDLE/'_internal'/relative
        included[relative]={'bundle_sha256':sha(path.read_bytes()),'official_archive_sha256':selected[original]['archive_sha256']}
    check('bundled_CPython_TLS_and_Expat_exact_authenticated_bytes',all(v['bundle_sha256']==v['official_archive_sha256'] for v in included.values()),included)
    version=binary_version(BUNDLE/'_internal/python312.dll')
    check('bundled_python_DLL_version_resource_is_31215',version==binary_version(RUNTIME/'python312.dll')==[3,12,15150,1013] and all(value['FileVersion']=='3.12.15' and value['ProductVersion']=='3.12.15' for value in json.loads((OUT/'DLL-resource-original-diagnostic.json').read_bytes())),version)
    import PySide6
    from PySide6.QtCore import qVersion
    qt_root=Path(PySide6.__file__).resolve().parent
    qt={relative:sha((BUNDLE/'_internal/PySide6'/relative).read_bytes())==sha((qt_root/relative).read_bytes())
        for relative in ['Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','plugins/platforms/qwindows.dll','plugins/platforms/qoffscreen.dll']}
    check('Qt_683_runtime_and_five_native_binaries_equal_locked_environment',PySide6.__version__=='6.8.3' and qVersion()=='6.8.3' and all(qt.values()),
          {'PySide6':PySide6.__version__,'Qt':qVersion(),'binary_equal':qt})
    author=json.loads((EVI/'desktop31215-build66-20261019/package-inventory.json').read_text(encoding='utf8'))
    effective={canonical_name(name):version for name,version in before['packages']}
    expected_packages={canonical_name(item['name']):item['version'] for item in author}
    check('effective_83_packages_equal_frozen_build_inventory',effective==expected_packages and len(effective)==len(author)==83,
          {'effective_packages':len(effective),'author_packages':len(author)})
    audit_path=EVI/'desktop31215-security-20261019/desktop-audit-tests/audit.json'
    audit_raw=audit_path.read_bytes();audit=json.loads(audit_raw)
    audit_packages={canonical_name(item['name']):item['version'] for item in audit['dependencies']}
    check('retained_original_SCA83_exact_inventory_zero_matches',sha(audit_raw)=='ca85f119c35388197de1c8854ef2e0b62c0b926a47646a56997c2a05d8d462f6'
          and audit_packages==effective and len(audit['dependencies'])==83 and not any(item['vulns'] for item in audit['dependencies']),
          {'retained_audit_sha256':sha(audit_raw),'packages':len(audit_packages),'findings':sum(len(item['vulns']) for item in audit['dependencies']),
           'new_audit_or_network_query':False,'scope':'Retained OSV result only for Python distribution inventory; not exhaustive native DLL/CVE analysis.'})
    (OUT/'retained-original-audit83.json').write_bytes(audit_raw)
    diagnostic=json.loads((OUT/'bundle51-source.json').read_text(encoding='utf8'))['checks']['independent_packaged_offscreen_diagnostic']
    check('actual_new_packaged_Qt_diagnostic_passed_separate_profile',diagnostic['ok'] and diagnostic['details']['exit_code']==0
          and diagnostic['details']['receipt']['qt_platform']=='offscreen' and diagnostic['details']['receipt']['python_network_blocked'] is True
          and diagnostic['details']['receipt']['product_flow_executed'] is False,diagnostic['details'])
    source_after={name:sha((ROOT/name).read_bytes()) for name in source_before}
    check('runtime_review_sources_and_bundle_unchanged',source_before==source_after and len(source_after)==4433 and bundle_before==inventory(BUNDLE),
          {'sources':len(source_after),'bundle_files':len(bundle_before)})
finally:
    after=packages('runtime-v2-after')
    check('runtime_review_83_packages_and_all_locks_unchanged',before==after)
    save('runtime-review-v2.json',{'checks':checks,'check_count':len(checks),'failed':[name for name,value in checks.items() if not value['ok']],
          'source_commit':HEAD,'scope':'Authenticated retained Astral standalone release and actual bundled binaries; no PSF Windows installer provenance/signature claim, no Setup execution, no new SCA or broad/source suites.'})
print(json.dumps({'checks':len(checks),'failed':[name for name,value in checks.items() if not value['ok']]}))
