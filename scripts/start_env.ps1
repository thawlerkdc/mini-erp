param(
    [ValidateSet("development", "homolog", "production")]
    [string]$Environment = "development"
)

$ErrorActionPreference = "Stop"

$env:APP_ENV = $Environment
if ($Environment -eq "development") {
    $env:FLASK_ENV = "development"
} else {
    $env:FLASK_ENV = "production"
}

Write-Host "Iniciando Mini ERP no ambiente: $Environment" -ForegroundColor Green
python app.py
