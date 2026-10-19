from pathlib import Path
import collections,csv,hashlib,json,re

LAB=Path(r'F:\MetodoBaseWeb-linux-lab-20261019')
ROOT=LAB/'evidence/os-audit-abd559a'
PRIMARY=ROOT/'triage-primary'
OUT=ROOT/'triage-matrix';OUT.mkdir(exist_ok=False)
rows=json.loads((PRIMARY/'selected-debian-entries.json').read_text())
pages={p['id']:p for p in json.loads((PRIMARY/'page-extracts.json').read_text())}
components=json.loads((ROOT/'component-applicability-v2/component-metadata.json').read_text())
scan=json.loads((ROOT/'results/scan.json').read_text())
packages={p['Name']:p for r in scan['Results'] for p in r['Packages']}
group_notes={
 'apt':'apt-key no existe físicamente. Debian describe una condición de keyring URI; revisar esa condición antes de aceptar no aplicabilidad. APT sigue presente.',
 'bash':'La escalada descrita requiere transición entre identidades y shell. Falta demostrar el flujo real y revisar la referencia upstream; no hay cierre por ejecutar como UID 999.',
 'util-linux':'mount es SUID 4755; nsenter y login existen. fstab está sin configurar. Los cuatro HIGH requieren hooks/montajes o nsenter privilegiado; el kernel del laboratorio es 6.1, pero el kernel de despliegue futuro no está validado. chfn/chsh son de shadow y Debian indica que no se compilan desde util-linux.',
 'coreutils':'Riesgos de utilidades concretas sobre argumentos/archivos controlados y, en algunos casos, operaciones privilegiadas. Se requieren revisión de llamadas operativas y parches del mantenedor; una nota de baja relevancia no elimina el hallazgo.',
 'dash':'Se requieren condiciones del matcher o argumentos de printf/echo y verificar las opciones de compilación. El shell existe en la imagen; no se probaron entradas malformadas.',
 'diffutils':'La condición afecta diff3 y su programa diff. Se cita corrección upstream; falta demostrar si ese flujo recibe datos externos en operación.',
 'gcc-14':'Solo hay bibliotecas de runtime, no el compilador/headers. erase_if puede estar instanciado en consumidores nativos; actualizar libstdc++ no prueba que un binario ya compilado quede corregido. Revisar SBOM/compilación de extensiones y el parche GCC 14.',
 'acl':'libacl está presente. getfacl/setfacl/chacl no existen físicamente. El ID de funciones de biblioteca requiere analizar llamadores y rutas bajo privilegios; el ID de CLI tiene evidencia de componente ausente para revisión.',
 'attr':'Solo se inventaría libattr; getfattr/setfattr no existen físicamente. La vulnerabilidad descrita es de esas utilidades. Propuesta de no aplicabilidad pendiente de revisión, conservando el resultado bruto.',
 'bzip2':'La biblioteca está presente; bzip2recover no existe físicamente. El defecto descrito es de esa utilidad. No se aplica una excepción automática.',
 'glibc':'libc6/libc-bin están presentes y CPython depende de libc. Hay condiciones distintas de regex, locale, conversión o APIs por ID. Varias tienen parches o versión Debian posterior; no se extrapola cierre desde un único caso ni desde aislamiento del laboratorio.',
 'xz-utils':'DSA y TEMP remiten a la misma GHSA, sin CVE asignado. La extensión Python _lzma enlaza liblzma.so.5. Hay backport estable u2 verificado por APT; el cambio está escrito, aún requiere inventario y nuevo scan de la imagen construida.',
 'ncurses':'infocmp existe y el HIGH corresponde a esa utilidad. El otro ID involucra tparm/libtinfo. Faltan revisión de entradas y uso; el entorno web sin TTY no demuestra por sí solo ausencia de la ruta.',
 'pam':'Se requiere pam_userdb y un servicio que autentique por esa ruta. Hay bibliotecas/PAM; no se verificó la configuración completa de despliegue ni se ejercitó autenticación.',
 'sqlite3':'SQLite real 3.46.1. sqlite3changeset_apply_v3 y sqlite3_zipfile_init no están exportados; apply_v2 y changegroup_add sí. Revisar cada ID: la ausencia del símbolo v3 no permite cerrar otros caminos de Session o bases corruptas.',
 'systemd':'Solo libsystemd0/libudev1 están instaladas desde esta fuente; no hay homed, oomd, journald ni systemd-tmpfiles en las rutas medidas. Evidencia concreta de componente ausente para esos servicios, pendiente de revisión y sin eliminar entradas del scanner.',
 'shadow':'su/chfn/chsh SUID están presentes; newuidmap está ausente. Revisar configuración de login/btmp/subuid y operaciones administrativas. La ausencia de SSH en la imagen no resuelve automáticamente estos IDs.',
 'perl':'perl-base incluye File::Temp y el motor regex. Archive::Tar y Pod::Text no se encuentran en @INC. Los IDs de esos módulos tienen evidencia de ausencia; los otros requieren revisión. fix_deferred continúa abierto aunque haya parche upstream.',
 'sysvinit':'No hay init en la ruta medida; sulogin sí está presente. Se necesita evaluar el escenario de instalación/recuperación descrito, distinto del CMD web; sin excepción automática.',
 'tar':'tar y rmt están presentes. Deben revisarse extracción/restauración y argumentos con archivos no confiables; no se ejecutaron exploits. Los parches citados y las condiciones se conservan por ID.',
 'zlib':'La biblioteca está presente. Se requieren llamadas concretas a crc32_combine64 o gz* y sus precondiciones. No se asume seguridad porque la aplicación use una API de compresión distinta.'}
