[CmdletBinding()]
param(
    [ValidateSet('check', 'test', 'bundle-ffmpeg', 'package', 'ci-package', 'clean')]
    [string]$Action = 'package',
    [string]$PythonExe = 'python',
    [switch]$SkipTests,
    [switch]$DownloadBundledFFmpeg,
    [string]$FFmpegArchive = '',
    [string]$FFmpegArchiveUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
    [string]$ArtifactName = 'RAVN-windows-x64',
    [string]$SignCertBase64 = $env:SIGN_CERT_BASE64,
    [string]$SignCertPassword = $env:SIGN_CERT_PASSWORD
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AssetsRoot = Join-Path $ProjectRoot 'assets\ffmpeg\win64'
$BuildRoot = Join-Path $ProjectRoot 'build'
$DistRoot = Join-Path $ProjectRoot 'dist'
$ArtifactZip = Join-Path $DistRoot "$ArtifactName.zip"
$ChecksumFile = Join-Path $DistRoot "$ArtifactName.sha256.txt"

function Write-Section([string]$Message) {
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Assert-Windows {
    if ($env:OS -ne 'Windows_NT') {
        throw 'build.ps1 packaging pipeline is Windows-only.'
    }
}

function Invoke-Python([string[]]$Arguments) {
    & $PythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $PythonExe $($Arguments -join ' ')"
    }
}

function Ensure-BuildDependencies {
    Write-Section 'Installing build dependencies'
    Invoke-Python @('-m', 'pip', 'install', '--upgrade', 'pip')
    Invoke-Python @('-m', 'pip', 'install', '-r', 'requirements.txt')
    Invoke-Python @('-m', 'pip', 'install', 'pyinstaller', 'pytest')
}

function Invoke-Verification {
    if ($SkipTests) {
        Write-Host 'Skipping tests by request.' -ForegroundColor Yellow
        return
    }

    Write-Section 'Running verification suite'
    Invoke-Python @('-m', 'pytest', '-q')
}

function Clear-PreviousBuilds {
    Write-Section 'Cleaning previous build artifacts'
    foreach ($path in @($BuildRoot, $DistRoot)) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
        }
    }
}

function Expand-BundledFFmpegFromArchive([string]$ArchivePath) {
    if (-not (Test-Path $ArchivePath)) {
        throw "FFmpeg archive not found: $ArchivePath"
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ravn-ffmpeg-" + [System.Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    try {
        Expand-Archive -Path $ArchivePath -DestinationPath $tempRoot -Force
        $ffmpegExe = Get-ChildItem -Path $tempRoot -Filter ffmpeg.exe -Recurse | Select-Object -First 1
        $ffprobeExe = Get-ChildItem -Path $tempRoot -Filter ffprobe.exe -Recurse | Select-Object -First 1
        if (-not $ffmpegExe -or -not $ffprobeExe) {
            throw 'Archive did not contain ffmpeg.exe and ffprobe.exe'
        }

        New-Item -ItemType Directory -Path $AssetsRoot -Force | Out-Null
        Copy-Item $ffmpegExe.FullName (Join-Path $AssetsRoot 'ffmpeg.exe') -Force
        Copy-Item $ffprobeExe.FullName (Join-Path $AssetsRoot 'ffprobe.exe') -Force
    }
    finally {
        if (Test-Path $tempRoot) {
            Remove-Item $tempRoot -Recurse -Force
        }
    }
}

function Ensure-BundledFFmpeg {
    Write-Section 'Preparing bundled FFmpeg runtime'
    New-Item -ItemType Directory -Path $AssetsRoot -Force | Out-Null

    $ffmpegExe = Join-Path $AssetsRoot 'ffmpeg.exe'
    $ffprobeExe = Join-Path $AssetsRoot 'ffprobe.exe'

    if ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe)) {
        Write-Host "Bundled FFmpeg runtime found in $AssetsRoot" -ForegroundColor Green
        return
    }

    if ($FFmpegArchive) {
        Expand-BundledFFmpegFromArchive -ArchivePath $FFmpegArchive
        Write-Host "Bundled FFmpeg extracted from archive: $FFmpegArchive" -ForegroundColor Green
        return
    }

    if ($DownloadBundledFFmpeg) {
        $downloadPath = Join-Path $BuildRoot 'ffmpeg-runtime.zip'
        New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
        Write-Host "Downloading FFmpeg runtime from $FFmpegArchiveUrl" -ForegroundColor Yellow
        Invoke-WebRequest -Uri $FFmpegArchiveUrl -OutFile $downloadPath
        Expand-BundledFFmpegFromArchive -ArchivePath $downloadPath
        Write-Host 'Bundled FFmpeg downloaded and extracted.' -ForegroundColor Green
        return
    }

    throw "Bundled FFmpeg runtime missing. Place ffmpeg.exe and ffprobe.exe under $AssetsRoot, pass -FFmpegArchive <zip>, or use -DownloadBundledFFmpeg."
}

