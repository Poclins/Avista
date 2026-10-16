param(
    [Parameter(Mandatory = $false)]
    [string]$Image = "jaimes-mvp:local",
    [Parameter(Mandatory = $false)]
    [int]$Port = 9000
)

$ErrorActionPreference = "Stop"
$containerName = "jaimes-mvp-smoke-$PID"
$invokeUrl = "http://localhost:$Port/2015-03-31/functions/function/invocations"

function Invoke-LambdaPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $event = @{
        version = "2.0"
        routeKey = '$default'
        rawPath = $Path
        rawQueryString = ""
        headers = @{
            host = "localhost"
            "x-forwarded-proto" = "http"
        }
        requestContext = @{
            accountId = "anonymous"
            apiId = "local"
            domainName = "localhost"
            domainPrefix = "localhost"
            http = @{
                method = "GET"
                path = $Path
                protocol = "HTTP/1.1"
                sourceIp = "127.0.0.1"
                userAgent = "jaimes-smoke"
            }
            requestId = [guid]::NewGuid().ToString()
            routeKey = '$default'
            stage = '$default'
            time = [DateTime]::UtcNow.ToString("dd/MMM/yyyy:HH:mm:ss +0000")
            timeEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        }
        isBase64Encoded = $false
    } | ConvertTo-Json -Depth 8 -Compress

    return Invoke-RestMethod -Method Post -Uri $invokeUrl -ContentType "application/json" -Body $event
}

try {
    docker run --rm -d --name $containerName -p "${Port}:8080" $Image | Out-Null

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $health = Invoke-LambdaPath -Path "/health"
            $ready = $true
            break
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        throw "La imagen Lambda no estuvo lista dentro de 30 segundos."
    }
    if ($health.statusCode -ne 200) {
        throw "GET /health devolvió estado $($health.statusCode)."
    }
    $healthBody = $health.body | ConvertFrom-Json
    if ($healthBody.status -ne "ok") {
        throw "GET /health no devolvió status=ok."
    }

    $root = Invoke-LambdaPath -Path "/"
    if ($root.statusCode -ne 200) {
        throw "GET / devolvió estado $($root.statusCode)."
    }
    $contentType = [string]$root.headers."content-type"
    if (-not $contentType.StartsWith("text/html")) {
        throw "GET / no devolvió HTML (Content-Type: $contentType)."
    }
    if ([string]::IsNullOrWhiteSpace([string]$root.body)) {
        throw "GET / devolvió un cuerpo vacío."
    }

    Write-Host "Smoke Lambda correcto: /health y / respondieron 200."
}
finally {
    docker rm -f $containerName 2>$null | Out-Null
}
