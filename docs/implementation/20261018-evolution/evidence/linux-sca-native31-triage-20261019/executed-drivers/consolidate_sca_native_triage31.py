from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import csv,hashlib,json,re
LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019');OUT=LAB/'evidence/sca-native-triage31-20261019'
MAIN=Path(r'F:\MetodoBaseWeb-execution-20261018/docs/implementation/20261018-evolution/evidence')
NATIVE=LAB/'evidence/runtime28-native-20261019/native/native.json'
SCAN=LAB/'evidence/os-audit-bc365c1/results/scan.json'
PRIOR=LAB/'evidence/os-audit-abd559a/triage-matrix/matrix-73.json'
TRACK=OUT/'primary/debian-security-tracker.current.raw.json'
OLDTRACK=LAB/'evidence/os-audit-abd559a/triage-primary/debian-security-tracker.raw.json'
OPENSSL=MAIN/'linux-runtime28-native-20261019/native-openssl-sec09'
DEPS=LAB/'evidence/container-system-libpq-20261019/runtime-os-expected.json'
inputs=[NATIVE,SCAN,PRIOR,TRACK,OLDTRACK,DEPS]+sorted(OPENSSL.glob('CVE-*.json'))
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
assert before[str(NATIVE)]=='9cbf93d511d52a80272f9d5525058062f282202934c2dc6e26aa8347d774eaec'
def save(name,value):
    path=OUT/name;assert not path.exists(),name;path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
native=json.loads(NATIVE.read_text());scan=json.loads(SCAN.read_text());prior={r['id']:r for r in json.loads(PRIOR.read_text())};tracker=json.loads(TRACK.read_text())
findings=[v for result in scan['Results'] for v in result.get('Vulnerabilities',[])];ids=sorted({v['VulnerabilityID'] for v in findings});assert len(findings)==164 and len(ids)==71 and not any(v.get('FixedVersion') for v in findings)
old=json.loads(OLDTRACK.read_text());unchanged=[]
for cid in ids:
    source=prior[cid]['source_package'];assert tracker[source][cid]['releases']['trixie']==old[source][cid]['releases']['trixie'];unchanged.append(cid)
del old
selected={};matrix=[];source_ids=defaultdict(list)
special={
 'CVE-2026-85091':{'classification':'PRIMARY_RANGE_AND_SOURCE_MISMATCH_PENDING_INDEPENDENT_REVIEW','evidence':'CNA range 1.3.1.2 through 1.3.2 excludes measured zlib 1.3.1. Official matching .deb has identical libz ELF SHA256 85590dd58edf5445e18bc7193e5ebc01ac5841f1ae187e97705a662e90c6421e. Debian source orig has no gz_vacate and debian/patches/series is empty. .dsc signature not independently verified on this host. Retain raw scanner finding.','action':'Independent component-scope review; do not blindly upgrade to 1.3.2 because it enters this CNA affected range.'},
 'CVE-2026-50812':{'classification':'NAMED_API_ABSENT_IN_MATCHING_LIBRARY_PENDING_INDEPENDENT_REVIEW','evidence':'CNA describes SQLite 3.53.1 sqlite3changeset_apply_v3. Actual 3.46.1 library matches official .deb ELF SHA256 317d80bf5d592f98a71e14d2330591d6a339f631f37c5977835af748a1f26715; named symbol string absent and upstream 3.46.1 session header/source do not define the API. All scanner entries retained.','action':'Independent review of version/API introduction; not a claim that other SQLite IDs are absent.'},
 'CVE-2026-27171':{'classification':'VERSION_AND_FUNCTION_PRESENT_REACHABILITY_UNPROVEN','evidence':'Measured zlib 1.3.1 is below fixed upstream 1.3.2; matching ELF exports crc32_combine64. Exact Debian source crc32.c has no non-positive len2 guard and no Debian patches. Python zlib API does not by itself establish a path to combine64.','action':'Prefer Debian stable backport of upstream ba829a458576d1ff0f26fc7230c6de816d1f6a77. Review source, package signatures and regression cases before any custom package; no stable fixed version available in current tracker.'},
}
for cid in ids:
    original=prior[cid];source=original['source_package'];source_ids[source].append(cid);primary=tracker[source][cid];selected.setdefault(source,{})[cid]=primary
    actual=[v for v in findings if v['VulnerabilityID']==cid]
    row={'id':cid,'kind':'CVE' if cid.startswith('CVE-') else 'Debian TEMP identifier','source_package':source,'actual_scanner_entries':len(actual),'actual_binary_packages':sorted({v['PkgName'] for v in actual}),'actual_installed_versions':sorted({v['InstalledVersion'] for v in actual}),'scanner_statuses':dict(Counter(v['Status'] for v in actual)),'scanner_fixed_versions':sorted({v['FixedVersion'] for v in actual if v.get('FixedVersion')}),'debian_trixie':primary['releases']['trixie'],'debian_description':primary['description'],'primary_url':'https://security-tracker.debian.org/tracker/'+cid,'other_debian_release_status':{k:v for k,v in primary['releases'].items() if k!='trixie'},'upstream_patch_links_reported_by_debian':original['tracker_explicit_upstream_fix_links'],'prior_component_scope_review':{'classification':original['applicability_classification'],'evidence':original['applicability_evidence']},'review_state':'OPEN; raw scan preserved, no ignores, accepted exceptions or exploit/reachability claims','stable_remediation':'Current trixie tracker remains open and has no fixed_version. Newer forky/sid fixes, if listed, are not stable backports and are not proposed for installation.'}
    row['new_component_review']=special.get(cid,{'classification':'PACKAGE_VERSION_MATCH_COMPONENT_REACHABILITY_UNPROVEN','evidence':'Use actual ELF owner/linkage and exact canonical-path evidence; source-package association does not prove every binary contains the affected function. Prior component notes retained.','action':'Review linked upstream patch/condition and stable security status; verify a focused signed backport or component absence before changing disposition. No blind dist-upgrade or mixed distribution packages.'})
    matrix.append(row)
