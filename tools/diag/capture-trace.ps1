# Record what the Windows audio service does while a CABLE endpoint is opened.
#
# Run from an ELEVATED PowerShell (ETW sessions need admin):
#   powershell -ExecutionPolicy Bypass -File tools\diag\capture-trace.ps1 [-Cable A] [-Python <python.exe>]
#
# Starts an ETW session with the audio stack's diagnostic providers, opens CABLE-<x> Output
# (capture) and CABLE-<x> Input (render, as a known-good control) in shared and exclusive mode,
# stops the session, decodes it to XML and prints a summary (tools\diag\summarize_trace.py).
# Output: %TEMP%\vc_audio_trace\{audio.etl,audio.xml,probe.txt,summary.txt}.
# Does not restart services or change any setting. See docs\DEBUGGING.md.

param(
    [ValidateSet('A', 'B', 'C', 'D')] [string]$Cable = 'A',
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$tools = Split-Path -Parent $PSScriptRoot          # ...\tools
$repo = Split-Path -Parent $tools
if (-not $Python) {
    $venv = Join-Path $repo '.venv-test\Scripts\python.exe'
    $Python = if (Test-Path $venv) { $venv } else { 'python' }
}
$out = Join-Path $env:TEMP 'vc_audio_trace'
New-Item -ItemType Directory -Force $out | Out-Null
Remove-Item "$out\*" -Force -ErrorAction SilentlyContinue

# Provider GUIDs. The TraceLogging ones are the name hashes of the names listed below; they are
# self-describing, so tracerpt decodes them without symbols. (The manifest provider
# Microsoft-Windows-Audio alone is not enough: it does not log why audiosrv fails.)
$providers = @'
{AE4BD3BE-F36F-45B6-8D21-BDD6FB832853} 0xFFFFFFFFFFFFFFFF 0xff
{3d2b6366-47a4-5e10-6974-e5f7de0d3f28} 0xFFFFFFFFFFFFFFFF 0xff
{46df03df-beab-5f0b-7eb2-e471c1bea993} 0xFFFFFFFFFFFFFFFF 0xff
{553ca39b-c608-566d-18ae-7b9a03a39acd} 0xFFFFFFFFFFFFFFFF 0xff
{2c2677bd-bc9a-5a88-4772-6f17de82b2c7} 0xFFFFFFFFFFFFFFFF 0xff
{64788b34-e8e5-5664-af50-45afb294a1dc} 0xFFFFFFFFFFFFFFFF 0xff
{29b5a4da-cbf8-5556-2939-13256cb52969} 0xFFFFFFFFFFFFFFFF 0xff
{0e7e8596-d648-5c94-adbd-3d780faa58e8} 0xFFFFFFFFFFFFFFFF 0xff
{ec6ede49-f40f-5f93-8651-a4edc18afe06} 0xFFFFFFFFFFFFFFFF 0xff
{6e7b1892-5288-5fe5-8f34-e3b0dc671fd2} 0xFFFFFFFFFFFFFFFF 0xff
{c8b6aae6-230c-5894-c672-c9fa8cf0b857} 0xFFFFFFFFFFFFFFFF 0xff
{d375f14e-9624-5a18-f53e-5bce2043a97f} 0xFFFFFFFFFFFFFFFF 0xff
{a076f707-4472-5083-d14f-826d0ef75c78} 0xFFFFFFFFFFFFFFFF 0xff
'@
# In order: Microsoft-Windows-Audio, Microsoft.Windows.Audio.Service, .Engine, .KernelStreamingEndpoint,
# .AudioEngineUtil, .DeviceGraph, .AudioDG, .EndpointBuilder, .EndpointCharacteristics, .Client,
# Microsoft.Audio.AudioClient, .CrossProcess, Microsoft.Windows.Audio.MultimediaDevice
Set-Content -Path "$out\providers.txt" -Value $providers -Encoding ASCII

logman stop vc_audio -ets 2>$null | Out-Null
logman start vc_audio -pf "$out\providers.txt" -o "$out\audio.etl" -ets | Out-Null
try {
    Start-Sleep -Seconds 1
    & $Python (Join-Path $PSScriptRoot 'wasapi_probe.py') open --cable $Cable 2>&1 |
        Out-File -FilePath "$out\probe.txt" -Encoding ASCII
    Get-Content "$out\probe.txt"
    Start-Sleep -Seconds 1
}
finally {
    logman stop vc_audio -ets | Out-Null
    tracerpt "$out\audio.etl" -o "$out\audio.xml" -of XML -y | Out-Null
    Write-Host "Trace written to $out"
}
& $Python (Join-Path $PSScriptRoot 'summarize_trace.py') "$out\audio.xml" 2>&1 |
    Tee-Object -FilePath "$out\summary.txt"