function Invoke-PackageBuild {
    Write-Section 'Building PyInstaller package'
    Invoke-Python @('-m', 'PyInstaller', '--clean', '--noconfirm', 'ravn.spec')
    if (-not (Test-Path (Join-Path $DistRoot 'RAVN\RAVN.exe'))) {
        throw 'Expected packaged executable dist\RAVN\RAVN.exe was not created.'
    }
}

function Get-Sha256Hex([string]$FilePath) {
    if (Get-Command Get-FileHash -ErrorAction SilentlyContinue) {
        return (Get-FileHash -Algorithm SHA256 -Path $FilePath).Hash
    }

    $stream = [System.IO.File]::OpenRead($FilePath)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hashBytes = $sha.ComputeHash($stream)
            return ([System.BitConverter]::ToString($hashBytes)).Replace('-', '')
        }
        finally {
            $sha.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Invoke-SignTool {
    if (-not $SignCertBase64 -or -not $SignCertPassword) {
        Write-Host "Skipping code signing: Credentials not provided." -ForegroundColor Yellow
        return
    }
    Write-Section 'Signing executable'
    $certPath = Join-Path $BuildRoot 'cert.pfx'
    [IO.File]::WriteAllBytes($certPath, [Convert]::FromBase64String($SignCertBase64))
    $exePath = Join-Path $DistRoot 'RAVN\RAVN.exe'
    
    if (-not (Test-Path $exePath)) {
        throw "Executable not found for signing: $exePath"
    }

    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certPath, $SignCertPassword)
    $sig = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -TimestampServer "http://timestamp.digicert.com"
    
    if ($sig.Status -ne 'Valid') {
        Write-Host "Signing failed: $($sig.StatusMessage)" -ForegroundColor Red
    } else {
        Write-Host "Successfully signed $exePath" -ForegroundColor Green
    }
    
    if (Test-Path $certPath) {
        Remove-Item $certPath -Force
    }
}

function New-ReleaseArtifacts {
    Write-Section 'Creating distributable archive'
    if (Test-Path $ArtifactZip) {
        Remove-Item $ArtifactZip -Force
    }
    Compress-Archive -Path (Join-Path $DistRoot 'RAVN\*') -DestinationPath $ArtifactZip -Force
    $hash = Get-Sha256Hex -FilePath $ArtifactZip
    Set-Content -Path $ChecksumFile -Value ("{0}  {1}" -f $hash, (Split-Path $ArtifactZip -Leaf))
    Write-Host "Archive: $ArtifactZip" -ForegroundColor Green
    Write-Host "Checksum: $ChecksumFile" -ForegroundColor Green
}

function Show-EnvironmentSummary {
    Write-Section 'Environment summary'
    & $PythonExe --version
    if ($LASTEXITCODE -ne 0) {
        throw 'Python is not available.'
    }
    Write-Host "Project root: $ProjectRoot"
    Write-Host "Bundled FFmpeg root: $AssetsRoot"
    Write-Host "Spec file: $(Join-Path $ProjectRoot 'ravn.spec')"
}

Push-Location $ProjectRoot
try {
    Assert-Windows
    switch ($Action) {
        'check' {
            Show-EnvironmentSummary
            Ensure-BuildDependencies
            Ensure-BundledFFmpeg
        }
        'test' {
            Ensure-BuildDependencies
            Invoke-Verification
        }
        'bundle-ffmpeg' {
            Ensure-BundledFFmpeg
        }
        'package' {
            Show-EnvironmentSummary
            Ensure-BuildDependencies
            Ensure-BundledFFmpeg
            Invoke-Verification
            Clear-PreviousBuilds
            Invoke-PackageBuild
            Invoke-SignTool
            New-ReleaseArtifacts
        }
        'ci-package' {
            Show-EnvironmentSummary
            Ensure-BuildDependencies
            Ensure-BundledFFmpeg
            if (-not $SkipTests) {
                Invoke-Verification
            }
            Clear-PreviousBuilds
            Invoke-PackageBuild
            Invoke-SignTool
            New-ReleaseArtifacts
        }
        'clean' {
            Clear-PreviousBuilds
        }
    }
}
finally {
    Pop-Location
}
