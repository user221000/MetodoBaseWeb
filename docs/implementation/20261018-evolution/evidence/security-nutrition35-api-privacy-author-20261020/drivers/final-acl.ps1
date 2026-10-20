$taskRoot = 'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-nutrition35-api-peer-private-20261019'
$taskSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskBasic = @($taskSid, 'S-1-5-18')
$taskFixture = @($taskSid, 'S-1-5-18', 'S-1-3-4', 'S-1-5-32-544')
$taskParent = Get-Acl -LiteralPath $taskRoot
if (-not $taskParent.AreAccessRulesProtected) { throw 'Private parent DACL is not protected' }
foreach ($taskRule in $taskParent.Access) {
    $taskRuleSid = $taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    if ($taskRule.AccessControlType -ne 'Allow' -or $taskRuleSid -notin $taskBasic) { throw 'Unexpected private parent access rule' }
}
$taskEntries = @(Get-ChildItem -LiteralPath $taskRoot -Recurse -Force)
$taskCaptureCount = 0
$taskSyntheticCount = 0
foreach ($taskEntry in $taskEntries) {
    $taskEntryAcl = Get-Acl -LiteralPath $taskEntry.FullName
    $taskIsFixture = $taskEntry.FullName.Contains('\pytest\') -or $taskEntry.Name -eq 'pytest'
    $taskAllowed = if ($taskIsFixture) { $taskFixture } else { $taskBasic }
    foreach ($taskRule in $taskEntryAcl.Access) {
        $taskRuleSid = $taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($taskRule.AccessControlType -ne 'Allow' -or $taskRuleSid -notin $taskAllowed) { throw 'Unexpected retained private entry access rule' }
    }
    if ($taskIsFixture) { $taskSyntheticCount++ } else { $taskCaptureCount++ }
}
$taskReceipt = [ordered]@{
    parent_DACL_protected = $true
    parent_rule_count = @($taskParent.Access).Count
    parent_SDDL = $taskParent.Sddl
    checked_entries = $taskEntries.Count
    raw_capture_and_code_entries_current_user_SYSTEM_only = $taskCaptureCount
    synthetic_pytest_entries_allow_OWNER_RIGHTS_Administrators = $taskSyntheticCount
    unexpected_allow_or_deny_rules = 0
    initial_SDDL_snapshot_retained = $false
    initial_private_parent_DACL_set_before_payload_by_tool_call = $true
    execution_policy_changed = $false
}
$taskJson = ConvertTo-Json -InputObject $taskReceipt -Depth 6
[System.IO.File]::WriteAllText((Join-Path $taskRoot 'ACL-final.private.json'), $taskJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ('Private ACL checked: ' + $taskEntries.Count + ' entries')
