# CI28 history and landing extension

`ci28-before.yml` is the exact LF-normalized workflow from commit
`dd9877350aad3f483299c990a1e97aab63c83f5d`, before this extension. Its SHA256 is
`ec7938ccb76783666023588147685c0acf84454040f5e94d09a839bd06b18524`.
The maintained verifier pins both this snapshot and the accepted historical
`verify_recovery_ci.py`, which verifies its own CI27 references and CI28 delta
against this snapshot. Historical verifier assertions stay unchanged.

The only workflow additions are 23 history VM cases, two isolated browser
fixtures with startup identity/revision checks (10 history and 8 landing groups,
four screens each), their evidence uploads, and this verifier in test-web.
All previous jobs, 21 PostgreSQL reports, restore28, seven browser invocations,
process ownership checks and acceptance minimums remain in the expected tree.

The verifier checks the complete parsed workflow, 13 unauthorized mutations,
Bash syntax/references, and 16 inert process/report/startup cases. Inert cases
use the actual unchanged fixture function, real report/startup parsers and
owned sleeping Bash children. They prove wiring and cleanup, without claiming
a real browser, database, container or Actions run. Real browser validation
uses the maintained fixture and driver in a separate integration gate.
