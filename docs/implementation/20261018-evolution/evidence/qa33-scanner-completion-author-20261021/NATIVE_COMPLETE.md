The two bounded native controls completed after the initial handoff. Source was
4ec70e0a1c9ba8bda99e1e7cd7cf0e5a4334e7df; all six source blobs are identical
to the 45-control source b3b1846a4e9c30d25b506112ce0ab6fbc7771586.

Each fixture contains the unchanged Main25d1 .gitleaks.toml and one synthetic
text file, in a new private local Git tree with no remote. The first input is
harmless text; the second is an inert randomly generated test value with the
api_key label. Neither value came from a provider, account or environment.
No registry data was copied: the actual loader's documented missing-data branch
disables classifications, so the one native finding remains blocking.

The conductor invokes the actual wrapper, real Git and pinned Gitleaks 8.30.1.
It asserts the production dir-call timeout is 600 seconds, then bounds that
specific synthetic native call to 10 seconds. The internal Gitleaks timeout
remains zero and the command/configuration/redact=100 flags are unchanged.
The conductor captures real version stdout/stderr and real scan stdout/stderr
plus the raw redacted report privately. The production evidence-boundary
creation and semantic WinAPI readback execute without a mock.

Both controls passed: clean input 303386 bytes, wrapper exit 0 and zero findings
in 1.593 seconds; synthetic input 303416 bytes, wrapper exit 1 and one unclassified
finding in 1.641 seconds. Both emitted the exact complete summary, empty stdout,
and stable fixture bytes. All source and WEB92/Node installed-file photographs
were quiet. No new pip claim is inferred from this native phase; the preceding
45-control phase separately ran pip check 0/0.

Closed archive SHA256:
f81ef2a6af9bc9d33de317d2e16205f3ca1d27f6262d9e8f90fa67c590f474f2,
72 members with complete readback. The adjacent public receipt is byte exact.
Fresh CIM audit found zero Gitleaks processes and the binary SHA256 remained
17157e2ee8b76fc8b1d8bee607a250e34b8a8023c8bc81822d4b5ee4d78fcb7c.

This phase establishes the strict parser's compatibility with the actual small
complete runs. It does not validate the project's full scan, release, image,
Linux/Actions, ignored files or Git history. Main25d1's old 43532 result remains
unaccepted. No SQL, Chrome, Redis, VM or parallel pytest was launched.
