param(
    [switch]$Uninstall,
    [string]$LogPath = (Join-Path $env:TEMP "VirtualCable-Install.log")
)

$ErrorActionPreference = "Stop"
Start-Transcript -LiteralPath $LogPath -Force | Out-Null
trap {
    Write-Host "Installer failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Diagnostic log: $LogPath"
    Stop-Transcript | Out-Null
    exit 1
}

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
    $devconExitCode = $LASTEXITCODE
    if ($devconExitCode -ne 0) { throw "DevCon failed to remove the virtual audio device (exit code $devconExitCode)." }
    Stop-Transcript | Out-Null
    exit 0
}

if (-not (Test-Path $certificatePath) -or -not (Test-Path $infPath)) {
    throw "Extract the complete driver ZIP before running this script."
}

$bcdOutput = & "$env:SystemRoot\System32\bcdedit.exe" /enum '{current}' 2>&1
$bcdExitCode = $LASTEXITCODE
if ($bcdExitCode -ne 0) {
    throw "Could not query the boot configuration (exit code $bcdExitCode): $($bcdOutput -join ' ')"
}
$testSigning = $bcdOutput | Select-String -Pattern "testsigning\s+Yes"
if (-not $testSigning) {
    throw "Test signing is not enabled. Run 'bcdedit /set TESTSIGNING ON' as administrator, reboot, then run this installer again. Secure Boot may need to be disabled on this test machine."
}

Import-Certificate -FilePath $certificatePath -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
Import-Certificate -FilePath $certificatePath -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher" | Out-Null

& $devcon install $infPath $hardwareId
$devconExitCode = $LASTEXITCODE
if ($devconExitCode -ne 0) {
    throw "DevCon failed to install the virtual audio driver (exit code $devconExitCode). Review the DevCon output above and $env:SystemRoot\inf\setupapi.dev.log for the Windows driver-install error."
}

Write-Host "Installed test driver. Windows Sound settings should show CABLE-A/B/C/D Input (playback) and CABLE-A/B/C/D Output (recording)."
Stop-Transcript | Out-Null