# Independent current37 SaaS native preparation

Product freeze: `50325b464169fc750d9f39e339d874a716030797`. This is a new fixture and driver. The older native35/37 PostgreSQL fixtures and historical browser drivers are unchanged. Preparation is offline; it does not establish native, SQL migration, accessibility, layout or print acceptance.

The new fixture requires port8812, a fresh existing protected Temp directory named `metodobase-test-routines37-*`, and a separate finite Root lease. It checks product Git content before environment/SQL setup. Only after authorization does it run the real migration to `20261020_account_security`, verify41ORM/42physical SQLite tables and foreign keys, seed owner/personal/team-VIEWER plus personalB, and start the real `web.main_web.create_app`. No create-all/stamp fallback, authentication dependency override or test HTTP authority route exists. Provider configuration is off and external sockets are guarded. Credentials and exact runtime-source map remain private. The Node helper performs actual password enrollment/reauth/TOTP confirmation/recovery through unchanged HTTP functions; the UI login fills both fields and presses Enter, then uses actual MFA and browser-cookie replies. No token is injected into the product API or browser Storage.

Root lease JSON binds `approved:true`, scope `routines37-saas-sqlite-native-exclusive-v1`, complete `source_commit`, absolute `private_directory`, exact RAW `fixture_sha256` and `driver_sha256`, `port:8812`, `expires_at_UTC` within four hours, `node_dependencies_directory`, `chrome_executable` and its RAW `chrome_executable_sha256`. The fixture validates its own fields before side effects; the browser validates both files/tool paths before importing Playwright or launching Chrome. Each new browser phase revalidates expiry. Expiry does not skip normal cleanup of an already started own browser. Root must independently bind resources and process ownership/birth/argv; these tests grant no lease.

Offline commands (no services):

```text
WEB92python -B -X utf8 tests/e2e/security_routines37_server_peer.py --source 50325b464169fc750d9f39e339d874a716030797 --check-only
Node24 tests/e2e/security_routines_browser37_peer.cjs --compile-only
WEB92python -B -X utf8 tests/run_isolated.py tests/test_security_routines_native_preparation_peer.py tests/test_security_routines_timer_a11y_peer.py -q
```

Future execution, only after Root authorizes the exclusive window:

```text
WEB92python -B -X utf8 tests/e2e/security_routines37_server_peer.py --source 50325b464169fc750d9f39e339d874a716030797 --private ABSOLUTE_PROTECTED_PRIVATE --lease-ack ROOT_ACK --serve
Node24 tests/e2e/security_routines_browser37_peer.cjs --run
```

The driver receives `ROUTINES37_FIXTURE_PRIVATE`, `ROUTINES37_ROOT_ACK` and absolute `ROUTINES37_PYTHON` pointing to the unchanged WEB92 interpreter. Shared read-only dependencies default to Main's existing `tests/e2e/node_modules`; Chrome defaults to the installed executable. Explicit overrides must equal the lease. Root creates private ACLs before payload, journals startup PID/birth and closes only the owned server normally after the driver exits. No dependency copying, install, pruning, forced cleanup or process-wide termination is provided here.

The finite plan covers owner gym, standalone personal and team VIEWER in both spaces at320/390/768/1440 (16scoped captures). Actual catalogue200, private headers and4/4/5exercises precede assertions. Keyboard menu Enter/Escape/focus and collapsed off-canvas tab stops, circular invalid-week/reset, native details, timer pause/reset and silent clock semantics are tested. PDF printing checks all three sessions/all exercises and sources, print CSS and detail restoration; it does not prove an operating-system print dialog. Scoped axe violations and horizontal overflow must be empty; no screen-reader claim is made. All external browser requests are aborted; product API requests pass through unchanged.

Negative acceptance uses an actual403 with the current personal actor, an explicit accountB login and real SQLite SV revocation. The last test invokes the actual exported catalogue transport after a separately authorized private control increments one whitelisted own actor's persisted SV. It does not fabricate a successful API reply. This intentional fixture write is outside the catalogue read, whose no-DML contract was independently tested. Failures stop dependent criteria; partial screenshots/cases are retained and never converted to global acceptance. Accesses, passwords, factors and kits stay out of reports/stdout. Screenshots and original reports are private.

The timer semantic canary was1RED/1control on6f130 and2/2after ROOT's two-attribute fix. [W3C ARIA in HTML](https://www.w3.org/TR/html-aria/#el-output) maps output to status and permits a timer role. [WAI-ARIA1.2](https://www.w3.org/TR/wai-aria-1.2/#timer) specifies timer's implicit live-off behavior; the independent polite state-message region remains intact. This is semantic/source verification, not measured assistive-technology announcements.
