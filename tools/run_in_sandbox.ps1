[CmdletBinding()]
param(
    [string]$DistPath = "..\dist",
    [string]$SandboxWsbPath = "windows_sandbox.wsb"
)

$HostDistPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $DistPath))

if (-not (Test-Path $HostDistPath)) {
    Write-Host "Warning: The dist folder does not exist at $HostDistPath. Build the package first." -ForegroundColor Yellow
}

$WsbContent = @"
<Configuration>
  <VGpu>Disable</VGpu>
  <Networking>Default</Networking>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$HostDistPath</HostFolder>
      <SandboxFolder>C:\Users\WDAGUtilityAccount\Desktop\dist</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$([System.IO.Path]::GetFullPath($PSScriptRoot))</HostFolder>
      <SandboxFolder>C:\Users\WDAGUtilityAccount\Desktop\tools</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -ExecutionPolicy Bypass -NoExit -Command "Set-Location C:\Users\WDAGUtilityAccount\Desktop\dist\RAVN; .\RAVN.exe info https://www.youtube.com/watch?v=BaW_jenozKc --json"</Command>
  </LogonCommand>
</Configuration>
"@

$OutWsbPath = Join-Path $PSScriptRoot $SandboxWsbPath
Set-Content -Path $OutWsbPath -Value $WsbContent -Encoding UTF8

Write-Host "Generated WSB file at $OutWsbPath" -ForegroundColor Green
Write-Host "Double click $SandboxWsbPath or run 'Invoke-Item $SandboxWsbPath' to start the sandbox." -ForegroundColor Cyan