special={
 'CVE-2011-3374':('component_absence_for_review','apt-key ausente; condición de keyring URI indicada por Debian aún requiere decisión de revisión.'),
 'CVE-2022-0563':('source_component_mapping_for_review','Debian declara chfn/chsh deshabilitados en util-linux; los ejecutables presentes pertenecen a shadow, no a esa compilación vulnerable.'),
 'CVE-2026-54370':('component_absence_for_review','getfacl/setfacl/chacl ausentes; libacl presente. Revisar que el ID se limita a las utilidades descritas.'),
 'CVE-2026-54371':('component_absence_for_review','getfattr/setfattr ausentes; biblioteca libattr presente.'),
 'CVE-2026-42250':('component_absence_for_review','bzip2recover ausente; biblioteca bzip2 presente.'),
 'CVE-2026-16742':('component_absence_for_review','systemd-homed ausente; no usuario homed ejercitado.'),
 'CVE-2026-15059':('component_absence_for_review','systemd-oomd ausente; API IPC afectada no encontrada en las rutas de componente.'),
 'CVE-2013-4392':('component_absence_for_review','systemd-tmpfiles ausente; condición systemd+SELinux descrita por Debian no ejercitada.'),
 'CVE-2023-31437':('component_absence_for_review','journald ausente; no se valida ni manipula sellado de journals.'),
 'CVE-2023-31438':('component_absence_for_review','journald ausente; no se valida ni manipula sellado de journals.'),
 'CVE-2023-31439':('component_absence_for_review','journald ausente; no se valida ni manipula sellado de journals.'),
 'CVE-2026-40228':('component_absence_for_review','journald ausente; ForwardToWall no ejercitado.'),
 'CVE-2026-9538':('component_absence_for_review','Archive::Tar ausente en @INC; el motor Perl sí está presente. Sin excepción aceptada.'),
 'CVE-2026-82560':('component_absence_for_review','Pod::Text ausente en @INC; no extrapolar a File::Temp o regex.'),
 'CVE-2026-50812':('symbol_absence_for_review','SQLite 3.46.1 no exporta sqlite3changeset_apply_v3; otras APIs Session sí existen.'),
 'CVE-2025-70873':('component_absence_for_review','sqlite3_zipfile_init no exportado; Debian indica que la extensión zipfile no se construye para sus binarios.'),
 'CVE-2026-78409':('deployment_preconditions_unproven','mount presente/SUID; fstab vacío. Kernel TCG 6.1 inferior al camino >=6.15 descrito; kernel de producción desconocido.'),
 'DSA-6549-1':('stable_fix_available_unbuilt','Alias de la misma GHSA de XZ que TEMP-1147318-639065; backport liblzma5 u2 preparado.'),
 'TEMP-1147318-639065':('stable_fix_available_unbuilt','Misma GHSA que DSA; _lzma enlaza liblzma5. Reuso del decoder + fallo de asignación; sin exploit probado.')}
