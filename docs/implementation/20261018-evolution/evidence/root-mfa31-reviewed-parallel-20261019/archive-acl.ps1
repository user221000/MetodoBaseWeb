param([ValidateSet('create','verify','final')][string]$Mode,[string]$PrivateRoot)
$ErrorActionPreference = 'Stop'
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$names = @('parallel-originals.zip')
function Assert-PrivateAcl([string]$Path,[bool]$Directory) {
    $item = Get-Item -LiteralPath $Path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse point rejected' }
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) { throw 'Inheritance remains enabled' }
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $sid.Value) { throw 'Owner mismatch' }
    $rules = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
    if ($rules.Count -ne 2) { throw 'Unexpected ACE count' }
    $ids = @()
    foreach ($rule in $rules) {
        if ($rule.IsInherited -or $rule.AccessControlType -ne 'Allow' -or $rule.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl) { throw 'Unexpected ACE' }
        $ids += $rule.IdentityReference.Value
    }
    if ((@($ids | Sort-Object) -join '|') -ne (@($sid.Value,$system.Value | Sort-Object) -join '|')) { throw 'Unexpected ACL identity' }
    if (-not $Directory -and $Mode -ne 'final' -and $item.Length -ne 0) { throw 'ZIP payload already written' }
}
if ($Mode -eq 'create') {
    if (Test-Path -LiteralPath $PrivateRoot) { throw 'Private directory already exists' }
    [IO.Directory]::CreateDirectory($PrivateRoot) | Out-Null
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner($sid)
    foreach ($id in @($sid,$system)) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($id,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $PrivateRoot -AclObject $acl
    Assert-PrivateAcl $PrivateRoot $true
    foreach ($name in $names) {
        $path = Join-Path $PrivateRoot $name
        $empty = [IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        $empty.Dispose()
        $fileAcl = [Security.AccessControl.FileSecurity]::new()
        $fileAcl.SetAccessRuleProtection($true,$false)
        $fileAcl.SetOwner($sid)
        foreach ($id in @($sid,$system)) { $fileAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($id,'FullControl','Allow')) }
        Set-Acl -LiteralPath $path -AclObject $fileAcl
        Assert-PrivateAcl $path $false
    }
}
Assert-PrivateAcl $PrivateRoot $true
foreach ($name in $names) { Assert-PrivateAcl (Join-Path $PrivateRoot $name) $false }
@{schema=1;mode=$Mode;verified_before_payload=($Mode -ne 'final');directory_inheritance_off=$true;file_inheritance_off=$true;owner_current_user=$true;allow_only=@('CURRENT_USER','SYSTEM');explicit_aces=2;files=$names;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 4 -Compress
