param(
    [Parameter(Position = 0)]
    [ValidateSet('run', 'build', 'license')]
    [string]$Action,
    [string]$DataDir
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot

if (-not $Action) {
    Write-Host 'SistemasHN'
    Write-Host '1. Ejecutar programa'
    Write-Host '2. Compilar para Windows'
    Write-Host '3. Generar licencia de desarrollo'
    Write-Host '0. Salir'
    $Action = switch (Read-Host 'Opcion') {
        '1' { 'run' }
        '2' { 'build' }
        '3' { 'license' }
        '0' { exit 0 }
        default { throw 'Opcion invalida.' }
    }
}

if ($Action -eq 'build') {
    & (Join-Path $repo 'scripts\dev.ps1') build
    exit $LASTEXITCODE
}

$python = Join-Path $repo 'evn\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Falta evn\Scripts\python.exe. Siga las instrucciones de instalacion en README.md.'
}

Push-Location $repo
try {
    if (-not $DataDir) {
        $DataDir = & $python -c 'from sistemashn.core.db.engine import data_dir; print(data_dir("repuestos"))'
        if ($LASTEXITCODE -ne 0 -or -not $DataDir) {
            throw 'No se pudo determinar la carpeta de datos.'
        }
    }

    if ($Action -eq 'license') {
        Write-Host "Licencia de desarrollo para: $DataDir"
        & $python activar_licencia.py --data-dir $DataDir
    }
    else {
        & $python src\main.py --data-dir $DataDir
    }
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $code
