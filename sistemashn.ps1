param(
    [Parameter(Position = 0)]
    [ValidateSet('run', 'build', 'license')]
    [string]$Action,
    [ValidateSet('repuestos', 'ferreteria')]
    [string]$Vertical,
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

if (-not $Vertical) {
    $available = @(@('repuestos', 'ferreteria') | Where-Object {
        $entry = if ($_ -eq 'repuestos') { 'src\main.py' } else { "src\main_$_.py" }
        Test-Path -LiteralPath (Join-Path $repo $entry)
    })
    if ($available.Count -eq 0) { throw 'No hay verticales disponibles.' }
    Write-Host 'Seleccione la vertical:'
    for ($i = 0; $i -lt $available.Count; $i++) {
        Write-Host "$($i + 1). $($available[$i])"
    }
    $selection = Read-Host 'Opcion'
    $index = 0
    if (-not [int]::TryParse($selection, [ref]$index) -or $index -lt 1 -or $index -gt $available.Count) {
        throw 'Vertical invalida.'
    }
    $Vertical = $available[$index - 1]
}
$entry = if ($Vertical -eq 'repuestos') { 'src\main.py' } else { "src\main_$Vertical.py" }
if (-not (Test-Path -LiteralPath (Join-Path $repo $entry))) {
    throw "La vertical $Vertical no esta disponible en este proyecto."
}

if ($Action -eq 'build') {
    & (Join-Path $repo 'scripts\dev.ps1') build -Vertical $Vertical
    exit $LASTEXITCODE
}

$python = Join-Path $repo 'evn\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Falta evn\Scripts\python.exe. Siga las instrucciones de instalacion en README.md.'
}

Push-Location $repo
try {
    if (-not $DataDir) {
        $DataDir = & $python -c "from sistemashn.core.db.engine import data_dir; print(data_dir('$Vertical'))"
        if ($LASTEXITCODE -ne 0 -or -not $DataDir) {
            throw 'No se pudo determinar la carpeta de datos.'
        }
    }

    if ($Action -eq 'license') {
        Write-Host "Licencia de desarrollo ($Vertical) para: $DataDir"
        & $python activar_licencia.py --data-dir $DataDir --vertical $Vertical
    }
    else {
        & $python $entry --data-dir $DataDir
    }
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $code
