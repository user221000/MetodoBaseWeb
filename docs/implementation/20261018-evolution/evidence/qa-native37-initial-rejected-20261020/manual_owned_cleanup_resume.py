"""Resume only after original post-termination image lookup failed; never rerun termination."""
from pathlib import Path
import json
import hashlib
source_path = Path(__file__).with_name('manual_owned_cleanup.py')
original = source_path.read_text(encoding='utf-8')
head = original[:original.index('script = ')]
exec(compile(head, str(source_path), 'exec'))
put('manual-cleanup-first-wrapper-error.json', {
    'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
    'error_class': 'AssertionError', 'site': 'observe_handle.QueryFullProcessImageNameW after termination',
    'execution_reached': 'after worker TerminateProcess and redirector wait/actions, before DB connect',
    'termination_actions_not_repeated': True,
    'public_tool_output_recorded_separately': True})
closed = []
for pid in (27404, 27324):
    handle = api.OpenProcess(0x1000 | 0x100000, False, pid)
    if not handle:
        assert ctypes.get_last_error() in (87, 1168)
        closed.append({'pid': pid, 'birth': EXPECTED[pid], 'state': 'absent'})
        continue
    try:
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        assert api.GetProcessTimes(handle, *[ctypes.byref(x) for x in (created, exited, kernel, user)])
        actual = (created.dwHighDateTime << 32) | created.dwLowDateTime
        if actual != EXPECTED[pid]:
            closed.append({'pid': pid, 'birth': EXPECTED[pid], 'state': 'original_generation_absent_PID_reused'})
        else:
            wait = api.WaitForSingleObject(handle, 0)
            code = wintypes.DWORD()
            assert api.GetExitCodeProcess(handle, ctypes.byref(code))
            assert wait == 0 and code.value != 259, 'Original process is still active; no DROP permitted'
            closed.append({'pid': pid, 'birth': actual, 'state': 'terminated_exact_process_object',
                'wait_zero': wait, 'exit_code': code.value})
    finally: api.CloseHandle(handle)
put('manual-server-process-closure-resume.json', {
    'after': closed, 'normal_server_exit': False,
    'classification': 'manual authorized recovery after server TimeoutExpired',
    'original_cleanup_source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
    'no_termination_action_in_resume': True})
exec(compile(original[original.index('import psycopg2\n'):], str(source_path) + ':DB-cleanup-unchanged', 'exec'))