assert len(source_ids)==20
save('os-findings71-current-primary.json',{'tracker_raw_sha256':before[str(TRACK)],'selected_entries':selected})
save('os-findings71-triage.json',{'image_id':scan['ArtifactName'],'actual_scan_sha256':before[str(SCAN)],'entries':164,'ids':71,'source_groups':20,'all_trixie_records_unchanged_since_previous_primary':len(unchanged),'rows':matrix})
save('os-scan164-preserved.json',{'scan_sha256':before[str(SCAN)],'scope':'Exact vulnerability objects copied without filtering; original scan remains immutable.','entries':findings})
group_actions={
 'acl':'Separate CLI-only CVE-2026-54370 (three exact canonical utilities absent) from CVE-2026-54369 libacl pathname functions (library present). Candidate upstream 2.4.0 requires reviewed stable backport, not forky packages.',
 'attr':'CVE-2026-54371 names getfattr/setfattr CLI; both exact canonical paths absent in inventory, libattr still present. Confirm full file/path scope independently before disposition; 2.6.0 is not a trixie fix.',
 'apt':'CVE-2011-3374 names apt-key; exact /usr/bin/apt-key absent, APT itself remains. Review Debian bug642480 and package file scope, not a generic APT trust bypass claim.',
 'bzip2':'CVE-2026-42250 names bzip2recover, exact canonical utility absent; loaded libbz2 remains a distinct component. Verify utility-specific upstream patch 35d122a3df8b0cc4082a4d89fdc6ee99f375fe67 before disposition.',
 'gcc-14':'Distinguish C++ header/template erase_if CVE-2026-102010 from aligned allocation CVE-2026-95619 in installed libstdc++; compiler executable absence would not remove runtime library exposure. 14.4.0-3 is sid, not a stable backport.',
 'glibc':'21 IDs require function/architecture/caller-specific review in actual 2.41-12+deb13u4. Current fixes listed in 2.43 sid/forky do not establish a trixie backport. Core libc is loaded; do not remove/upgrade Essential packages opportunistically.',
 'perl':'File::Temp exists in exact matching perl-base .deb and regex engine exists. Pod::Text and Archive::Tar are absent from perl-base archive only; whole-image text-module absence has not been proven. Keep fix_deferred distinct from fixed.',
 'sqlite3':'Review all four independently. apply_v3 ID50812 has source/API mismatch; 50813 session concat and 2025-70873 zipfile require extension/call-path checks. Corrupt database ID2021-45346 is disputed but remains tracked. Do not clear group by one absent API.',
 'systemd':'Seven source-package findings; only libsystemd0/libudev1 installed, named homed/oomd/journald/CLI canonical paths absent. Match each advisory to library versus daemon; journal parsing or library paths are not automatically eliminated.',
 'util-linux':'Six IDs replicated across util-linux source binaries. Exact login/chfn/chsh/mount/nsenter exist; user/group host privilege assumptions require runtime flags/caller scope. Source association alone does not place each flaw in libuuid/libblkid.',
 'zlib':'CVE27171 is a concrete source/version match with upstream negative-length fix; no stable backport. CVE85091 version/source mismatch remains explicit for independent review. Blind 1.3.2 upgrade is not adequate remediation.'}
