param(
    [string]$ZephyrWorkspace = "$env:USERPROFILE\CMU\18649\zephyrproject",
    [string]$Sdk = "$env:USERPROFILE\zephyr-sdk-1.0.1"
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $ZephyrWorkspace '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw "Zephyr Python not found: $pythonPath" }
if (!(Test-Path -LiteralPath $Sdk)) { throw "SDK not found: $Sdk" }
$env:Path = (Join-Path $ZephyrWorkspace '.venv\Scripts') + ';C:\Program Files\Git\mingw64\bin;' + $env:Path
$env:ZEPHYR_SDK_INSTALL_DIR = $Sdk
Push-Location $ZephyrWorkspace
try {
    & $pythonPath -m west build -b nucleo_f401re "$repoPath\stm32_zephyr" -d "$repoPath\build\part4" -o=-j4
    if ($LASTEXITCODE -ne 0) { throw 'Firmware build failed.' }
} finally { Pop-Location }
& $pythonPath "$repoPath\tools\check_part4_build.py" --build "$repoPath\build\part4" --zephyr-base "$ZephyrWorkspace\zephyr"
if ($LASTEXITCODE -ne 0) { throw 'Generated configuration check failed.' }
Write-Output 'BUILD ONLY: no board was flashed and no serial/network commands were sent.'
Get-FileHash -LiteralPath "$repoPath\build\part4\zephyr\zephyr.bin" -Algorithm SHA256
