param(
    [string]$ServerUser = "arunsanjeevms",
    [string]$ServerHost = "20.44.48.64",
    [string]$ServerDeployDir = "/home/arunsanjeevms/deploy/akhgam-sync",
    [string]$ServerProjectDir = "/home/arunsanjeevms/akhgam-herbals",
    [string]$ServiceName = "akhgam-herbals",
    [string]$MySQLUser = "",
    [securestring]$MySQLPassword = $null,
    [string]$MySQLDb = "akhgam_herbals"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$buildRoot = Join-Path $projectRoot "deploy_build"
$bundleRoot = Join-Path $buildRoot "akhgam_sync_$timestamp"
$projectStaging = Join-Path $bundleRoot "project"
$dbDumpPath = Join-Path $bundleRoot "akhgam_herbals.sql"
$zipPath = Join-Path $buildRoot "akhgam_sync_$timestamp.zip"

if (-not $MySQLUser) {
    if ($env:MYSQL_USER) {
        $MySQLUser = $env:MYSQL_USER
    } else {
        $MySQLUser = "root"
    }
}

if (-not $MySQLPassword) {
    if ($env:MYSQL_PASSWORD) {
        $MySQLPassword = ConvertTo-SecureString $env:MYSQL_PASSWORD -AsPlainText -Force
    } else {
        throw "Provide -MySQLPassword or set MYSQL_PASSWORD environment variable."
    }
}

$MySQLPasswordPlain = [System.Net.NetworkCredential]::new("", $MySQLPassword).Password

if (Test-Path $bundleRoot) {
    Remove-Item -Path $bundleRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $projectStaging -Force | Out-Null

$excludeDirs = @(".venv", "__pycache__", "deploy_build", ".git")
$robocopyArgs = @(
    $projectRoot,
    $projectStaging,
    "/MIR",
    "/XD"
) + $excludeDirs + @(
    "/XF", "*.pyc", "*.pyo", "*.log", "*.tmp", "Thumbs.db"
)

robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "Project copy failed (robocopy exit code: $LASTEXITCODE)."
}

$mysqldump = Get-Command mysqldump -ErrorAction SilentlyContinue
if (-not $mysqldump) {
    throw "mysqldump not found in PATH. Install MySQL client tools or add mysqldump to PATH."
}

$dumpArgs = @(
    "--single-transaction",
    "--routines",
    "--triggers",
    "--default-character-set=utf8mb4",
    "-u$MySQLUser",
    "-p$MySQLPasswordPlain",
    $MySQLDb
)

& $mysqldump.Source @dumpArgs | Out-File -FilePath $dbDumpPath -Encoding utf8

if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Compress-Archive -Path (Join-Path $bundleRoot "*") -DestinationPath $zipPath -Force

$zipName = Split-Path -Leaf $zipPath

Write-Host "Bundle created: $zipPath"
Write-Host ""
Write-Host "Upload bundle to server:"
Write-Host "scp \"$zipPath\" $ServerUser@${ServerHost}:$ServerDeployDir/"
Write-Host ""
Write-Host "Then run on server:"
Write-Host "cd $ServerDeployDir"
Write-Host "unzip -o $zipName"
Write-Host "sudo mysqldump -u<db_user> -p<db_password> $MySQLDb > backup_${MySQLDb}_before_sync.sql"
Write-Host "sudo systemctl stop $ServiceName"
Write-Host "sudo rsync -a --delete project/ $ServerProjectDir/"
Write-Host "sudo mysql -u<db_user> -p<db_password> $MySQLDb < akhgam_herbals.sql"
Write-Host "sudo systemctl start $ServiceName"
Write-Host "sudo systemctl reload nginx"
