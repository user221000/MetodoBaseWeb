# Checkpoint125 evidence seal

Original bytes remain intact. Private archives were created as exclusive empty files, assigned protected DACLs for the current user and SYSTEM, and verified before payload writes. Public files passed the unmodified checkpoint119 scanner.

The full serial run remains rejected: 3047 cases, 3045 passed, one setup error, one known skip. Later focal author replays do not establish the cause of that historical error or turn it into an accepted run. Repeated integration phases are not counted as additional unique criteria.

No tests, browser, database or provider were run while sealing. The closed coverage JSON was checked by the actual coverage gate only. RAW proof files use * -text; this prefix has not been staged or committed by the sealing agent.
