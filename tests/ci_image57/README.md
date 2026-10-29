Current-image57 is a new entrypoint. Historical image33 and its helpers are unchanged.

Use an explicit full Git commit and fresh absolute directories outside the checkout:

```text
python -I -B tests/run_current_image57.py --repository /checkout --source FULL40HEX --private-root /private/new-run --public-root /public/new-run --prepare-only
python -I -B tests/run_current_image57.py --repository /checkout --source FULL40HEX --private-root /private/another-run --public-root /public/another-run --build-probe
```

Each invocation prepares original Git bytes without checkout/export filters. The source TAR includes only the finite Docker COPY inputs. Its manifest records every blob, mode, size and SHA256. A second artifact contains the original commit and all necessary trees; the closed-context consumer verifies complete COPY membership against that commit without invoking Git. The 12 critical container inputs, 21-object original native recipe, 56 unchanged web lock blocks plus source-built psycopg2, and the reviewed 57-distribution catalog remain mandatory.

The APP inventory and executable modes derive from the chosen source. The four B19 corpus files are mandatory, including the reviewed payload SHA256 `d0d787734cd3ad38731ca3012e34532ff109e915feeb152cbf0fbd361c27c101`, its 99,999 sorted unique SHA256 records and license identity. This entrypoint has no final candidate commit pin; the caller supplies and records the reviewed source.

The prepare phase creates no image or container. The build phase attempts one build with `--pull=false` and one diagnostic probe against the actual immutable resulting image ID. It uses a unique owned name/nonce, network none, read-only root, user999, cap-drop ALL, no-new-privileges, memory512MiB, CPU1 and pids128. These are explicit test flags. The container is retained without `--rm`; ownership, ID, inspect, build log, stdout and stderr remain private even on failure. There is no automatic retry, prune or cleanup.

The probe preserves every original native function byte and binds only source hashes/modes and source labels. Its report checker requires the complete57 package/version/module inventory, all11 named XML cases, native linkage/exports/attestation and the exact APP inventory. It reports an import/native diagnostic, without application startup, migrations, providers, SBOM/SCA or overall product acceptance.

Private evidence receives a verified two-ACE User+SYSTEM DACL before payload on Windows, or owned0700 on Linux. Originals are closed in a private ZIP with full readback. Only a finite JSON projection is published after the original two-part-token, three-part-CSRF, factor-material and expanded-ZIP scanner.

Offline controls require an existing private artifact directory:

```text
python -I -B tests/test_ci_image57_offline.py --artifact-root /private/fresh-small-controls
```

Their positive report and mocked Docker transport are synthetic structural controls. They do not accept an image, execute Docker or replace a real Linux build/probe. The frozen source26b preparation evidence is also a historical demonstration, not the final source or the prior144/59 runtime result.

The separate current39 startup gate consumes the closed contract and immutable
image ID from that build, with fresh private/public evidence directories:

```text
python -B -X utf8 -m tests.ci_image57.current39_startup --contract /private/build/runtime-input-contract.json --contract-sha256 SHA256 --image-id sha256:IMAGE_ID --private /private/new-startup --output /public/new-startup
```

It requires Linux Docker and the dedicated synthetic PostgreSQL service at
127.0.0.1:55483/metodobase_test_image, with explicit
`METODOBASE_TEST_MIGRATOR_URL` and `METODOBASE_TEST_POSTGRES_URL` using the separate
`metodobase_test_admin`/`metodobase_test_app` roles. It refuses an existing app role.
It migrates through the exact image, then starts `/app/entrypoint.sh`, observes
`/health/ready`, and checks actual `web/main_web.py` PID1, schema39, all44 ORM/45
physical tables,35 FORCE RLS tables, restricted/nonowner role, complete source
hashes and normal owned-container closure. Logs, environment files and database
URLs remain private. Its summary explicitly identifies synthetic testing settings;
production configuration, real browsers and SBOM/SCA remain separate gates.
The historical33 runner and its schema witnesses are preserved unchanged.
