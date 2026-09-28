param(
    [string]$ZephyrWorkspace = "$env:USERPROFILE\CMU\18649\zephyrproject",
    [string]$Sdk = "$env:USERPROFILE\zephyr-sdk-1.0.1",
    [string]$ZephyrBase = '',
    [string]$BuildDirectory = '',
    [string[]]$Modules = @(),
    [string]$ExtraConf = ''
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (!$ZephyrBase) { $ZephyrBase = Join-Path $ZephyrWorkspace 'zephyr' }
if (!$BuildDirectory) { $BuildDirectory = Join-Path $repoPath 'build\part4' }
$pythonPath = Join-Path $ZephyrWorkspace '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw "Zephyr Python not found: $pythonPath" }
if (!(Test-Path -LiteralPath $Sdk)) { throw "SDK not found: $Sdk" }
$env:Path = (Join-Path $ZephyrWorkspace '.venv\Scripts') + ';C:\Program Files\Git\mingw64\bin;' + $env:Path
$env:ZEPHYR_SDK_INSTALL_DIR = $Sdk
$env:ZEPHYR_TOOLCHAIN_VARIANT = 'zephyr'
$env:ZEPHYR_BASE = $ZephyrBase
$cmakeArgs = @("-DZEPHYR_BASE=$ZephyrBase", "-DZEPHYR_SDK_INSTALL_DIR=$Sdk",
    "-DZephyr-sdk_DIR=$Sdk/cmake")
if ($Modules.Count) { $cmakeArgs += '-DZEPHYR_MODULES=' + ($Modules -join ';') }
if ($ExtraConf) { $cmakeArgs += "-DEXTRA_CONF_FILE=$ExtraConf" }
Push-Location $ZephyrWorkspace
try {
    & $pythonPath -m west build -b nucleo_f401re "$repoPath\stm32_zephyr" -d $BuildDirectory -o=-j4 -- @cmakeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Firmware build failed.' }
} finally { Pop-Location }
& $pythonPath "$repoPath\tools\check_part4_build.py" --build $BuildDirectory --zephyr-base $ZephyrBase
if ($LASTEXITCODE -ne 0) { throw 'Generated configuration check failed.' }
Write-Output 'BUILD ONLY: no board was flashed and no serial/network commands were sent.'
Get-FileHash -LiteralPath "$BuildDirectory\zephyr\zephyr.bin" -Algorithm SHA256