by_id={}
for row in rows:by_id.setdefault(row['id'],[]).append(row)
matrix=[]
for identity,entries in sorted(by_id.items()):
    first=entries[0];entry=first['debian_primary'] or {};target=entry.get('releases',{}).get('trixie',{})
    page=pages[identity];notes=page['text'].split('Notes',1)[1].split('Search for package',1)[0] if 'Notes' in page['text'] else ''
    fixes=re.findall(r'Fixed by:\s*(https?://\S+)',notes)
    newer={name:{k:value.get(k) for k in ['status','fixed_version']} for name,value in entry.get('releases',{}).items() if name in ('sid','forky') and value.get('status')=='resolved' and value.get('fixed_version') not in (None,'','0')}
    if identity=='DSA-6549-1':target={'status':'resolved','fixed_version':'5.8.1-1+deb13u2','source':'DSA primary HTML table; DSA is absent from CVE JSON feed.'}
    classification,condition=special.get(identity,('reachability_unproven',group_notes[first['source_package']]))
    if fixes:upstream='Tracker cita parche upstream; no demuestra backport binario instalado.'
    elif newer:upstream='Hay versión Debian sid/forky corregida; no demuestra corrección en trixie instalado.'
    else:upstream='No se estableció una corrección upstream verificada en esta pasada; conservar seguimiento del mantenedor.'
    matrix.append({'id':identity,'kind':'CVE' if identity.startswith('CVE-') else 'DSA' if identity.startswith('DSA-') else 'TEMP',
     'source_package':first['source_package'],'binary_packages':sorted({p['binary_package'] for p in entries}),'scanner_entries':len(entries),
     'scanner_statuses':sorted({p['scanner_status'] for p in entries}),'scanner_severities':sorted({p['scanner_severity'] for p in entries}),
     'debian_trixie':target,'installed_fix_available':sorted({p['scanner_fixed_version'] for p in entries if p['scanner_fixed_version']}),
     'primary_url':first['primary_url'],'tracker_explicit_upstream_fix_links':fixes,'newer_debian_fixed_releases':newer,
     'upstream_fix_assessment':upstream,'applicability_classification':classification,'applicability_evidence':condition,
     'review_state':'OPEN; no accepted exception, filtering or risk acceptance','alias_group':'GHSA-5qpq-xqfv-j9pg' if first['source_package']=='xz-utils' else None,
     'debian_primary_page_sha256':page['sha256']})