groups=[]
for source,cids in sorted(source_ids.items()):
    rows=[r for r in matrix if r['source_package']==source]
    groups.append({'source_package':source,'ids':cids,'id_count':len(cids),'scanner_entries':sum(r['actual_scanner_entries'] for r in rows),'installed_binary_versions':sorted({v for r in rows for v in r['actual_installed_versions']}),'trixie_statuses':dict(Counter(r['debian_trixie']['status'] for r in rows)),'stable_fixed_versions':sorted({r['debian_trixie']['fixed_version'] for r in rows if r['debian_trixie'].get('fixed_version')}),'action':group_actions.get(source,'Apply the retained per-ID function/argument conditions to actual binary/linkage paths; monitor stable backport. Upstream patches and newer-release versions are recorded per ID and have not been built or installed.'),'primary_urls':[r['primary_url'] for r in rows]})
save('os-groups20-actions.json',groups)
# Retain every observed ELF, its original hash/linkage, package owner and source-level scan association.
pkgs={p['name'].split(':')[0]:p for p in native['dpkg_packages']};elf_rows=[];origin_counts=Counter()
for elf in native['elf_files']:
    row=dict(elf);owners=sorted({p.split(':')[0] for p in elf['dpkg_owners']});packages=[pkgs[p] for p in owners if p in pkgs];sources=sorted({p['source_package'] for p in packages});dist=[d['name'].lower() for d in elf['python_distributions']]
    origin='dpkg_owned' if packages else ('python_distribution_owned' if dist else 'unowned_dpkg_or_dist_metadata')
    origin_counts[origin]+=1;row.update({'origin_classification':origin,'actual_dpkg_metadata':packages,'source_level_os_ids':sorted({cid for s in sources for cid in source_ids.get(s,[])}),'association_limit':'Source-package and wheel ownership are inventory associations, not proof of vulnerable function presence or product reachability.'})
    notes=[]
    if 'cryptography' in dist:notes.append('OpenSSL 4.0.3 measured via cryptography API; outside all 13 retained CNA affected ranges exactly at the 4.0.3 fixed boundary. Other Rust/native components not exhausted by PyPI metadata scan.')
    if 'psycopg2-binary' in dist:notes.append('Exact Linux wheel ELF hash match available for all 16 owned ELF. Bundled OpenSSL 3.5.8 matches 13 CNA ranges; Debian libssl backport does not patch this copy. Other bundled library versions/backports require separate provenance; SONAME is not a release version.')
    if 'pillow' in dist:notes.append('Pillow feature versions measured, 26 owned ELF retained. Vendored liblzma 5.8.4 is fixed boundary for GHSA-5qpq-xqfv-j9pg; other native advisory coverage remains component-specific, not cleared by PyPI metadata scan.')
    if 'pyexpat.' in row['path'] or '_elementtree.' in row['path']:notes.append('Measured Expat2.8.5 and exact PSF source match CVE-2026-77214; standard Python bindings have length/GetBuffer guards; no broad reachability exclusion. CVE-2026-102633 requires32bit, observed ELF64.')
    if not packages and not dist:notes.append('Path suggests official /usr/local CPython base, recorded as inference only. Exact PSF/Git source provenance supports version/guard review, not binary rebuild equality.')
    row['native_component_notes']=notes;elf_rows.append(row)
assert len(elf_rows)==811 and len({r['path'] for r in elf_rows})==811
save('elf811-native-association.json',{'native_raw_sha256':before[str(NATIVE)],'scope':native['scope'],'observed_elf_count':811,'all_elf64':all(r['class_bits']==64 for r in elf_rows),'origin_counts':dict(origin_counts),'versions':native['versions'],'runtime_native_api_versions':native['runtime_native_api_versions'],'exact_component_paths':native['exact_component_paths'],'qt_scope':native['qt_scope'],'rows':elf_rows})
with (OUT/'elf811-native-association.csv').open('w',newline='',encoding='utf-8') as file:
    fields=['path','sha256','origin_classification','class_bits','needed','source_level_os_ids','python_distributions'];writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
    for row in elf_rows:writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row[k],(list,dict)) else row[k] for k in fields})
