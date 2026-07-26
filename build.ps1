[CmdletBinding()]
param(
    [ValidateSet('check', 'test', 'bundle-ffmpeg', 'bundle-tools', 'package', 'ci-package', 'ci-msi', 'clean')]
    [string]$Action = 'package',
    [string]$PythonExe = 'python',
    [switch]$SkipTests,
    [switch]$DownloadBundledFFmpeg,
    [string]$FFmpegArchive = '',
    [string]$FFmpegArchiveUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
    [string]$Aria2ArchiveUrl = 'https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip',
    [string]$YtDlpBinaryUrl = 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
    [string]$ArtifactName = 'RAVN-windows-x64',
    [string]$SignCertBase64 = $env:SIGN_CERT_BASE64,
    [string]$SignCertPassword = $env:SIGN_CERT_PASSWORD
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# Bundled-tool layout mirrors ravn_app/utils/bundled_tools.py: assets/<tool>/<platform>/.
# Everything placed here is picked up by ravn.spec's assets/ collection and ships in the
# zip, so an unzipped build finds its tools with no install and no first-run download.
$AssetsRoot = Join-Path $ProjectRoot 'assets\ffmpeg\win64'
$Aria2AssetsRoot = Join-Path $ProjectRoot 'assets\aria2\win64'
$YtDlpAssetsRoot = Join-Path $ProjectRoot 'assets\ytdlp\win64'
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

function Ensure-BundledAria2 {
    Write-Section 'Preparing bundled aria2c runtime'
    New-Item -ItemType Directory -Path $Aria2AssetsRoot -Force | Out-Null

    $aria2Exe = Join-Path $Aria2AssetsRoot 'aria2c.exe'
    if (Test-Path $aria2Exe) {
        Write-Host "Bundled aria2c found in $Aria2AssetsRoot" -ForegroundColor Green
        return
    }

    if (-not $DownloadBundledFFmpeg) {
        # aria2c drives torrent/magnet downloads only, which the app already degrades
        # gracefully without. Warn rather than fail so a local build without network
        # access still produces a package.
        Write-Host "Skipping aria2c bundling (pass -DownloadBundledFFmpeg to fetch it). Torrent features will need a system aria2c." -ForegroundColor Yellow
        return
    }

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ravn-aria2-" + [System.Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    try {
        $downloadPath = Join-Path $tempRoot 'aria2.zip'
        Write-Host "Downloading aria2 from $Aria2ArchiveUrl" -ForegroundColor Yellow
        Invoke-WebRequest -Uri $Aria2ArchiveUrl -OutFile $downloadPath
        Expand-Archive -Path $downloadPath -DestinationPath $tempRoot -Force

        $found = Get-ChildItem -Path $tempRoot -Filter aria2c.exe -Recurse | Select-Object -First 1
        if (-not $found) {
            throw 'aria2 archive did not contain aria2c.exe'
        }

        Copy-Item $found.FullName $aria2Exe -Force
        Write-Host "Bundled aria2c extracted to $Aria2AssetsRoot" -ForegroundColor Green
    }
    finally {
        if (Test-Path $tempRoot) {
            Remove-Item $tempRoot -Recurse -Force
        }
    }
}

function Ensure-BundledYtDlp {
    Write-Section 'Preparing bundled yt-dlp runtime'
    New-Item -ItemType Directory -Path $YtDlpAssetsRoot -Force | Out-Null

    $ytDlpExe = Join-Path $YtDlpAssetsRoot 'yt-dlp.exe'
    if (Test-Path $ytDlpExe) {
        Write-Host "Bundled yt-dlp found in $YtDlpAssetsRoot" -ForegroundColor Green
        return
    }

    if (-not $DownloadBundledFFmpeg) {
        # Downloads are a core feature, but the runner can still self-update into
        # %LOCALAPPDATA% on first run, so a missing bundle degrades rather than breaks.
        Write-Host "Skipping yt-dlp bundling (pass -DownloadBundledFFmpeg to fetch it). First run will self-update instead." -ForegroundColor Yellow
        return
    }

    Write-Host "Downloading yt-dlp from $YtDlpBinaryUrl" -ForegroundColor Yellow
    Invoke-WebRequest -Uri $YtDlpBinaryUrl -OutFile $ytDlpExe
    Write-Host "Bundled yt-dlp downloaded to $YtDlpAssetsRoot" -ForegroundColor Green
}

