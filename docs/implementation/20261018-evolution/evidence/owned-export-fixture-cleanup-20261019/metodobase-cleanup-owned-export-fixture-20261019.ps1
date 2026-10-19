$ErrorActionPreference = 'Stop'
$cleanupOutput = 'C:\Users\Consu\AppData\Local\Temp\metodobase-owned-export-fixture-cleanup-20261019.json'
if (Test-Path -LiteralPath $cleanupOutput) { throw 'Receipt exists' }
$ownershipPath = 'F:\MetodoBaseWeb-execution-20261018\docs\implementation\20261018-evolution\evidence\ux\diary-ui-consumer-fix-runtime-freeze-before.json'
$ownership = Get-Content -Raw -Encoding UTF8 -LiteralPath $ownershipPath | ConvertFrom-Json
if ($ownership.launcher_pid -ne 288 -or $ownership.listener_pid -ne 30168 -or $ownership.port -ne 8777) { throw 'Ownership receipt mismatch' }
$listener = Get-CimInstance Win32_Process -Filter 'ProcessId=30168'
$launcher = Get-CimInstance Win32_Process -Filter 'ProcessId=288'
if (-not $listener -or -not $launcher) { throw 'Expected owned pair absent' }
$listenerEpoch = ([DateTimeOffset]$listener.CreationDate).ToUnixTimeMilliseconds()
$launcherEpoch = ([DateTimeOffset]$launcher.CreationDate).ToUnixTimeMilliseconds()
if ($listenerEpoch -ne 1792395134180 -or $launcherEpoch -ne 1792395134151) { throw 'Process identity changed' }
if ($listener.ParentProcessId -ne 288 -or $launcher.ParentProcessId -ne 30380) { throw 'Parent identity changed' }
if (Get-CimInstance Win32_Process -Filter 'ProcessId=30380') { throw 'Prior orchestration parent is still present; inspect first' }
if ($listener.ExecutablePath -ne 'C:\Users\Consu\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\python.exe' -or $launcher.ExecutablePath -ne 'C:\Users\Consu\AppData\Local\Temp\metodobase-candidate-web-20261018\Scripts\python.exe') { throw 'Executable identity changed' }
if ($listener.CommandLine -notmatch ' -X utf8 tests/e2e/personal_export_context_server\.py$' -or $launcher.CommandLine -notmatch ' -X utf8 tests/e2e/personal_export_context_server\.py$') { throw 'Fixture identity changed' }
$ownedPort = @(Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort 8777 -ErrorAction SilentlyContinue)
if ($ownedPort.Count -ne 1 -or $ownedPort[0].OwningProcess -ne 30168) { throw 'Listener identity changed' }
$foreign = Get-CimInstance Win32_Process -Filter 'ProcessId=15680'
if (-not $foreign -or ([DateTimeOffset]$foreign.CreationDate).ToUnixTimeMilliseconds() -ne 1792393095897) { throw 'Unattributed fixture baseline changed' }
Stop-Process -Id 30168 -ErrorAction Stop
Stop-Process -Id 288 -ErrorAction Stop
if (Get-CimInstance Win32_Process -Filter 'ProcessId=30168 OR ProcessId=288') { throw 'Owned pair still running' }
if (Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort 8777 -ErrorAction SilentlyContinue) { throw 'Owned port still listening' }
$foreignAfter = Get-CimInstance Win32_Process -Filter 'ProcessId=15680'
if (-not $foreignAfter -or ([DateTimeOffset]$foreignAfter.CreationDate).ToUnixTimeMilliseconds() -ne 1792393095897 -or $foreignAfter.CommandLine -ne $foreign.CommandLine) { throw 'Unattributed fixture changed' }
$receipt = [ordered]@{
  ownership_evidence = $ownershipPath
  ownership_sha256 = (Get-FileHash -LiteralPath $ownershipPath -Algorithm SHA256).Hash.ToLowerInvariant()
  stopped_exact_pids = @(30168,288)
  stopped_creation_epoch_ms = @($listenerEpoch,$launcherEpoch)
  port = 8777
  port_absent_after = $true
  foreign_port8776_pid15680_unchanged = $true
  no_files_deleted = $true
  scope = 'Stop two orphaned synthetic export-fixture processes after exact historical receipt, birth time, executable, command and port checks. No other processes or data changed.'
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $cleanupOutput
$receipt | ConvertTo-Json -Compress -Depth 4