# Evaluate every retained numeric affected branch rather than assuming OpenSSL major 4 is safe.
def ver(s):assert re.fullmatch(r'\d+\.\d+\.\d+',s);return tuple(map(int,s.split('.')))
def affected(version,entries):
    found=[]
    for entry in entries:
        for r in entry.get('versions',[]):
            if r.get('versionType')!='semver':continue
            if ver(version)<ver(r['version']):continue
            if 'lessThan' in r and ver(version)>=ver(r['lessThan']):continue
            if 'lessThanOrEqual' in r and ver(version)>ver(r['lessThanOrEqual']):continue
            found.append(r)
    return found
openssl_rows=[];boundary_checks=[]
for path in sorted(OPENSSL.glob('CVE-*.json')):
    cna=json.loads(path.read_text());entries=cna['containers']['cna']['affected'];assert all(e['defaultStatus']=='unaffected' for e in entries)
    assert not affected('4.0.3',entries) and affected('4.0.2',entries) and affected('3.5.8',entries) and not affected('3.5.9',entries)
    boundary_checks.append({'id':path.stem,'4.0.2_affected':True,'4.0.3_affected':False,'3.5.8_affected':True,'3.5.9_affected':False})
    openssl_rows.append({'id':path.stem,'primary_url':'https://openssl-library.org/news/secjson/'+path.stem.lower()+'.json','cna_raw_sha256':before[str(path)],'cve_metadata':cna['cveMetadata'],'all_cna_affected_entries':entries,'actual_components':{'cryptography_bundled_4.0.3':{'numeric_range_match':False,'reason':'Exact fixed boundary 4.0.3; evaluated all numeric branches, custom 1.x ranges retained but not interpreted as numeric.'},'psycopg2_binary_bundled_3.5.8':{'numeric_range_match':True,'ranges':affected('3.5.8',entries),'status':'OPEN SEC09; build candidate not executed.'},'debian_libssl_3.5.7_u3':{'upstream_version_range_match':True,'backport_status':'DSA-6531-1 and actual installed 3.5.7-1~deb13u3 changelog cover these 13; exact Debian version controls, not upstream string alone. Existing raw/changelog proof retained.'}},'reachability':'No exploit/TLS path acceptance; component range/backport assessment only.'})
assert len(openssl_rows)==13
save('openssl13-all-branches-component-comparison.json',{'rows':openssl_rows,'numeric_boundary_checks':boundary_checks,'primary_cna_original_manifest_sha256':'9b35765886380a8bd9295c4d39285bdc04c16b4e2bc9bee3fd9d177850295797'})
# Prospective system dependencies are not installed in image99c.
pred=json.loads(DEPS.read_text())['predicted_new_packages'];pred_sources=sorted({r['source'].split(' ')[0] for r in pred});pred_rows=[]
component_notes={
 'CVE-2018-5709':'KDC database dump/reload; proposed runtime archives do not contain KDC utilities. Library-wide absence not claimed.',
 'CVE-2026-107708':'KDC principal processing; KDC server not in proposed four library archives.',
 'CVE-2026-107778':'rd_cred/make_cred_list library path: retain potential library applicability, no product authentication call-path proven.',
 'CVE-2026-11850':'LDAP KDC plugin path: proposed runtime archives lack KDC plugin; library-wide reachability not asserted.',
 'CVE-2024-26458':'libRPC condition requires specific API/callers; proposed four krb5 archives lack separate libgssrpc library. Verify actual build inventory.',
 'CVE-2024-26461':'GSS seal path can belong to proposed libgssapi; keep open until fixed stable package or demonstrated scope.',
 'CVE-2017-14159':'slapd daemon is not in libldap2 archive; whole-image postcondition remains pending.',
 'CVE-2017-17740':'slapd module condition is not in libldap2 archive; do not clear all LDAP library findings.',
 'CVE-2026-22185':'LMDB mdb_load utility is absent from libldap2 archive; no LMDB installation proposed.',
 'CVE-2015-3276':'CNA names Mozilla NSS TLS backend; proposed libldap2 actual backend must be verified by linkage/configuration before disposition.',
 'CVE-2020-15719':'LDAP TLS certificate-validation condition requires dedicated API/configuration review; source package still open.',
 'CVE-2026-107161':'DIGEST-MD5 plugin is not in pinned libsasl2-2 or libsasl2-modules-db archives; no libsasl2-modules installation proposed. Independent component-scope review and actual final file inventory required.'}
