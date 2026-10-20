Independent account37 QA-28 final replay

Product 12b4b11322060255eb7ca894520ea0652fe33543 is reviewed as a delta from c91a18bbb7a21cc92616574280ec61959fd8caa5.
Only web/static/js/api.js changes product. The seven own canary files
from ffee085f,08de03f3 ande4598f7a remain exact Git bytes. Original RED receipts stay
unchanged: six actual HTTP failures and twelve typed VM failures, plus six
separate403/422 controls and eighteen independent timing/privacy/GIS cases.
The separate four blocked-body GET failures and two POST controls frome459
also remain preserved; all six now pass on the final candidate.

The selected tests now pass:42 own VM/minimal DOM, six real HTTP (both
factories, real MFA/cookie login followed by persisted SV invalidation), and
ten unchanged author DOM cases. This is48 own tests plus ten author cases,
not a whole-project count. Three of the18 timing cases use the explicit,
reversible headers401 companion frome4598f7a; the other15 original cases and
all actor/epoch assertions remain unchanged. This is not18 literal replays.
The further six headers401 canaries now retire all four own-account GET
authorities and both POSTs before a blocked error body can keep access live.
No automatic refresh/retry is introduced;
wrong-primary401 and confirmed403/422 stay correctable. Old401 cannot retire
a newer genuine actor or overwrite a later external epoch. Shared cookie lock
and captured immutable request bodies retain their earlier behavior. Private
server/Storage errors are opaque; only an epoch enters persistent Storage.

Both final gates have quiet source photos, Node and Python binaries,92
distributions and pip0/0. Own Python canary has0 Ruff diagnostics. Original
outputs remain private under the previously frozen restricted DACL; ZIP
members are read back byte-for-byte. Public projections pass both scanners.
No product edits were made by the independent reviewer. No PostgreSQL/native
browser/real Google acceptance/delivery/Main/fullscan/global closure is claimed.
