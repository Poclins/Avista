param(
    [string]$ExpectedAccount = "655275680575",
    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$infraDir = Join-Path $repoRoot "infra"
$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$python = Join-Path $infraDir ".venv\Scripts\python.exe"

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $output = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "El comando '$Command $($Arguments -join ' ')' fallo con codigo $LASTEXITCODE."
    }
    return $output
}

if (-not (Test-Path $aws -PathType Leaf)) {
    throw "No se encontro AWS CLI en $aws."
}
if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
    throw "AWS CDK no esta disponible en PATH."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker no esta disponible en PATH."
}
if (-not (Test-Path $python -PathType Leaf)) {
    throw "Falta infra/.venv. Ejecute python -m venv infra/.venv y pip install -r infra/requirements.txt."
}

$identity = (Invoke-NativeChecked $aws @("sts", "get-caller-identity", "--region", $Region, "--output", "json") | Out-String) | ConvertFrom-Json
if ($identity.Account -ne $ExpectedAccount) {
    throw "Cuenta AWS incorrecta: $($identity.Account). Se esperaba $ExpectedAccount."
}
$configuredRegion = (Invoke-NativeChecked $aws @("configure", "get", "region") | Out-String).Trim()
if ($configuredRegion -ne $Region) {
    throw "Region AWS incorrecta: $configuredRegion. Se esperaba $Region."
}
$bootstrap = (Invoke-NativeChecked $aws @("cloudformation", "describe-stacks", "--stack-name", "CDKToolkit", "--region", $Region, "--output", "json") | Out-String) | ConvertFrom-Json
$bootstrapStack = $bootstrap.Stacks[0]
$bootstrapVersion = ($bootstrapStack.Outputs | Where-Object OutputKey -eq "BootstrapVersion").OutputValue
if ($bootstrapStack.StackStatus -notin @("CREATE_COMPLETE", "UPDATE_COMPLETE") -or [int]$bootstrapVersion -lt 6) {
    throw "CDKToolkit no esta listo: estado $($bootstrapStack.StackStatus), version $bootstrapVersion."
}
Invoke-NativeChecked "cdk" @("--version") | Out-Null
Invoke-NativeChecked "docker" @("info", "--format", "{{.ServerVersion}}") | Out-Null

$existingStacks = Invoke-NativeChecked $aws @(
    "cloudformation", "list-stacks", "--region", $Region,
    "--stack-status-filter", "CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE",
    "--query", "StackSummaries[].{Name:StackName,Status:StackStatus}", "--output", "table"
)
Write-Host "Stacks existentes (no se modificaran salvo JaimesMvpStack):"
$existingStacks | Write-Host

$env:CDK_DEFAULT_ACCOUNT = $ExpectedAccount
$env:CDK_DEFAULT_REGION = $Region
Push-Location $infraDir
try {
    Invoke-NativeChecked "cdk" @("synth", "JaimesMvpStack") | Out-Null
    Invoke-NativeChecked "cdk" @(
        "deploy", "JaimesMvpStack", "--require-approval", "never",
        "--outputs-file", "cdk-outputs.json"
    ) | Write-Host
}
finally {
    Pop-Location
}

Write-Host "Despliegue exclusivo de JaimesMvpStack completado."