for src in pred_sources:
    for cid,data in tracker.get(src,{}).items():
        trixie=data.get('releases',{}).get('trixie')
        if not trixie or not (trixie['status']=='open' or cid in ['CVE-2026-40355','CVE-2026-40356']):continue
        selected.setdefault(src,{})[cid]=data
        pred_rows.append({'source_package':src,'id':cid,'primary_url':'https://security-tracker.debian.org/tracker/'+cid,'debian_description':data['description'],'trixie':trixie,'all_release_status':data.get('releases',{}),'expected_packages':[p for p in pred if p['source'].split(' ')[0]==src],'component_review':component_notes.get(cid,'Source range/status only; specific component reachability has not been established.'),'scope':'PREDICTED d038 closure only; not installed in image99c. No CVE total added to current scan.'})
save('candidate10-os-dependency-triage.json',{'candidate':'d038f1c3860296f42ba41ce9ee64a8a4e6300ebc; runtime-cleanup child af548f71a8a763ba523853e85903a9ab8cf2b0a7','expected_new_packages':pred,'source_packages_with_no_open_trixie_records_in_snapshot':[s for s in pred_sources if not any(r['source_package']==s and r['trixie']['status']=='open' for r in pred_rows)],'rows':pred_rows,'limits':'Static dependency closure/archive inspection, not APT resolution, installed inventory or clean scan. Native upstream/branch applicability remains per component.'})
save('debian-primary-selected-all-scopes.json',{'raw_sha256':before[str(TRACK)],'selected':selected})
native_ids={r['id'] for r in openssl_rows};os_ids=set(ids)
save('id-set-relationships.json',{'os_scanner_identifiers':ids,'openssl_sec09_cna_identifiers':sorted(native_ids),'intersection':sorted(native_ids & os_ids),'union_identifiers':sorted(native_ids | os_ids),'os_identifier_kinds':dict(Counter('CVE' if x.startswith('CVE-') else 'TEMP' for x in ids)),'limits':'Explicit set relationship only. OS71 and vendoredOpenSSL13 remain separate scopes; affected range, aliases, reachability and mitigations are not interchangeable counts. Expat and pip vendor findings are not silently added to these historical counts.'})
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};assert before==after
summary={'completed_utc':datetime.now(timezone.utc).isoformat(),'image_id':'sha256:99c846bd28b0d464c837a72fc6340df1c9583834b2529c8bde18bd6d7544410c','image_source_head':'bc365c13b9af9e24129a56b4068059a67bb3afa0','os_packages':87,'os_entries':164,'os_identifiers':71,'source_groups':20,'current_debian_trixie_open':sum(r['debian_trixie']['status']=='open' for r in matrix),'os_fixed_version_available':0,'elf_count':811,'elf_origin_counts':dict(origin_counts),'openssl_cna_rows':len(openssl_rows),'openssl_numeric_boundary_cases':4*len(boundary_checks),'predicted_os_packages_not_installed':10,'predicted_source_advisory_rows':len(pred_rows),'static_source_guards':16,'bounded_pip_vendor_function_mocks':3,'actual_python_distribution_queries':55,'actual_python_distribution_osv_matches':0,'pip_vendor_version_cve_matches':6,'pip_vendor_affected_code_present':3,'pip_vendor_matches_with_missing_affected_files':3,'runtime_installer_cleanup_candidate':'af548f71a8a763ba523853e85903a9ab8cf2b0a7','inputs_quiet':True,'input_hashes_before':before,'input_hashes_after':after,'scope':'Read-only primary/archive/source triage plus separate isolated Dockerfile candidate; no image rebuild, QEMU boot, actual binary exploit or web startup. No OS71/SEC09 closure.'}
save('triage-summary.json',summary)
print(json.dumps({k:v for k,v in summary.items() if not k.startswith('input_hashes')},indent=2))
