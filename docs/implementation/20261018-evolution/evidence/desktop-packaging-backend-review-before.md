# Independent desktop packaging review

Reviewed commit: `41ad55f1a238422a2f7c86a64ad2469977e7ff8a`, isolated worktree
`F:/MetodoBaseWeb-desktop-20261019`, base `0e8cd42`. All 19 commit files were
examined, including the historical test artifacts. Product, desktop sources and
the execution worktree were not edited. No build, Analysis, GUI, installer,
license operation, network provider, push or deployment was executed.

## Blocking finding

**P1: source provenance can claim a commit whose tracked code differs.**
`build.py:252-272` validates HEAD and `git status`, then hashes the working files
without establishing that their bytes represent the requested commit. Git's
`assume-unchanged` and `skip-worktree` flags can hide tracked modifications from
that status check. The first accepted snapshot then becomes the reference for
the later before/after comparison, so unchanged unreviewed bytes remain accepted.
`build_executable` would label the manifest with the supplied commit anyway.

Reproduced independently in two new temporary Git repositories, with no build:
commit a synthetic main.py; set one index flag; replace its contents; obtain a
clean status; call the unchanged source_snapshot with the correct HEAD. Both
variants were accepted and recorded the modified working hash instead of the
committed hash. The probe never executes either synthetic source file.

Before evidence is preserved in `desktop-packaging-backend-review.provenance.py`
and `.provenance.json`. Root and the packaging author were notified. Require an
explicit comparison against the selected commit's blobs under a reviewed checkout
normalization/filter policy; flags/status alone are insufficient proof. Regressions
must cover both flags and any permitted content filters, without mutating the
operator's index. This finding blocks artifact provenance acceptance, not the
continued development of the isolated recipe. No live incident is asserted.

An additional exploratory local-filter probe was rejected by the guard; its raw
artifact is preserved separately and is not presented as another reproduction.

## Verified bounded behavior

The available packaging suites passed **58 tests in 7.02 seconds** under the
external isolated Python 3.12.13 runner. PyInstaller constructors and GUI
subprocesses are doubles; temporary Git repositories, junctions and ZIP payloads
are real. This independently confirms source-test behavior, not a packaged app.

- The spec selects actual `main.py`, PySide6, EXE/COLLECT onedir and `_internal`.
  The real entrypoint uses QApplication and the desktop flow; its error branches
  and full product/license flows remain outside a mocked packaging test.
- Required Inter/QSS and native/offscreen platform plugins are checked. Resource
  data are selected from tracked files with explicit roots/extensions rather
  than copying config/core/src wholesale. Missing resources and linked paths fail.
- The manifest covers the exact file set and size/SHA256. ZIP creation includes
  the full dependency tree and manifest, verifies the archived bytes, and publishes
  via a temporary sibling plus replace. The transient source-mutation negative
  matters: restoring the source before the second verification does not cause
  corrupted archive bytes to be accepted.
- Names matching the private-data policy are rejected before manifest generation.
  This is an explicit filename/resource boundary, not proof that arbitrary
  dependency bytes never contain a secret. A frozen reviewed source/runtime and
  artifact secret scan remain separate checks.
- The diagnostic wrapper supplies private Temp cwd, HOME/USERPROFILE,
  APPDATA/LOCALAPPDATA and METODOBASE_DATA_DIR; inherited provider/DB settings are
  excluded. The hook loads font/theme/login only and exits before main's business
  flow. Its declared Python socket patch is not operating-system isolation.
- Existing tests prove junction/symlink refusal and ZIP write/read race handling.
  They do not prove resistance to an adversary concurrently replacing the entire
  private workspace namespace. No diagnostic/build was run to make that claim.
- Tooling is separately pinned with hashes. Runtime installation, actual native
  PyInstaller analysis, clean-machine GUI and native platform acceptance remain
  pending. The Windows-only tooling audit does not cover uninstalled macOS extras.

## Legacy entrypoints remain real work

These are not closed or accepted by the 58 synthetic tests:

- `setup.py:37` and `build_config.py:27` still copy broad config/source directories
  as data and import product constants; neither delegates to the reviewed recipe.
  build_config also documents source replacement for obfuscation.
- `build_all.bat:20-23` recursively deletes relative paths and the tracked spec,
  runs unisolated tests and dispatches to setup.py. It lacks the new source-commit
  contract and checked workspace semantics.
- `metodobase_iniciar.bat` installs unhashed generic/API requirements and starts
  api_server.py; README_DISTRIBUCION describes a console/browser application and
  single-executable updates, conflicting with PySide onedir distribution.
- `setup_installer.iss:56-59` explicitly deletes legacy data directories under
  the application directory during uninstall. Preservation/migration, privilege,
  version and architecture behavior need repair and an installer test before use.

The new desktop document acknowledges these divergent recipes. They require the
next coordinated operation/QA wave rather than silently remaining release paths.

## Evidence integrity

`desktop-packaging-backend-review.before.json` and `.after.json` record all 19
source SHA256s, exact commit and clean worktree status. Every source hash remained
unchanged after tests/probes. The after report also hashes the preserved provenance
probe. The XML-artifacts summary records the five historical JUnit documents,
including prior true negatives and fixture errors without relabeling either.

Verdict: useful recipe preparation, **not accepted for an artifact while P1 remains**.
Parent coordinates the author's fix and independent rerun; no source edits or
release actions are authorized or performed by this review.
