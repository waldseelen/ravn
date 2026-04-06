[CmdletBinding()]
param(
    [string]$PackageRoot = (Join-Path (Get-Location) 'dist\RAVN'),
    [int]$LaunchSeconds = 8,
    [switch]$KeepOpen,
    [string]$ReportPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Add-Result {
    param(
        [System.Collections.Generic.List[object]]$Results,
        [string]$Check,
        [bool]$Passed,
        [string]$Detail
    )

    $Results.Add([PSCustomObject]@{
        Check  = $Check
        Passed = $Passed
        Detail = $Detail
    }) | Out-Null

    if ($Passed) {
        Write-Host "[PASS] $Check - $Detail" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] $Check - $Detail" -ForegroundColor Red
    }
}

function Test-ExpectedPath {
    param(
        [System.Collections.Generic.List[object]]$Results,
        [string]$Path,
        [string]$Label,
        [switch]$Directory
    )

    $exists = if ($Directory) { Test-Path $Path -PathType Container } else { Test-Path $Path -PathType Leaf }
    Add-Result -Results $Results -Check $Label -Passed $exists -Detail $Path
}

if ($env:OS -ne 'Windows_NT') {
    throw 'tools/windows_package_smoke.ps1 is intended for Windows validation only.'
}

$results = [System.Collections.Generic.List[object]]::new()
$packageRootResolved = if ([System.IO.Path]::IsPathRooted($PackageRoot)) {
    [System.IO.Path]::GetFullPath($PackageRoot)
}
else {
    [System.IO.Path]::GetFullPath((Join-Path $PWD.Path $PackageRoot))
}
$exePath = Join-Path $packageRootResolved 'RAVN.exe'
$internalRoot = Join-Path $packageRootResolved '_internal'
$bundledFFmpeg = Join-Path $internalRoot 'assets\ffmpeg\win64\ffmpeg.exe'
$bundledFFprobe = Join-Path $internalRoot 'assets\ffmpeg\win64\ffprobe.exe'
$translationEn = Join-Path $internalRoot 'ravn_app\translations\en.json'
$translationTr = Join-Path $internalRoot 'ravn_app\translations\tr.json'

$appDataRoot = Join-Path $env:APPDATA 'ravn'
$dataRoot = Join-Path $appDataRoot 'data'
$cacheRoot = Join-Path $env:LOCALAPPDATA 'ravn\cache'
$logsRoot = Join-Path $appDataRoot 'logs'
$logFile = Join-Path $logsRoot 'ravn.log'

Write-Section 'Packaged artifact structure checks'
Test-ExpectedPath -Results $results -Path $packageRootResolved -Label 'Package root exists' -Directory
Test-ExpectedPath -Results $results -Path $exePath -Label 'Executable exists'
Test-ExpectedPath -Results $results -Path $bundledFFmpeg -Label 'Bundled ffmpeg.exe exists'
Test-ExpectedPath -Results $results -Path $bundledFFprobe -Label 'Bundled ffprobe.exe exists'
Test-ExpectedPath -Results $results -Path $translationEn -Label 'English translations bundled'
Test-ExpectedPath -Results $results -Path $translationTr -Label 'Turkish translations bundled'

$process = $null
$launchPassed = $false

if (Test-Path $exePath -PathType Leaf) {
    Write-Section 'Launch smoke'
    try {
        $process = Start-Process -FilePath $exePath -PassThru
        Start-Sleep -Seconds $LaunchSeconds
        $process.Refresh()
        $launchPassed = -not $process.HasExited
        Add-Result -Results $results -Check 'Packaged app launches' -Passed $launchPassed -Detail ("PID={0}" -f $process.Id)
    }
    catch {
        Add-Result -Results $results -Check 'Packaged app launches' -Passed $false -Detail $_.Exception.Message
    }
}

Write-Section 'Runtime side-effect checks'
Test-ExpectedPath -Results $results -Path $appDataRoot -Label 'Config root created' -Directory
Test-ExpectedPath -Results $results -Path $dataRoot -Label 'Data root created' -Directory
Test-ExpectedPath -Results $results -Path $cacheRoot -Label 'Cache root created' -Directory
Test-ExpectedPath -Results $results -Path $logsRoot -Label 'Log directory created' -Directory
Test-ExpectedPath -Results $results -Path $logFile -Label 'Log file created'

if ($process -and -not $KeepOpen) {
    try {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
            Add-Result -Results $results -Check 'Packaged app can be stopped after smoke launch' -Passed $true -Detail ("PID={0}" -f $process.Id)
        }
    }
    catch {
        Add-Result -Results $results -Check 'Packaged app can be stopped after smoke launch' -Passed $false -Detail $_.Exception.Message
    }
}

Write-Section 'Manual validation checklist'
@(
    'Download: paste a normal media URL and complete a basic download.',
    'Convert: open Studio > Convert and complete one conversion.',
    'Queue/History: confirm queue row visibility and persisted history entry.',
    'Library: confirm a supported output appears in the local media library when auto-add is enabled.'
) | ForEach-Object { Write-Host "[TODO] $_" -ForegroundColor Yellow }

if (-not $ReportPath) {
    $ReportPath = Join-Path $packageRootResolved 'windows-package-smoke-report.json'
}
elseif (-not [System.IO.Path]::IsPathRooted($ReportPath)) {
    $ReportPath = [System.IO.Path]::GetFullPath((Join-Path $PWD.Path $ReportPath))
}

$reportDirectory = Split-Path -Parent $ReportPath
if ($reportDirectory -and -not (Test-Path $reportDirectory)) {
    New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
}

$results | ConvertTo-Json -Depth 3 | Set-Content -Path $ReportPath -Encoding UTF8
Write-Host "`nReport written to: $ReportPath" -ForegroundColor Cyan

$failed = @($results | Where-Object { -not $_.Passed }).Count
if ($failed -gt 0) {
    Write-Host "`nSmoke validation completed with $failed failing checks." -ForegroundColor Red
    exit 1
}

Write-Host "`nSmoke validation checks passed. Complete the manual checklist before marking BLD-07 done." -ForegroundColor Green
