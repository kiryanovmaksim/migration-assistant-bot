<#
.SYNOPSIS
  ������������ ������� git-�����������, ������� ������ � ��������� �� ����� ���/�����.
  ����� ������ ���� ������ ��� ������ ������� � ���������� ������ ������.

.PARAMETER Name
  ����� ��� ������/���������.

.PARAMETER Email
  ����� e?mail ������/���������.

.PARAMETER OldEmail
  (�������������) ������ �����. ���� ������� � ���������� ������ ������� � ���� ������.
  ���� �� ������� � ����� ���������� *���* �������.

.PARAMETER Force
  ���������� ������������� ����� �������������� �������.

.PARAMETER DryRun
  ������� ������: �������, ��� ����� �������, �� �� ������� �������.

.EXAMPLE
  .\reset_git_author.ps1 -Name "Ivan Petrov" -Email "ivan@example.com"

.EXAMPLE
  .\reset_git_author.ps1 -Name "Ivan Petrov" -Email "ivan@example.com" -OldEmail "old@mail.com"

.EXAMPLE
  .\reset_git_author.ps1 -Name "Ivan Petrov" -Email "ivan@example.com" -Force

.NOTES
  ��� *������������ �������* (rebase ����� ����). ����� � ������ ������ --force-with-lease.
#>

param(
  [Parameter(Mandatory = $true)] [string] $Name,
  [Parameter(Mandatory = $true)] [string] $Email,
  [string] $OldEmail,
  [switch] $Force,
  [switch] $DryRun
)

function Fail($msg) { Write-Error $msg; exit 1 }

# 1) ������������
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Fail "git �� ������ � PATH."
}

# ��������, ��� �� � �����������
$gitTop = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0) { Fail "������, ��� �� git?�����������." }
Set-Location $gitTop

# �������� ������� �������� ������
$dirty = (git status --porcelain)
if ($dirty) {
  Write-Warning "������� ������ �� ������. ���������/����������� ��������� ��� �������� stash."
  if (-not $Force) { Fail "�����������. ��������� � -Force, ���� �������." }
}

# 2) ���������� � �������������
Write-Host "�����������: $gitTop"
if ($OldEmail) {
  Write-Host "�������� ������� c ������ '$OldEmail' ��:"
} else {
  Write-Host "�������� �������/���������� �� ���� ������� ��:"
}
Write-Host "  Name : $Name"
Write-Host "  Email: $Email"
if ($DryRun) { Write-Host "`nDRY RUN: ������� ��������� � ������� ������� �� �����.`n" }

if (-not $Force) {
  $answer = Read-Host "��� ��������� ��� ������� (branches, tags). ����������? (yes/no)"
  if ($answer -notin @("y","Y","yes","YES")) { Fail "�������� �������������." }
}

# 3) �������� �����-��� �� ������ ������
$backupRef = "refs/backup/author-rewrite/$(Get-Date -f yyyyMMdd-HHmmss)"
if (-not $DryRun) {
  git update-ref $backupRef HEAD | Out-Null
  Write-Host "������ ��������� ref: $backupRef (��������� �� ������� HEAD)."
}

# 4) ������� ��������� ������������ user.name/user.email (����� ����� ������� ���� �������)
if (-not $DryRun) {
  git config user.name  "$Name"
  git config user.email "$Email"
  Write-Host "��������� git-������������ ��������� (user.name, user.email)."
} else {
  Write-Host "[DRY RUN] ��������� ���������� ��������� ������������."
}

# 5) ��������� ������������ git filter-repo (���� ��������). ����� fallback �� filter-branch.
function HasFilterRepo {
  & git filter-repo --help *>$null
  return ($LASTEXITCODE -eq 0)
}

if (HasFilterRepo) {
  Write-Host "���������: git filter-repo � ���������� ���."
  # �������� ������� ������
  # ��� filter-repo ������ mapping �������/����������.
  $tmpMap = New-TemporaryFile
  try {
    if ($OldEmail) {
      # ������ ��� ��������� ������ �����
      @"
author email <$OldEmail> ==> $Name <$Email>
committer email <$OldEmail> ==> $Name <$Email>
"@ | Set-Content -NoNewline -Encoding UTF8 $tmpMap
    } else {
      # ��� ���� � ���������� callback ����� arguments, �.�. �������� ����� ������� ����� env � filter-branch.
      # �� filter-repo ���� ����� "replace-text" ��� �������������:
      @"
author identity ==>* $Name <$Email>
committer identity ==>* $Name <$Email>
"@ | Set-Content -NoNewline -Encoding UTF8 $tmpMap
    }

    $commonArgs = @("--force", "--commit-callback", "pass")
    $mapArg = @("--mailmap", $tmpMap.FullName)

    if ($DryRun) {
      Write-Host "[DRY RUN] ������� ���������� ������������� ���������:"
      git filter-repo @mapArg --dry-run
    } else {
      git filter-repo @mapArg
    }
  }
  finally {
    if (Test-Path $tmpMap) { Remove-Item $tmpMap -Force }
  }
}
else {
  Write-Host "git filter-repo �� ������. ��������� �� git filter-branch (���������)."

  # ���������� env-filter bash-������ ��� filter-branch
  $envFilter = if ($OldEmail) {
@"
if [ "\$GIT_AUTHOR_EMAIL" = "$OldEmail" ]; then
  export GIT_AUTHOR_NAME="$Name"
  export GIT_AUTHOR_EMAIL="$Email"
fi
if [ "\$GIT_COMMITTER_EMAIL" = "$OldEmail" ]; then
  export GIT_COMMITTER_NAME="$Name"
  export GIT_COMMITTER_EMAIL="$Email"
fi
"@
  } else {
@"
export GIT_AUTHOR_NAME="$Name"
export GIT_AUTHOR_EMAIL="$Email"
export GIT_COMMITTER_NAME="$Name"
export GIT_COMMITTER_EMAIL="$Email"
"@
  }

  if ($DryRun) {
    Write-Host "[DRY RUN] ����� ���������:"
    Write-Host "git filter-branch --env-filter '<script>' --tag-name-filter cat -- --branches --tags"
    Write-Host "`n--- env-filter preview ---`n$envFilter`n--------------------------"
  } else {
    # ��������� filter-branch
    & git filter-branch --env-filter $envFilter --tag-name-filter cat -- --branches --tags
    if ($LASTEXITCODE -ne 0) { Fail "git filter-branch ���������� � �������." }
  }
}

Write-Host "`n������."
Write-Host "�����: ����� �������� �������� ������ � �����������:"
Write-Host "  git push --force-with-lease --all"
Write-Host "  git push --force-with-lease --tags"
Write-Host "���� ���-�� ����� �� ���, ����� ��������� � ������:"
Write-Host "  git reset --hard $backupRef"
