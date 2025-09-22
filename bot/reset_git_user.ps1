# reset_git_user.ps1
Write-Host "=== Git User Switch & Push Helper ===" -ForegroundColor Cyan

# 1. Спросить данные
$GitUser  = Read-Host "Введите новый Git user.name"
$GitEmail = Read-Host "Введите новый Git user.email"
$RepoUrl  = Read-Host "Введите URL репозитория (например https://github.com/kiryanovmaksim/migration-assistant-bot.git)"
$UseSSH   = Read-Host "Использовать SSH вместо HTTPS? (y/n)"
$Rename   = Read-Host "Переименовать текущую ветку в main? (y/n)"
$Force    = Read-Host "Сделать force push? (y/n)"
$ClearCreds = Read-Host "Очистить старые креды GitHub? (y/n)"

function Invoke-Git { param([string[]]$Args) git @Args }

# 2. Настроить user
git config user.name  $GitUser
git config user.email $GitEmail
Write-Host "✅ Установлен Git user: $GitUser <$GitEmail>"

# 3. Очистить креды
if ($ClearCreds -eq "y") {
    Write-Host "🧹 Чистим кэшированные учётки GitHub..."
    @"
protocol=https
host=github.com
"@ | git credential-manager-core erase
    cmdkey /delete:git:https://github.com 2>$null
    cmdkey /delete:github.com 2>$null
}

# 4. Remote
if ($UseSSH -eq "y") {
    if ($RepoUrl -match "github\.com[:/](.+?)/(.+?)(\.git)?$") {
        $owner = $Matches[1]; $repo = $Matches[2]
        $RepoUrl = "git@github.com:$owner/$repo.git"
    }
}
git remote remove origin 2>$null
git remote add origin $RepoUrl
Write-Host "🔗 Remote установлен: $RepoUrl"

# 5. Ветка
if ($Rename -eq "y") {
    git branch -M main
    $Branch = "main"
} else {
    $Branch = (git branch --show-current)
}
Write-Host "🌿 Текущая ветка: $Branch"

# 6. Push
if ($Force -eq "y") {
    Write-Host "🚀 Делаем force push в origin/$Branch ..."
    git push --force origin $Branch
} else {
    Write-Host "🚀 Делаем обычный push в origin/$Branch ..."
    git push origin $Branch
}

Write-Host "Готово ✅" -ForegroundColor Green
