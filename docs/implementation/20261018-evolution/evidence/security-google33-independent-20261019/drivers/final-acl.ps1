$taskPrivate = 'C:\Users\Consu\AppData\Local\Temp\metodobase-sec-google33-peer-private-20261019'
$taskAcl = Get-Acl -LiteralPath $taskPrivate
$taskIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskAllowed = @($taskIdentity, 'S-1-5-18')
$taskRules = @($taskAcl.Access)
if (-not $taskAcl.AreAccessRulesProtected -or $taskRules.Count -ne 2) { throw 'Private parent ACL shape changed' }
foreach ($taskRule in $taskRules) {
    $taskSid = $taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    if ($taskSid -notin $taskAllowed -or $taskRule.AccessControlType -ne 'Allow' -or $taskRule.FileSystemRights -ne 'FullControl') { throw 'Private parent ACL authority changed' }
}
$taskInitial = [System.IO.File]::ReadAllText((Join-Path $taskPrivate 'acl-initial.private.txt')).Trim()
if ($taskInitial -ne $taskAcl.Sddl) { throw 'Initial parent ACL differs' }
$taskChecked = 0
$taskFixtureChecked = 0
foreach ($taskItem in Get-ChildItem -LiteralPath $taskPrivate -Force -Recurse) {
    if ($taskItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'Unexpected private reparse point' }
    $taskRelative = $taskItem.FullName.Substring($taskPrivate.Length + 1)
    $taskItemAcl = Get-Acl -LiteralPath $taskItem.FullName
    $taskItemAllowed = $taskAllowed
    if ($taskRelative -match '^pytest-(?:sqlite|own-sqlite|pg-functional|pg-migration-restore|pg-final-races)(?:\\|$)') {
        $taskOwner = $taskItemAcl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
        $taskItemAllowed = @($taskAllowed) + @($taskOwner, 'S-1-3-4', 'S-1-5-32-544')
        $taskFixtureChecked += 1
    }
    foreach ($taskRule in $taskItemAcl.Access) {
        $taskSid = $taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($taskSid -notin $taskItemAllowed -or $taskRule.AccessControlType -ne 'Allow') { throw ('Private descendant ACL authority changed: ' + $taskRelative) }
    }
    $taskChecked += 1
}
$taskResult = @{ protected = $true; parent_rule_count = 2; parent_SDDL_unchanged = $true; raw_capture_files_current_user_and_system_only = $true; descendants_checked = $taskChecked; synthetic_pytest_fixture_entries_with_owner_system_administrators_allowed = $taskFixtureChecked }
[System.IO.File]::WriteAllText((Join-Path $taskPrivate 'acl-final.private.json'), ($taskResult | ConvertTo-Json), [System.Text.UTF8Encoding]::new($false))
$taskResult | ConvertTo-Json -Compress
