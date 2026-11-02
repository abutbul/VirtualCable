param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($currentIdentity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell window."
}

$certificatePath = Join-Path $PSScriptRoot "VirtualCable-TestCertificate.cer"
$infPath = Join-Path $PSScriptRoot "ComponentizedAudioSample.inf"
$hardwareId = "Root\sysvad_ComponentizedAudioSample"

$devconCandidates = @(
    (Join-Path $PSScriptRoot "devcon.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\Tools\x64\devcon.exe"),
    (Join-Path $env:ProgramFiles "Windows Kits\10\Tools\x64\devcon.exe")
)
$devcon = $devconCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $devcon) {
    $devconCommand = Get-Command devcon.exe -ErrorAction SilentlyContinue
    if ($devconCommand) { $devcon = $devconCommand.Source }
}
if (-not $devcon) {
    throw "DevCon was not found. Install the Windows Driver Kit, or add its x64 Tools folder to PATH."
}

if ($Uninstall) {
    & $devcon remove $hardwareId
    if ($LASTEXITCODE -ne 0) { throw "DevCon failed to remove the virtual audio device." }
    exit 0
}

if (-not (Test-Path $certificatePath) -or -not (Test-Path $infPath)) {
    throw "Extract the complete driver ZIP before running this script."
}

$testSigning = bcdedit /enum '{current}' | Select-String -Pattern "testsigning\s+Yes"
if (-not $testSigning) {
    throw "Test signing is not enabled. Run 'bcdedit /set TESTSIGNING ON' as administrator, reboot, then run this installer again. Secure Boot may need to be disabled on this test machine."
}

Import-Certificate -FilePath $certificatePath -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
Import-Certificate -FilePath $certificatePath -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher" | Out-Null

& $devcon install $infPath $hardwareId
if ($LASTEXITCODE -ne 0) { throw "DevCon failed to install the virtual audio driver." }

Write-Host "Installed test driver. Windows Sound settings should show CABLE-A/B/C/D Input (playback) and CABLE-A/B/C/D Output (recording)."