assert len(matrix)==73 and sum(p['scanner_entries'] for p in matrix)==166
assert len({p['source_package'] for p in matrix})==21
(OUT/'matrix-73.json').write_text(json.dumps(matrix,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
groups=[]
for name in sorted(group_notes):
    items=[p for p in matrix if p['source_package']==name]
    groups.append({'source_package':name,'ids':len(items),'entries':sum(p['scanner_entries'] for p in items),
     'scanner_status_entries':dict(collections.Counter(row['scanner_status'] for row in rows if row['source_package']==name)),
     'open_trixie_ids':sum(p['debian_trixie'].get('status')=='open' for p in items),
     'ids_with_tracker_explicit_upstream_fix':sum(bool(p['tracker_explicit_upstream_fix_links']) for p in items),
     'ids_with_newer_debian_fixed_release':sum(bool(p['newer_debian_fixed_releases']) for p in items),'applicability':group_notes[name]})
(OUT/'groups-21.json').write_text(json.dumps(groups,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
with (OUT/'matrix-73.csv').open('w',encoding='utf-8',newline='') as stream:
    writer=csv.writer(stream);writer.writerow(['ID','Fuente','Binarios','Entradas','Estado scanner','Estado trixie','Fix trixie','Referencia primaria','Parche upstream citado','Corrección Debian posterior','Aplicabilidad','Decisión'])
    for p in matrix:writer.writerow([p['id'],p['source_package'],','.join(p['binary_packages']),p['scanner_entries'],','.join(p['scanner_statuses']),p['debian_trixie'].get('status'),p['debian_trixie'].get('fixed_version'),p['primary_url'],' '.join(p['tracker_explicit_upstream_fix_links']),json.dumps(p['newer_debian_fixed_releases']),p['applicability_evidence'],p['review_state']])
lines=['La matriz conserva las 166 entradas: 67 CVEs, cinco IDs TEMP y un DSA, agrupados en 73 identificadores y 21 paquetes fuente. DSA-6549-1 y TEMP-1147318-639065 corresponden a una misma GHSA de XZ; no son dos defectos ni dos paquetes. No hay excepciones aceptadas.\n',
 'El estado `fixed` del scanner significa que existe corrección para la versión vulnerable instalada. `resolved` en Debian describe la disponibilidad en la distribución; no confirma instalación en la imagen examinada. Los otros 71 identificadores siguen `open` en trixie; dos entradas Perl están `fix_deferred` en el scanner.\n',
 'La presencia de bibliotecas no prueba que toda vulnerabilidad de su paquete fuente afecte al binario. Las ausencias medidas son propuestas para revisión, sin borrar hallazgos ni aplicar ignores. `matrix-73.json` conserva todos los enlaces de parches explícitos y versiones corregidas en sid/forky; esos enlaces son evidencia citada por el tracker, no una prueba de backport o compatibilidad binaria en trixie.\n',
 '| Paquete fuente | IDs / entradas | Estado scanner (entradas) | Evidencia y trabajo de aplicabilidad |', '|---|---:|---|---|']
for g in groups:lines.append('| '+g['source_package']+' | '+str(g['ids'])+' / '+str(g['entries'])+' | '+', '.join(k+': '+str(v) for k,v in g['scanner_status_entries'].items())+' | '+g['applicability'].replace('|','/')+' |')
lines+=['\nEl seguimiento por ID está completo en el CSV/JSON; esta tabla resume corrección y decisión sin reproducir descripciones ajenas.\n','| ID / primaria | Fuente | Entradas / estado | Corrección observada | Aplicabilidad / decisión |','|---|---|---|---|---|']
for p in matrix:
    correction=('trixie '+','.join(p['installed_fix_available']) if p['installed_fix_available'] else 'Parche upstream citado' if p['tracker_explicit_upstream_fix_links'] else 'Debian sid/forky corregido' if p['newer_debian_fixed_releases'] else 'No establecida en esta pasada')
    lines.append('| ['+p['id']+']('+p['primary_url']+') | '+p['source_package']+' | '+str(p['scanner_entries'])+' / '+','.join(p['scanner_statuses'])+' | '+correction+' | '+p['applicability_classification']+'; abierto |')
(OUT/'TRIAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
summary={'ids':len(matrix),'entries':166,'source_groups':21,'id_kinds':dict(collections.Counter(p['kind'] for p in matrix)),
 'ids_with_explicit_tracker_upstream_fix_links':sum(bool(p['tracker_explicit_upstream_fix_links']) for p in matrix),
 'ids_with_newer_debian_fixed_release':sum(bool(p['newer_debian_fixed_releases']) for p in matrix),
 'applicability_review_counts':dict(collections.Counter(p['applicability_classification'] for p in matrix)),
 'accepted_exceptions':0,'scope':'First applicability triage with primary vendor data and measured component metadata. No exploit test, no complete native dependency reachability proof, no OS-green acceptance.'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,indent=2))
