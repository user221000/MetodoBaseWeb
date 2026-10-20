$taskPrivate='C:\Users\Consu\AppData\Local\Temp\metodobase-followup34-author-sec-peer-20261019'
$taskAcl=Get-Acl -LiteralPath $taskPrivate
$taskIdentity=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskAllowed=@($taskIdentity,'S-1-5-18')
if(-not $taskAcl.AreAccessRulesProtected -or @($taskAcl.Access).Count -ne 2){throw 'Private parent ACL changed'}
if([System.IO.File]::ReadAllText((Join-Path $taskPrivate 'acl-initial.private.txt')).Trim() -ne $taskAcl.Sddl){throw 'Private initial ACL differs'}
$taskChecked=0
$taskFixtures=0
foreach($taskItem in Get-ChildItem -LiteralPath $taskPrivate -Force -Recurse){
 if($taskItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint){throw 'Unexpected private reparse point'}
 $taskRelative=$taskItem.FullName.Substring($taskPrivate.Length+1)
 $taskItemAcl=Get-Acl -LiteralPath $taskItem.FullName
 $taskItemAllowed=@($taskAllowed)
 if($taskRelative -match '^(?:pytest-[^\\]+|restore-evidence)(?:\\|$)'){
  $taskItemAllowed+=@($taskItemAcl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value,'S-1-3-4','S-1-5-32-544')
  $taskFixtures+=1
 }
 foreach($taskRule in $taskItemAcl.Access){
  $taskSid=$taskRule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
  if($taskSid -notin $taskItemAllowed -or $taskRule.AccessControlType -ne 'Allow'){throw ('Unexpected descendant ACL: '+$taskRelative)}
 }
 $taskChecked+=1
}
$taskResult=@{protected=$true;parent_SDDL_unchanged=$true;parent_rule_count=2;descendants_checked=$taskChecked;raw_captures_current_user_and_SYSTEM_only=$true;synthetic_fixture_entries_with_owner_system_administrators_allowed=$taskFixtures;scope='pytest fixture trees and synthetic restore artifacts separately distinguished; no actual profile copied'}
[System.IO.File]::WriteAllText((Join-Path $taskPrivate 'acl-final.private.json'),($taskResult|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
$taskResult|ConvertTo-Json -Compress
