[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "status", "down")]
    [string]$Action = "up",

    [string]$Workspace = "dm-assistant-dev",

    [ValidateRange(1, 65535)]
    [int]$WindmillPort = 8000,

    [ValidateRange(1, 65535)]
    [int]$CampaignCorePort = 8001,

    [string]$EnvFile = (Join-Path $PSScriptRoot ".env"),

    [switch]$SkipWorkspaceDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $PSScriptRoot "compose.yaml"
$TestingComposeFile = Join-Path $PSScriptRoot "compose.testing.yaml"
$WorkspaceRoot = Join-Path $RepositoryRoot "windmill"
$DeployWorkspace = Join-Path $WorkspaceRoot "deploy_workspace.py"
$VenvPython = Join-Path $RepositoryRoot "campaign-core\.venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Environment file not found: $EnvFile. Copy deploy\.env.example to deploy\.env and replace every replace-me value."
}

function Resolve-DockerExecutable {
    $command = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }

    $localDocker = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
    if (Test-Path -LiteralPath $localDocker -PathType Leaf) {
        return $localDocker
    }

    throw "Docker CLI was not found. Start Docker Desktop and open a new PowerShell session."
}

$Docker = Resolve-DockerExecutable
$ComposeArguments = @(
    "compose",
    "--env-file", (Resolve-Path -LiteralPath $EnvFile).Path,
    "-f", $ComposeFile,
    "-f", $TestingComposeFile
)

function Invoke-DockerCompose {
    param([string[]]$CommandArguments)

    & $Docker @ComposeArguments @CommandArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed with exit code $LASTEXITCODE."
    }
}

function Test-HttpHealth {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
    }
    catch {
        return $false
    }
}

function Wait-HttpHealth {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSeconds = 180
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpHealth -Url $Url) {
            Write-Host "$Name is healthy: $Url"
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "$Name did not become healthy within $TimeoutSeconds seconds: $Url"
}

function Show-Health {
    param([string]$Name, [string]$Url)

    $state = if (Test-HttpHealth -Url $Url) { "healthy" } else { "unavailable" }
    Write-Host "${Name}: $state ($Url)"
}

$WindmillOrigin = "http://127.0.0.1:$WindmillPort"
$CampaignCoreOrigin = "http://127.0.0.1:$CampaignCorePort"
$env:WINDMILL_BIND_ADDRESS = "127.0.0.1"
$env:WINDMILL_HTTP_PORT = $WindmillPort.ToString()
$env:CAMPAIGN_CORE_TEST_PORT = $CampaignCorePort.ToString()

switch ($Action) {
    "up" {
        Write-Host "Validating the local test stack..."
        Invoke-DockerCompose -CommandArguments @("config", "--quiet")

        Write-Host "Building and starting the local test stack..."
        Invoke-DockerCompose -CommandArguments @("up", "-d", "--build")

        Wait-HttpHealth -Name "Windmill" -Url "$WindmillOrigin/api/health/status"
        Wait-HttpHealth -Name "Campaign Core" -Url "$CampaignCoreOrigin/health"

        if (-not $SkipWorkspaceDeploy) {
            $WmillCli = Join-Path $WorkspaceRoot "node_modules\.bin\wmill.cmd"
            if (-not (Test-Path -LiteralPath $WmillCli -PathType Leaf)) {
                throw "Windmill CLI is missing. Run npm ci in $WorkspaceRoot."
            }
            if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
                throw "Campaign Core virtual environment is missing. Create it before deploying the workspace."
            }

            Write-Host "Deploying Windmill workspace profile '$Workspace'..."
            & $VenvPython $DeployWorkspace --workspace $Workspace --apply
            if ($LASTEXITCODE -ne 0) {
                throw "Workspace deployment failed. Confirm that '$Workspace' is a configured CLI profile pointing to an existing Windmill workspace."
            }
        }

        $appUrl = "$WindmillOrigin/apps_raw/get/f/dm_assistant/apps/library"
        Write-Host ""
        Write-Host "Local UI test stack is ready."
        Write-Host "App: $appUrl"
        Write-Host "Stop safely: .\deploy\test-stack.ps1 down"
    }
    "status" {
        Invoke-DockerCompose -CommandArguments @("ps")
        Show-Health -Name "Windmill" -Url "$WindmillOrigin/api/health/status"
        Show-Health -Name "Campaign Core" -Url "$CampaignCoreOrigin/health"
    }
    "down" {
        Write-Host "Stopping the local test stack; named database volumes will be preserved..."
        Invoke-DockerCompose -CommandArguments @("down", "--remove-orphans")
        Write-Host "Local test stack stopped. Windmill and Campaign database volumes were preserved."
    }
}
