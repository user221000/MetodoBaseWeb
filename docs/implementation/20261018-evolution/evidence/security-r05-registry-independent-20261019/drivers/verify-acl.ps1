$taskPrivate = 'C:\Users\Consu\AppData\Local\Temp\metodobase-sec-r05-classifier-peer-private-20261019'
$taskAcl = Get-Acl -LiteralPath $taskPrivate
$taskIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskAllowed = @($taskIdentity, 'S-1-5-18')
$taskRules = @($taskAcl.Access)
if (-not $taskAcl.AreAccessRulesProtected -or $taskRules.Count -ne 2) { throw 'Private parent ACL shape changed' }
foreach ($taskRule in $taskRules) {
    $taskSid = $taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    if ($taskSid -notin $taskAllowed -or $taskRule.AccessControlType -ne 'Allow' -or $taskRule.FileSystemRights -ne 'FullControl') { throw 'Private parent ACL authority changed' }
}
$taskChecked = 0
$taskFixtureChecked = 0
foreach ($taskItem in Get-ChildItem -LiteralPath $taskPrivate -Force -Recurse) {
    if ($taskItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'Unexpected private reparse point' }
    $taskRelative = $taskItem.FullName.Substring($taskPrivate.Length + 1)
    $taskItemAcl = Get-Acl -LiteralPath $taskItem.FullName
    $taskItemAllowed = $taskAllowed
    if ($taskRelative -match '^pytest-(?:final|17)(?:\\|$)') {
        $taskOwner = $taskItemAcl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
        $taskItemAllowed = @($taskAllowed) + @($taskOwner, 'S-1-3-4', 'S-1-5-32-544')
        $taskFixtureChecked += 1
    }
    foreach ($taskRule in $taskItemAcl.Access) {
        $taskSid = $taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($taskSid -notin $taskItemAllowed -or $taskRule.AccessControlType -ne 'Allow') {
            @{ relative_path = $taskRelative; kind = $taskRule.AccessControlType.ToString(); allowed_principal = ($taskSid -in $taskItemAllowed); inherited = $taskRule.IsInherited } | ConvertTo-Json -Compress
            throw 'Private descendant ACL authority changed'
        }
    }
    $taskChecked += 1
}
$taskAclData = @{ protected = $true; parent_rule_count = 2; raw_capture_files_current_user_and_system_only = $true; descendants_checked = $taskChecked; synthetic_pytest_fixture_entries_with_owner_system_administrators_allowed = $taskFixtureChecked; sddl = $taskAcl.Sddl }
[System.IO.File]::WriteAllText((Join-Path $taskPrivate 'acl-final.private.json'), ($taskAclData | ConvertTo-Json), [System.Text.UTF8Encoding]::new($false))
@{ protected = $true; parent_rule_count = 2; descendants_checked = $taskChecked; raw_capture_files_current_user_and_system_only = $true; synthetic_pytest_fixture_entries_with_owner_system_administrators_allowed = $taskFixtureChecked } | ConvertTo-Json -Compress