function Ensure-BundledTools {
    Ensure-BundledFFmpeg
    Ensure-BundledAria2
    Ensure-BundledYtDlp
}

function Invoke-PackageBuild {
    Write-Section 'Building PyInstaller package'
    Invoke-Python @('-m', 'PyInstaller', '--clean', '--noconfirm', 'ravn.spec')
    if (-not (Test-Path (Join-Path $DistRoot 'RAVN\RAVN.exe'))) {
        throw 'Expected packaged executable dist\RAVN\RAVN.exe was not created.'
    }
    if (-not (Test-Path (Join-Path $DistRoot 'RAVN\ravn-cli.exe'))) {
        throw 'Expected packaged executable dist\RAVN\ravn-cli.exe was not created.'
    }
}

function Test-BundledToolsInPackage {
    # The whole point of bundling is that an unzipped build resolves its own tools.
    # Verify the binaries actually landed in dist/ rather than trusting that the spec
    # collected them -- a silent miss here only shows up as "tools missing" for users.
    Write-Section 'Verifying bundled tools in package'
    $packageAssets = Join-Path $DistRoot 'RAVN\_internal\assets'
    if (-not (Test-Path $packageAssets)) {
        $packageAssets = Join-Path $DistRoot 'RAVN\assets'
    }

    $expected = @{
        'ffmpeg\win64\ffmpeg.exe'  = $true
        'ffmpeg\win64\ffprobe.exe' = $true
        'aria2\win64\aria2c.exe'   = $false
        'ytdlp\win64\yt-dlp.exe'   = $false
    }

    foreach ($relative in $expected.Keys) {
        $full = Join-Path $packageAssets $relative
        if (Test-Path $full) {
            Write-Host "  bundled: $relative" -ForegroundColor Green
        }
        elseif ($expected[$relative]) {
            throw "Required bundled tool missing from package: $relative"
        }
        else {
            Write-Host "  MISSING (optional): $relative" -ForegroundColor Yellow
        }
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
    Write-Host "Bundled aria2c root: $Aria2AssetsRoot"
    Write-Host "Bundled yt-dlp root: $YtDlpAssetsRoot"
    Write-Host "Spec file: $(Join-Path $ProjectRoot 'ravn.spec')"
}

function Invoke-MsiBuild {
    Write-Section 'Building MSI installer package'
    $PackageDir = Join-Path $DistRoot 'RAVN'
    if (-not (Test-Path $PackageDir)) {
        throw "Package directory not found at $PackageDir. Run -Action ci-package first."
    }
    $WxsFile = Join-Path $ProjectRoot 'packaging\ravn.wxs'
    $MsiOutput = Join-Path $DistRoot "$ArtifactName.msi"
    Write-Host "Running WiX build for $WxsFile -> $MsiOutput..." -ForegroundColor Yellow
    & wix build $WxsFile -d "SourceDir=$PackageDir" -o $MsiOutput
    if ($LASTEXITCODE -ne 0) {
        throw "WiX build failed with exit code $LASTEXITCODE"
    }
    Write-Host "MSI package created at $MsiOutput" -ForegroundColor Green
}

Push-Location $ProjectRoot
try {
    Assert-Windows
    switch ($Action) {
        'check' {
            Show-EnvironmentSummary
            Ensure-BuildDependencies
            Ensure-BundledTools
        }
        'test' {
            Ensure-BuildDependencies
            Invoke-Verification
        }
        'bundle-ffmpeg' {
            Ensure-BundledFFmpeg
        }
        'bundle-tools' {
            Ensure-BundledTools
        }
        'package' {
            Show-EnvironmentSummary
            Ensure-BuildDependencies
            Ensure-BundledTools
            Invoke-Verification
            Clear-PreviousBuilds
            Invoke-PackageBuild
            Test-BundledToolsInPackage
            Invoke-SignTool
            New-ReleaseArtifacts
        }
        'ci-package' {
            Show-EnvironmentSummary
            Ensure-BuildDependencies
            Ensure-BundledTools
            if (-not $SkipTests) {
                Invoke-Verification
            }
            Clear-PreviousBuilds
            Invoke-PackageBuild
            Test-BundledToolsInPackage
            Invoke-SignTool
            New-ReleaseArtifacts
        }
        'ci-msi' {
            Invoke-MsiBuild
        }
        'clean' {
            Clear-PreviousBuilds
        }
    }
}
finally {
    Pop-Location
}
