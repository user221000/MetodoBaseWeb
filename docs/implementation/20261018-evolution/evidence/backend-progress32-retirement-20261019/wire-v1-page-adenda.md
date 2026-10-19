# Public page privacy addendum

Wire v1 remains byte-exact. Root authorized the UI shell at
`/retirar-consentimientos` and its slash path. These two exact paths receive
the same fixed first-party CSP, no-store and no-referrer for every status and
method. Adjacent paths and existing GIS/login-page policy retain their prior
behavior. This adds no API, identity, capability or session operation. The UI
page is implemented/reviewed separately; a404 in this backend-only worktree
does not claim a mounted page.
