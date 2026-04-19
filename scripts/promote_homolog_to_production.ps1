param(
    [string]$HomologBranch = "homolog",
    [string]$ProductionBranch = "main",
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([string]$Args)
    Write-Host "> git $Args" -ForegroundColor Cyan
    cmd /c "git $Args"
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar: git $Args"
    }
}

Write-Host "=== Promocao de Homologacao para Producao ===" -ForegroundColor Yellow

$status = git status --porcelain
if ($status) {
    throw "Workspace com alteracoes locais. Commit/stash antes de promover."
}

$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()

Invoke-Git "fetch origin"

if (-not $SkipPull) {
    Invoke-Git "checkout $HomologBranch"
    Invoke-Git "pull origin $HomologBranch"

    Invoke-Git "checkout $ProductionBranch"
    Invoke-Git "pull origin $ProductionBranch"
} else {
    Invoke-Git "checkout $ProductionBranch"
}

$mergeMessage = "Promocao homolog -> producao " + (Get-Date -Format "yyyy-MM-dd HH:mm")

try {
    Invoke-Git "merge --no-ff $HomologBranch -m \"$mergeMessage\""
} catch {
    Write-Host "Conflito detectado no merge. Resolva os conflitos e finalize manualmente." -ForegroundColor Red
    throw
}

Invoke-Git "push origin $ProductionBranch"

Write-Host "Promocao concluida com sucesso." -ForegroundColor Green

if ($currentBranch -ne $ProductionBranch) {
    Invoke-Git "checkout $currentBranch"
}
