QA-33: completion evidence for Gitleaks 8.30.1

Source freeze: `b3b1846a4e9c30d25b506112ce0ab6fbc7771586`. These are bounded harness controls, not a project scan or release approval. Root's Main25d1 result43532 remains UNACCEPTED: the old wrapper did not establish complete execution. The decrease in counts alone does not prove the cause of that actual run.

The unchanged classification/configuration/V8 data are outside this delta. The scanner now uses internal timeout0 and external600seconds, retains redacted-tool diagnostics and raw report privately, requires empty stdout and exactly the complete INF scanned-bytes record plus the matching WRN finding count or INF no-leaks record. Missing/duplicate/partial/error/skip/unexpected records fail closed. Public output excludes raw diagnostics.

Evidence root must be fresh, absolute and external to the deliverable. On Windows, its protected DACL is set to User+SYSTEM full control, then independently read via WinAPI and verified before payload. Explicit Administrators/OWNER RIGHTS ACEs caused the preserved44/45 refusal; grants alone were insufficient. The fix replaces the fresh-directory DACL and keeps the strict oracle. POSIX requires owner UID and mode0700.

Phases (all original results preserved):

- Baseline completion controls:12FAIL+1PASS, including exit1 plus classified finding and partial/error stderr incorrectly accepted.
- Initial completion fix:13/13 PASS.
- Additional unexpected-stdout canary:1FAIL before its fix.
- Added semantic Windows boundary:44PASS+1FAIL, correctly refusing extra explicit ACEs before payload.
- Final source:45/45 PASS,0F/E/skip, all independently collected IDs exact; source and92 installed distributions plus3 Node packages/157 installed files quiet; pip check0/0.
- Real bounded synthetic timeout1:1.75seconds,32809277input bytes, tool exit1,0redacted findings and explicit ERR/partial diagnostics. This corroborates the exit-code ambiguity; it is not a project scan.

The original safety11 source remains byte exact. The explicit companion verifies its finite LF/CRLF pins and preserves every original function code object, defaults and pytest markers. It only supplies authentic complete-summary framing to successful mocks, whose raw finding fields still carry the original privacy canary. The original module is preserved; final CI must require the companion11 instead of collecting the obsolete diagnostic-free positive mocks.

Root independently replayed all 45 controls after this source freeze: 45 PASS, no failures, errors or skips, with 1409 source files and WEB92 installed files/interpreter quiet and pip check 0/0. Its private receipt is `C:/Users/Consu/AppData/Local/Temp/metodobase-root-qa33-peer45-private-20261021`. Root accepted the six source files for the next bounded native controls; SEC review and actual complete positive controls are still pending. No Gitleaks process, PostgreSQL, Chrome, VM or Redis was used in final45. A bounded prior real timeout control closed before the Native lease. The project fullscan remains unaccepted.
