param(
    [Parameter(Mandatory = $false)]
    [string]$OutputsFile = ".\infra\cdk-outputs.json",
    [Parameter(Mandatory = $false)]
    [string]$AudioPath = ".\audio_testing\test1.mp3",
    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"

function Resolve-RepoPath {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $repoRoot $Path.TrimStart(".\")
}

function Invoke-JsonRequest {
    param(
        [string]$Method,
        [string]$Uri,
        [object]$Body = $null,
        [int]$TimeoutSec = 180
    )
    $params = @{
        Method = $Method
        Uri = $Uri
        UseBasicParsing = $true
        TimeoutSec = $TimeoutSec
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json; charset=utf-8"
        $params.Body = $Body | ConvertTo-Json -Depth 10 -Compress
    }
    $response = Invoke-WebRequest @params
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
        throw "$Method $Uri devolvio HTTP $($response.StatusCode)."
    }
    if ([string]::IsNullOrWhiteSpace($response.Content)) { return $null }
    return $response.Content | ConvertFrom-Json
}

$outputsPath = Resolve-RepoPath $OutputsFile
$audioFullPath = Resolve-RepoPath $AudioPath
if (-not (Test-Path $outputsPath -PathType Leaf)) { throw "No existe $outputsPath." }
if (-not (Test-Path $audioFullPath -PathType Leaf)) { throw "No existe $audioFullPath." }
$outputs = Get-Content $outputsPath -Raw | ConvertFrom-Json
$stackOutputs = $outputs.JaimesMvpStack
$functionUrl = [string]$stackOutputs.FunctionUrl
if ([string]::IsNullOrWhiteSpace($functionUrl) -or -not $functionUrl.StartsWith("https://")) {
    throw "FunctionUrl no es una URL HTTPS valida."
}
$baseUrl = $functionUrl.TrimEnd("/")

$healthResponse = Invoke-WebRequest -Method Get -Uri "$baseUrl/health" -UseBasicParsing -TimeoutSec 60
$health = $healthResponse.Content | ConvertFrom-Json
if ($healthResponse.StatusCode -ne 200 -or $health.status -ne "ok") {
    throw "GET /health no devolvio 200 status=ok."
}
$root = Invoke-WebRequest -Method Get -Uri "$baseUrl/" -UseBasicParsing -TimeoutSec 60
if ($root.StatusCode -ne 200 -or -not $root.Headers["Content-Type"].StartsWith("text/html")) {
    throw "GET / no devolvio la PWA HTML con HTTP 200."
}

$educadoras = @(Invoke-JsonRequest -Method Get -Uri "$baseUrl/educadoras" -TimeoutSec 60)
if ($educadoras.Count -eq 0) { throw "GET /educadoras no devolvio datos." }
$educadora = $null
$ninos = @()
foreach ($candidate in $educadoras) {
    $candidateNinos = @(Invoke-JsonRequest -Method Get -Uri "$baseUrl/educadoras/$([uri]::EscapeDataString($candidate.id_educadora))/ninos" -TimeoutSec 60)
    if ($candidateNinos.Count -gt 0) {
        $educadora = $candidate
        $ninos = $candidateNinos
        break
    }
}
if ($null -eq $educadora) { throw "No se encontro una educadora con ninos relacionados." }
$nino = $ninos[0]
$today = [DateTime]::UtcNow.Date

Add-Type -AssemblyName System.Net.Http
$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromSeconds(180)
$multipart = New-Object System.Net.Http.MultipartFormDataContent
$fileContent = $null
try {
    $multipart.Add((New-Object System.Net.Http.StringContent([string]$educadora.id_educadora)), "id_educadora")
    $multipart.Add((New-Object System.Net.Http.StringContent("audio")), "formato")
    $multipart.Add((New-Object System.Net.Http.StringContent($today.ToString("yyyy-MM-dd"))), "fecha_observacion")
    $fileContent = New-Object System.Net.Http.ByteArrayContent(,[System.IO.File]::ReadAllBytes($audioFullPath))
    $fileContent.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue("audio/mpeg")
    $multipart.Add($fileContent, "archivo", [System.IO.Path]::GetFileName($audioFullPath))
    $uploadUrl = "$baseUrl/ninos/$([uri]::EscapeDataString($nino.id_nino))/observaciones"
    $uploadResponse = $client.PostAsync($uploadUrl, $multipart).GetAwaiter().GetResult()
    $uploadBody = $uploadResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    if (-not $uploadResponse.IsSuccessStatusCode) {
        throw "POST observacion de audio devolvio HTTP $([int]$uploadResponse.StatusCode): $uploadBody"
    }
    $observation = $uploadBody | ConvertFrom-Json
}
finally {
    if ($null -ne $fileContent) { $fileContent.Dispose() }
    $multipart.Dispose()
    $client.Dispose()
}

$transcript = [string]$observation.nota_breve
if ([string]::IsNullOrWhiteSpace($transcript)) {
    throw "Nova Sonic no produjo un transcript en nota_breve."
}
if ($null -eq $observation.clasificacion) {
    throw "Claude no produjo una clasificacion para el transcript."
}
$classificationBody = @{
    accion = "confirmar"
    nivel_estimado = $observation.clasificacion.nivel_estimado
    dominios = @($observation.clasificacion.dominios)
    manifestaciones = @($observation.clasificacion.manifestaciones)
}
$null = Invoke-JsonRequest -Method Patch -Uri "$baseUrl/observaciones/$([uri]::EscapeDataString($observation.id_observacion))/clasificacion" -Body $classificationBody

$journalBody = @{
    id_educadora = [string]$educadora.id_educadora
    fecha_inicio = $today.AddDays(-13).ToString("yyyy-MM-dd")
    fecha_fin = $today.ToString("yyyy-MM-dd")
}
$journal = Invoke-JsonRequest -Method Post -Uri "$baseUrl/ninos/$([uri]::EscapeDataString($nino.id_nino))/bitacoras" -Body $journalBody -TimeoutSec 180
$journalText = [string]$journal.texto_generado
if ([string]::IsNullOrWhiteSpace($journalText) -or $journalText.Length -lt 100) {
    throw "Claude devolvio una bitacora vacia o incompleta ($($journalText.Length) caracteres)."
}

$stacksJson = & $aws cloudformation list-stacks --region $Region --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE --query "StackSummaries[].{Name:StackName,Status:StackStatus}" --output json
if ($LASTEXITCODE -ne 0) { throw "No se pudieron consultar los stacks existentes." }
$stacks = @($stacksJson | ConvertFrom-Json)
$mvpStack = $stacks | Where-Object Name -eq "JaimesMvpStack"
if ($null -eq $mvpStack -or $mvpStack.Status -notin @("CREATE_COMPLETE", "UPDATE_COMPLETE")) {
    throw "JaimesMvpStack no esta en CREATE_COMPLETE/UPDATE_COMPLETE."
}
$previousStacks = @($stacks | Where-Object Name -notin @("JaimesMvpStack", "CDKToolkit"))

Write-Host "Verificacion cloud correcta."
Write-Host "Function URL: $functionUrl"
Write-Host "Health/PWA/API: HTTP 200; origen unico confirmado."
Write-Host "Nova IAM: transcript no vacio ($($transcript.Length) caracteres)."
Write-Host "Claude IAM: clasificacion confirmada y bitacora no vacia ($($journalText.Length) caracteres)."
Write-Host "Nino de smoke: $($nino.id_nino); observacion: $($observation.id_observacion); bitacora: $($journal.id_bitacora)."
if ($previousStacks.Count -eq 0) {
    Write-Host "Stacks anteriores: ninguno presente; no se destruyo ningun stack."
} else {
    Write-Host "Stacks anteriores intactos: $((($previousStacks | ForEach-Object { \"$($_.Name)=$($_.Status)\" }) -join ', '))."
}
