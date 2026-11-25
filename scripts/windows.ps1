[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "clean-docker", "clean-builder", "delete-volumes")]
    [string]$Action = "start",
    [switch]$NoBrowser,
    [switch]$ConfirmDelete
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$exitCode = 0

function Invoke-Docker {
    param([string[]]$DockerArguments)
    & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed (exit code $LASTEXITCODE): docker $($DockerArguments -join ' ')"
    }
}

function New-LocalSecret {
    param([int]$ByteCount)
    $bytes = New-Object byte[] $ByteCount
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Initialize-Environment {
    $destination = Join-Path $projectRoot ".env"
    if (Test-Path -LiteralPath $destination) {
        Write-Host "Existing .env preserved."
        return
    }
    $template = [System.IO.File]::ReadAllText((Join-Path $projectRoot ".env.example"))
    $template = $template.Replace(
        "replace-with-a-random-secret-of-at-least-32-characters", (New-LocalSecret 48)
    ).Replace("ChangeThisDemoPassword123!", (New-LocalSecret 24))
    $encoding = New-Object System.Text.UTF8Encoding $false
    $stream = [System.IO.File]::Open(
        $destination, [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write, [System.IO.FileShare]::None
    )
    try {
        $bytes = $encoding.GetBytes($template)
        $stream.Write($bytes, 0, $bytes.Length)
    }
    finally {
        $stream.Dispose()
    }
    Write-Host "Created .env with local secrets. The demo password is DEMO_PASSWORD in that file."
}

Push-Location -LiteralPath $projectRoot
try {
    if ($Action -eq "delete-volumes" -and -not $ConfirmDelete) {
        throw ("This stops the project and permanently deletes its database, Redis data, and " +
            "uploaded images. To proceed, run: .\delete-volumes.cmd -ConfirmDelete")
    }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker was not found. Install Docker Desktop, then reopen your terminal."
    }
    try {
        $engineType = Invoke-Docker -DockerArguments @("info", "--format", "{{.OSType}}")
        if ([string]::IsNullOrWhiteSpace(($engineType -join '').Trim())) {
            throw "No Docker engine response."
        }
    }
    catch {
        throw "Docker is unavailable. Start Docker Desktop and wait until its engine is running."
    }
    if (($engineType -join '').Trim() -ne "linux") {
        throw "This project needs Linux containers. Switch Docker Desktop to Linux containers."
    }
    if ($Action -in @("start", "stop", "delete-volumes")) {
        Invoke-Docker -DockerArguments @("compose", "version")
    }

    if ($Action -eq "stop") {
        Invoke-Docker -DockerArguments @("compose", "down")
        Write-Host "diploma-project stopped. Database and uploaded images are preserved."
    }
    elseif ($Action -eq "clean-docker") {
        Write-Host "Remove unused Docker resources across ALL projects; volumes are preserved."
        Invoke-Docker -DockerArguments @("system", "prune", "--all")
    }
    elseif ($Action -eq "clean-builder") {
        Write-Host "Remove unused default-builder cache across ALL projects; volumes are preserved."
        Invoke-Docker -DockerArguments @("builder", "prune", "--all")
    }
    elseif ($Action -eq "delete-volumes") {
        Invoke-Docker -DockerArguments @("compose", "down", "--volumes")
        Write-Host "Project containers and volumes removed. Run .\start.cmd to create a fresh demo."
    }
    else {
        Initialize-Environment
        Write-Host "Building diploma-project..."
        Invoke-Docker -DockerArguments @("compose", "build")
        Invoke-Docker -DockerArguments @(
            "compose", "up", "-d", "--wait", "--wait-timeout", "120", "db", "redis"
        )
        Invoke-Docker -DockerArguments @(
            "compose", "run", "--rm", "--no-deps", "api", "alembic", "upgrade", "head"
        )
        Invoke-Docker -DockerArguments @(
            "compose", "run", "--rm", "--no-deps", "api", "python", "-m", "scripts.seed_demo"
        )
        Invoke-Docker -DockerArguments @(
            "compose", "up", "-d", "--wait", "--wait-timeout", "120"
        )
        Write-Host "diploma-project is ready at http://localhost:8000"
        Write-Host "Demo password: DEMO_PASSWORD in .env. Stop with .\stop.cmd"
        if (-not $NoBrowser) {
            try {
                Start-Process "http://localhost:8000"
            }
            catch {
                Write-Warning "Open http://localhost:8000 in your browser."
            }
        }
    }
}
catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "For container details, run: docker compose logs --tail 80"
    $exitCode = 1
}
finally {
    Pop-Location
}
exit $exitCode
